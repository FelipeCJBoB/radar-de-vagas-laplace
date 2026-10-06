"""Validação do config.yaml e resolução da região.

O modelo não traz estado, cidade nem nível de carreira preenchidos (princípio de
zero-default): quem não definiu isso recebe uma lista de pendências em vez de uma
rodada com vagas de um lugar que não é o dele. `resolver_regiao` transforma a seção
`regiao` nas chaves que o resto do código lê (`cidades`, `incluir_remoto`, `_estados`
etc.); `validar_config` diz o que falta, em português e com a correção.
"""
from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import geografia
from .text import normalize

NIVEIS = ("estagio", "junior", "pleno", "senior", "lideranca")
REMOTOS = ("nao", "aceitar", "preferir", "somente")
FUSO_PADRAO = "America/Sao_Paulo"
# O detector de senioridade só distingue três degraus (estágio conta como júnior e
# liderança como sênior), então o nível-alvo é projetado nessa escala.
ESCALA = ("junior", "pleno", "senior")
_PARA_ESCALA = {"estagio": "junior", "junior": "junior", "pleno": "pleno",
                "senior": "senior", "lideranca": "senior"}


class ConfigInvalida(Exception):
    """config.yaml incompleto ou inconsistente; a mensagem lista cada pendência."""


def normalizar_nivel(valor) -> str | None:
    v = normalize(str(valor or ""))
    return v if v in NIVEIS else None


def nivel_na_escala(valor) -> str | None:
    n = normalizar_nivel(valor)
    return _PARA_ESCALA.get(n) if n else None


def _secao(cfg: dict, nome: str) -> dict:
    v = cfg.get(nome)
    return v if isinstance(v, dict) else {}


def resolver_regiao(cfg: dict) -> dict:
    """Preenche as chaves derivadas a partir de `regiao` e `alvo`. Não levanta erro.

    Seção ausente ou incompleta resulta em `cidades` vazia; quem barra a rodada é
    `exigir_config_valida`, para que `status`, testes e o `init` consigam carregar o
    arquivo mesmo vazio.
    """
    r = _secao(cfg, "regiao")
    remoto = normalize(str(r.get("remoto", "aceitar")))
    cfg["_remoto"] = remoto if remoto in REMOTOS else "aceitar"
    cfg["incluir_remoto"] = cfg["_remoto"] != "nao"

    siglas = [s for s in (geografia.uf_sigla(str(e)) for e in (r.get("estados") or [])) if s]
    cfg["_estados_sigla"] = siglas
    cfg["_estados"] = [geografia.ufs()[s] for s in siglas]
    cfg["_fuso"] = r.get("fuso") or FUSO_PADRAO
    cfg["_idioma_ia"] = r.get("idioma_ia") or "pt-BR"

    base = _secao(r, "base")
    base_uf = base.get("uf") or (siglas[0] if len(siglas) == 1 else "")
    alcance = normalize(str(r.get("alcance", "regiao_imediata"))).replace(" ", "_")
    cfg["cidades"] = (geografia.expandir(alcance, str(base.get("cidade") or ""), str(base_uf),
                                         cfg["_estados"], r.get("cidades"))
                      if cfg["_estados"] else [])
    cfg["cidades_alias"] = {a: c for a, c in (r.get("apelidos") or {}).items() if c in cfg["cidades"]}
    cfg["_nivel_alvo"] = nivel_na_escala(_secao(cfg, "alvo").get("nivel"))
    return cfg


