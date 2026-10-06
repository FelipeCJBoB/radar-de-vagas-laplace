"""`init`: monta o config.yaml, o perfil.md e a referência de calibração para uma pessoa.

Três caminhos, que gravam os MESMOS arquivos e passam pela MESMA validação:

* **IA** (`curriculo` informado e uma chave de IA disponível): o currículo é anonimizado
  localmente, a pessoa aprova o texto, a IA propõe áreas, termos e perfil.
* **Manual** (`manual=True`, sem IA): a pessoa escolhe as áreas do catálogo e o papel de cada
  uma (alvo, adjacente, ponte). O `perfil.md` sai como esqueleto para ela preencher.
* O terceiro caminho é o Claude Code (`/personalizar`), que chama estas mesmas funções.

Nada aqui envia o currículo a lugar nenhum sem `aprovado=True`.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import yaml

from . import anonimizar as anon
from . import areas, calibracao, curriculo
from .config import ROOT, avaliacao_cfg, load_config
from .config_io import escrever_config
from .text import normalize
from .validar import normalizar_nivel, validar_config

SENIORIDADE_PADRAO = {
    "junior": ["júnior", "junior", "jr", "jr.", "estágio", "estagiário", "estagiária", "trainee", "entry level",
               "iniciante", "aprendiz", "nível i", "assistente"],
    "pleno": ["pleno", "plena", "pl", "pl.", "mid-level", "mid level", "nível ii"],
    "senior": ["sênior", "senior", "sr", "sr.", "especialista", "specialist", "lead", "líder", "gerente", "manager",
               "coordenador", "coordenadora", "head", "principal", "staff", "diretor", "diretora", "arquiteto",
               "arquiteta", "tech lead", "supervisor", "supervisora", "nível iii"],
}
MAX_TERMOS_BUSCA = 8
MAX_HABILIDADES = 20


class InitErro(Exception):
    """Entrada incompleta ou inválida; a mensagem diz o que corrigir."""


def _slug(nome: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", normalize(nome)).strip("_") or "categoria"


def _parse_areas(itens: list[str], papel_padrao: str = "alvo") -> list[tuple[str, str]]:
    sel = []
    for item in itens or []:
        slug, _, papel = item.partition(":")
        sel.append((slug.strip(), (papel or papel_padrao).strip()))
    return sel


def perfil_esqueleto(objetivo: str, nivel: str, cidade: str, uf: str, nomes_areas: list[str]) -> str:
    base = (ROOT / "perfil.example.md").read_text(encoding="utf-8")
    base = re.sub(r"<!--.*?-->\s*", "", base, flags=re.S)
    obj = (f"**Objetivo:** {objetivo.strip() or ', '.join(nomes_areas)}, nível {nivel}. "
           f"Base em {cidade}/{uf}.")
    return re.sub(r"\*\*Objetivo:\*\*.*?\n\n", obj + "\n\n", base, count=1, flags=re.S)


def previa_anonimizada(e: dict) -> tuple[str, dict]:
    """O texto EXATO que seria enviado à IA e o que foi removido, para a pessoa aprovar."""
    texto = curriculo.ler_texto(e["curriculo"])
    if e.get("anonimizar", True):
        return anon.anonimizar(texto, nomes=e.get("nomes"), ocultar=e.get("ocultar"))
    return texto, {}


def executar_init(e: dict, raiz: Path | None = None, proposta_fn=None) -> dict:
    """Executa o `init`. `e` traz as respostas; devolve o resultado (caminhos, avisos, validação).

    Chaves de `e`: estados, cidade, uf, alcance, remoto, nivel, objetivo, curriculo, manual, areas,
    anonimizar, nomes, ocultar, aprovado, quero, nao_quero, sobrescrever.
    """
    raiz = Path(raiz or ROOT)
    avisos: list[str] = []
    estados = [s for s in (e.get("estados") or []) if s]
    remoto = (e.get("remoto") or "aceitar").lower()
    regiao = {"estados": estados, "base": {"cidade": e.get("cidade") or "", "uf": e.get("uf") or (estados[0] if len(estados) == 1 else "")},
              "alcance": e.get("alcance") or "regiao_imediata", "cidades": [], "apelidos": {}, "remoto": remoto,
              "fuso": "America/Sao_Paulo", "idioma_ia": "pt-BR"}
    if remoto == "somente":
        regiao["base"], regiao["estados"] = {"cidade": "", "uf": ""}, []

    # ----------------------------------------------------------------- áreas, termos e perfil
    proposta, perfil_md = None, None
    selecao: list[tuple[str, str]] = []
    extras: list[dict] = []
    termos: list[str] = []
    excluir: list[str] = []
    habil: list[str] = []
    if e.get("curriculo") and not e.get("manual"):
        if not e.get("aprovado"):
            raise InitErro("o currículo só é enviado à IA depois de você aprovar o texto anonimizado "
                           "(aprovado=True / --sim).")
        texto = curriculo.ler_texto(e["curriculo"])
        if e.get("anonimizar", True):
            texto, _ = anon.anonimizar(texto, nomes=e.get("nomes"), ocultar=e.get("ocultar"))
        fn = proposta_fn or (lambda t, o, n: curriculo.propor(t, o, avaliacao_cfg(load_config(raiz / "config.yaml")
                                                                                   if (raiz / "config.yaml").exists() else {}), n))
        proposta = fn(texto, e.get("objetivo") or "", e.get("nivel"))
        selecao = [(a["slug"], a["papel"]) for a in proposta["areas"]]
        extras = proposta["categorias_extras"]
        termos, excluir, habil = proposta["termos_busca"], proposta["excluir_titulo"], proposta["habilidades"]
        perfil_md = proposta.get("perfil_md")
        avisos += [f"IA: {a}" for a in proposta.get("avisos", [])]
        if proposta.get("areas_fora_do_catalogo"):
            avisos.append("a IA citou áreas fora do catálogo e elas foram ignoradas: "
                          + ", ".join(map(str, proposta["areas_fora_do_catalogo"])))
    else:
        selecao = _parse_areas(e.get("areas") or [])
        if not selecao:
            raise InitErro("informe ao menos uma área (areas=['slug', ...]) ou um currículo. "
                           "Veja o catálogo com `python -m vagas_monitor init --listar-areas`.")
    try:
        comp = areas.compor(selecao) if selecao else {"categorias": {}, "termos_busca": [], "excluir_titulo": [], "habilidades": []}
    except (KeyError, ValueError) as err:
        raise InitErro(str(err.args[0])) from err

    categorias = comp["categorias"]
    base_prio = len(categorias)
    for i, ex in enumerate(extras, 1):  # áreas fora do catálogo
        bonus = {"alvo": 10, "adjacente": 3, "ponte": areas.BONUS_PONTE}[ex["papel"]]
        categorias[_slug(ex["nome"])] = {"nome": ex["nome"], "prioridade": base_prio + i, "bonus": bonus,
                                         "titulo": ex["titulo"], "descricao": ex.get("descricao") or []}
    termos_final = list(dict.fromkeys(termos + comp["termos_busca"]))[:MAX_TERMOS_BUSCA]
    habil_final = list(dict.fromkeys(habil + comp["habilidades"]))[:MAX_HABILIDADES]
    betas = [areas.carregar(s)["nome"] for s, _ in selecao if areas.carregar(s).get("status") == "beta"]
    if betas:
        avisos.append("categorias em fase beta (geradas com IA, sem validação de quem trabalha na área): "
                      + ", ".join(betas) + ". Calibre com vagas reais.")

    nivel = normalizar_nivel(e.get("nivel") or (proposta or {}).get("nivel_sugerido"))
    if not nivel:
        raise InitErro("informe o nível (nivel='junior' etc.): estagio, junior, pleno, senior ou lideranca.")

    # ----------------------------------------------------------------- escreve config e perfil
    cfg_path, perfil_path = raiz / "config.yaml", raiz / "perfil.md"
    atual = (yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}) if cfg_path.exists() else {}
    novo = dict(atual)
    novo.update(regiao=regiao, alvo={"nivel": nivel, "aceita_niveis": (atual.get("alvo") or {}).get("aceita_niveis", [])},
                termos_busca=termos_final, categorias=categorias,
                excluir_titulo=list(dict.fromkeys((atual.get("excluir_titulo") or []) + excluir + comp["excluir_titulo"])),
                habilidades=habil_final)
    novo.setdefault("senioridade", SENIORIDADE_PADRAO)
    if not novo["senioridade"]:
        novo["senioridade"] = SENIORIDADE_PADRAO
    if cfg_path.exists():
        shutil.copyfile(cfg_path, cfg_path.with_suffix(".yaml.bak"))
    escrever_config(novo, cfg_path)

    nomes_areas = [areas.carregar(s)["nome"] for s, p in selecao if p == "alvo"] or [c["nome"] for c in categorias.values()][:1]
    perfil_final = perfil_md or perfil_esqueleto(e.get("objetivo") or "", nivel, regiao["base"]["cidade"] or "",
                                                 regiao["base"]["uf"] or "", nomes_areas)
    if perfil_path.exists():
        shutil.copyfile(perfil_path, perfil_path.with_suffix(".md.bak"))
    perfil_path.write_text(perfil_final, encoding="utf-8", newline="")

    # ----------------------------------------------------------------- validação e medição
    cfg_carregado = load_config(cfg_path)
    pendencias = validar_config(cfg_carregado)
    medicao = None
    quero, nao_quero = e.get("quero") or [], e.get("nao_quero") or []
    if quero or nao_quero:
        calibracao.gravar_referencia(raiz / "calibracao" / "referencia.yaml", quero, nao_quero)
        medicao = calibracao.medir(cfg_carregado, quero, nao_quero)
    if not e.get("curriculo") or e.get("manual"):
        avisos.append("perfil.md é um esqueleto: preencha formação, experiência e habilidades "
                      "(a avaliação por IA lê esse texto).")
    return {"config": cfg_path, "perfil": perfil_path, "pendencias": pendencias, "avisos": avisos,
            "medicao": medicao, "categorias": {k: v["nome"] for k, v in categorias.items()},
            "termos_busca": termos_final, "nivel": nivel, "cidades": cfg_carregado["cidades"][:12]}
