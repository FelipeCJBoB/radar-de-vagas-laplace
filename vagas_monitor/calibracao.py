"""Calibração: transforma "parece certo" em medida.

Dois instrumentos:

1. **Conjunto de referência** (`calibracao/referencia.yaml`): títulos de vagas que a pessoa
   QUER e que NÃO QUER. `medir` calcula o recall (quantas das queridas o monitor captura) e o
   corte (quantas das indesejadas ele descarta) e diz qual termo decidiu cada erro. Offline.
2. **Sondagem do mercado** (`sondar`): olha os títulos reais da região e mostra (a) o que as
   vagas que o config HOJE descarta têm em comum, para achar vocabulário que faltou, e (b) quais
   títulos cada termo atual captura, para expor homônimos antes que virem erro.

Foi comparando à mão o que o monitor capturava com as vagas em que a pessoa se candidatou
que apareceram os pontos cegos do primeiro monitor ("Implantador de Sistemas" e as vagas
de SAP nunca entravam). Aqui isso é um comando.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from . import filters
from .models import Job
from .text import any_term, normalize

META_PADRAO = 0.8
PARADAS = {"de", "da", "do", "das", "dos", "e", "em", "para", "com", "a", "o", "na", "no", "ii", "i", "iii", "pl", "jr",
           "sr", "vaga", "vagas", "junior", "pleno", "senior", "estagio", "estagiario", "remoto", "remota", "home", "office",
           "hibrido", "presencial", "temporario", "efetivo", "pcd", "area", "setor", "unidade"}


def _vaga(titulo: str) -> Job:
    return Job(source="ref", title=titulo, company="-", url="-")


def decide(titulo: str, cfg: dict) -> tuple[bool, str]:
    """(entra?, motivo curto) para um título, pelas mesmas regras da rodada."""
    nt = normalize(titulo)
    global_ex = any_term(nt, cfg.get("excluir_titulo") or [])
    if global_ex:
        return False, f"excluída por excluir_titulo ({', '.join(global_ex)})"
    primaria, _, _ = filters.classify(_vaga(titulo), cfg.get("categorias") or {})
    if not primaria:
        return False, "nenhuma categoria casou"
    cat = cfg["categorias"][primaria]
    por_titulo = any_term(nt, cat.get("titulo") or [])
    return True, f"{cat['nome']} por " + (f"título: {', '.join(por_titulo)}" if por_titulo else "descrição")


def carregar_referencia(caminho: str | Path) -> dict:
    p = Path(caminho)
    if not p.exists():
        raise FileNotFoundError(f"conjunto de referência não encontrado: {p}")
    d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {"quero": [str(t) for t in d.get("quero") or []], "nao_quero": [str(t) for t in d.get("nao_quero") or []]}


def gravar_referencia(caminho: str | Path, quero: list[str], nao_quero: list[str]) -> None:
    p = Path(caminho)
    p.parent.mkdir(parents=True, exist_ok=True)
    cab = ("# Vagas de referência da calibração: títulos que você QUER receber e que NÃO quer.\n"
           "# Este arquivo é pessoal e fica fora do git (veja .gitignore).\n")
    p.write_text(cab + yaml.safe_dump({"quero": quero, "nao_quero": nao_quero}, allow_unicode=True, sort_keys=False),
                 encoding="utf-8", newline="")


def medir(cfg: dict, quero: list[str], nao_quero: list[str], meta: float = META_PADRAO) -> dict:
    """Recall das queridas, corte das indesejadas e a lista dos erros com o porquê."""
    perdidas = [(t, decide(t, cfg)[1]) for t in quero if not decide(t, cfg)[0]]
    vazaram = [(t, decide(t, cfg)[1]) for t in nao_quero if decide(t, cfg)[0]]
    recall = (len(quero) - len(perdidas)) / len(quero) if quero else None
    corte = (len(nao_quero) - len(vazaram)) / len(nao_quero) if nao_quero else None
    ok = all(m is None or m >= meta for m in (recall, corte)) and (recall is not None or corte is not None)
    return {"recall": recall, "corte": corte, "perdidas": perdidas, "vazaram": vazaram, "meta": meta,
            "n_quero": len(quero), "n_nao_quero": len(nao_quero), "ok": ok}


def relatorio_medicao(m: dict) -> list[str]:
    def pct(v):
        return "sem exemplos" if v is None else f"{v:.0%}"
    linhas = [f"Recall das vagas queridas : {pct(m['recall'])}  ({m['n_quero'] - len(m['perdidas'])}/{m['n_quero']})",
              f"Corte das indesejadas     : {pct(m['corte'])}  ({m['n_nao_quero'] - len(m['vazaram'])}/{m['n_nao_quero']})",
              f"Meta: {m['meta']:.0%}"]
    if m["perdidas"]:
        linhas += ["", "FALTARAM (você queria, o monitor descarta):"] + [f"  - {t}: {why}" for t, why in m["perdidas"]]
        linhas.append("  -> acrescente o título em `titulo` da categoria certa, ou um termo de busca.")
    if m["vazaram"]:
        linhas += ["", "SOBRARAM (você não quer, o monitor aceita):"] + [f"  - {t}: {why}" for t, why in m["vazaram"]]
        linhas.append("  -> troque o termo por uma expressão mais específica ou use excluir_titulo na categoria.")
    linhas += ["", "RESULTADO: " + ("dentro da meta." if m["ok"] else "abaixo da meta, ajuste e rode de novo.")]
    return linhas


# --------------------------------------------------------------------------- sondagem
def _ngramas(titulo: str, n_max: int = 3, ignorar: frozenset | set = frozenset()):
    palavras = [p for p in re.findall(r"[a-z0-9]+", normalize(titulo))
                if p not in PARADAS and p not in ignorar and not p.isdigit() and len(p) > 1]
    for n in range(1, n_max + 1):
        for i in range(len(palavras) - n + 1):
            yield " ".join(palavras[i:i + n])


def _geografia_do_config(cfg: dict) -> set[str]:
    """Palavras de lugar (cidades, estados, UFs): aparecem em muito título e não dizem nada sobre a função."""
    from .geografia import ufs
    lugares = set(ufs()) | set(ufs().values()) | set(cfg.get("cidades") or []) | set(cfg.get("_estados") or [])
    return {w for lugar in lugares for w in re.findall(r"[a-z0-9]+", normalize(lugar)) if len(w) > 1}


def sondar(cfg: dict, titulos: list[str], minimo: int = 3, top: int = 15, amostras: int = 3) -> dict:
    """Analisa títulos reais de vagas da região contra o config atual.

    `candidatos`: expressões frequentes nos títulos que o config descarta (vocabulário que
    pode estar faltando). `termos`: para cada termo de título das categorias, quantas vagas
    ele captura e uma amostra (homônimos aparecem como amostras de áreas diferentes).
    """
    descartados, capturados = [], []
    for t in titulos:
        (capturados if decide(t, cfg)[0] else descartados).append(t)
    freq: Counter = Counter()
    exemplos: dict[str, list[str]] = defaultdict(list)
    lugares = _geografia_do_config(cfg)
    for t in descartados:
        for g in set(_ngramas(t, ignorar=lugares)):
            freq[g] += 1
            if len(exemplos[g]) < amostras:
                exemplos[g].append(t)
    # só vale como candidato o n-grama que não é pedaço de um termo que já existe e que é
    # frequente o bastante; os mais longos primeiro (mais específicos)
    ja_usados = {normalize(x) for c in (cfg.get("categorias") or {}).values() for x in (c.get("titulo") or [])}
    candidatos = [(g, n, exemplos[g]) for g, n in freq.items() if n >= minimo and g not in ja_usados]
    candidatos.sort(key=lambda x: (-x[1], -len(x[0].split())))
    # "atendente restaurante" (26x) já diz o que "restaurante" (26x) diria: o pedaço com a mesma
    # contagem de um n-grama maior que o contém é redundante
    escolhidos: list[tuple[str, int, list[str]]] = []
    for g, n, ex in candidatos:
        if not any(n == n2 and f" {g} " in f" {g2} " for g2, n2, _ in escolhidos):
            escolhidos.append((g, n, ex))
    candidatos = escolhidos
    termos = []
    for chave, cat in (cfg.get("categorias") or {}).items():
        for termo in cat.get("titulo") or []:
            pegos = [t for t in capturados if any_term(normalize(t), [termo])]
            if pegos:
                termos.append({"categoria": cat["nome"], "termo": termo, "n": len(pegos), "amostra": pegos[:amostras]})
    termos.sort(key=lambda x: -x["n"])
    return {"total": len(titulos), "capturados": len(capturados), "descartados": len(descartados),
            "candidatos": candidatos[:top], "termos": termos}


def relatorio_sondagem(s: dict) -> list[str]:
    linhas = [f"Títulos analisados: {s['total']}  |  o config captura {s['capturados']} e descarta {s['descartados']}", ""]
    linhas.append("TERMOS ATUAIS e o que cada um captura (leia as amostras: homônimos aparecem aqui):")
    for t in s["termos"][:20]:
        linhas.append(f"  [{t['categoria']}] '{t['termo']}': {t['n']} vaga(s)")
        linhas += [f"      ex.: {a}" for a in t["amostra"]]
    linhas += ["", "CANDIDATOS: expressões frequentes nos títulos que o config DESCARTA "
                   "(se alguma é uma vaga que você quer, vira termo):"]
    for g, n, ex in s["candidatos"]:
        linhas.append(f"  '{g}': {n}x   ex.: {ex[0]}")
    if not s["candidatos"]:
        linhas.append("  (nenhuma expressão frequente fora do config)")
    return linhas


def coletar_titulos(cfg: dict, dias: int = 30, fontes: tuple[str, ...] = ("gupy",)) -> tuple[list[str], dict]:
    """Títulos de vagas reais da região (dentro do escopo geográfico), com as fontes pedidas.

    Só a Gupy por padrão: é rápida (segundos) e cobre o estado inteiro. LinkedIn e Indeed levam
    minutos por rodada; peça com `fontes=("gupy", "indeed", "linkedin")` quando valer o tempo.
    """
    from . import pipeline

    skip = tuple(f for f in ("gupy", "indeed", "linkedin") if f not in fontes)
    erros: dict = {}
    jobs, _ = pipeline.collect_all(cfg, dias, erros, skip)
    return [j.title for j in jobs if pipeline.dentro_do_escopo(j, cfg)], erros