def validar_config(cfg: dict) -> list[str]:
    """Pendências do config.yaml, cada uma com o que fazer. Lista vazia = válido."""
    erros: list[str] = []
    r = _secao(cfg, "regiao")
    remoto = normalize(str(r.get("remoto", "aceitar")))
    somente_remoto = remoto == "somente"

    if remoto not in REMOTOS:
        erros.append(f"regiao.remoto: '{r.get('remoto')}' não é válido. Use um de: {', '.join(REMOTOS)}.")

    estados = r.get("estados") or []
    if not somente_remoto:
        if not estados:
            erros.append("regiao.estados está vazio. Informe a(s) UF(s) onde você busca, ex.: [SP] ou [SP, RJ].")
        for e in estados:
            if not geografia.uf_sigla(str(e)):
                erros.append(f"regiao.estados: '{e}' não é uma UF brasileira (use a sigla, ex.: SP).")

        base = _secao(r, "base")
        alcance = normalize(str(r.get("alcance", "regiao_imediata"))).replace(" ", "_")
        if alcance not in geografia.ALCANCES:
            erros.append(f"regiao.alcance: '{r.get('alcance')}' não é válido. Use um de: {', '.join(geografia.ALCANCES)}.")
        if alcance != "estado":
            cidade = str(base.get("cidade") or "")
            if not cidade and alcance != "lista":
                erros.append("regiao.base.cidade está vazio. Informe a cidade onde você mora ou quer trabalhar.")
            elif cidade:
                uf = base.get("uf") or (estados[0] if len(estados) == 1 else "")
                if not uf:
                    erros.append("regiao.base.uf está vazio e há mais de um estado em regiao.estados.")
                elif not geografia.buscar_cidade(cidade, str(uf)):
                    dicas = geografia.sugestoes(cidade, str(uf))
                    erros.append(f"regiao.base.cidade: '{cidade}' não existe em {uf}."
                                 + (f" Você quis dizer: {', '.join(dicas)}?" if dicas else ""))
        if alcance == "lista" and not r.get("cidades"):
            erros.append("regiao.alcance é 'lista', mas regiao.cidades está vazio.")

    if not normalizar_nivel(_secao(cfg, "alvo").get("nivel")):
        erros.append("alvo.nivel está vazio ou inválido. Use um de: " + ", ".join(NIVEIS) + ".")

    fuso = r.get("fuso") or FUSO_PADRAO
    try:
        ZoneInfo(fuso)
    except (ZoneInfoNotFoundError, ValueError):
        erros.append(f"regiao.fuso: '{fuso}' não é um fuso IANA válido (ex.: America/Sao_Paulo).")

    if not cfg.get("termos_busca"):
        erros.append("termos_busca está vazio. Sem termos, nenhuma fonte é consultada.")
    cats = cfg.get("categorias")
    if not isinstance(cats, dict) or not cats:
        erros.append("categorias está vazio. Sem categorias, nenhuma vaga é classificada.")
    else:
        for chave, c in cats.items():
            if not isinstance(c, dict) or not c.get("nome") or not c.get("titulo"):
                erros.append(f"categorias.{chave}: precisa de 'nome' e de ao menos um termo em 'titulo'.")
    if not cfg.get("senioridade"):
        erros.append("senioridade está vazio. Veja os termos de nível no config de exemplo.")
    return erros


def exigir_config_valida(cfg: dict) -> None:
    erros = validar_config(cfg)
    if erros:
        lista = "\n".join(f"  - {e}" for e in erros)
        raise ConfigInvalida(f"config.yaml tem {len(erros)} pendência(s):\n{lista}\n"
                             "Veja guia/04-personalizar.md.")


NIVEL_ROTULO = {"estagio": "estágio", "junior": "júnior", "pleno": "pleno",
                "senior": "sênior", "lideranca": "liderança"}


def contexto_ia(cfg: dict) -> dict:
    """O que a avaliação por IA precisa saber sobre quem busca, sem ler o config inteiro.

    Entra no prompt de sistema (ver `enrich.montar_system`): as áreas vêm das
    categorias, na ordem de prioridade, e o nível e o idioma da seção `alvo`/`regiao`.
    """
    cats = sorted((cfg.get("categorias") or {}).values(), key=lambda c: c.get("prioridade", 99))
    nivel = normalizar_nivel(_secao(cfg, "alvo").get("nivel"))
    return {"areas": [c["nome"] for c in cats if c.get("nome")],
            "nivel": NIVEL_ROTULO.get(nivel, ""),
            "idioma": cfg.get("_idioma_ia") or "pt-BR"}
