"""Packs de área: categorias prontas por área de atuação (`areas/*.yaml`).

Um pack reúne os termos que classificam vagas de uma área (título e descrição), os
homônimos a excluir, as habilidades de mercado e os termos de busca, mais exemplos de
títulos que DEVEM e que NÃO DEVEM entrar. Os exemplos viram teste, então mudar um pack
sem quebrar a classificação dele é verificável.

Packs com `status: beta` são sementes geradas com IA e ainda sem validação de quem
trabalha na área; o `init` avisa isso. Contribuir um pack ou validar um beta é a
melhor forma de ajudar o projeto.
"""
from __future__ import annotations

from difflib import get_close_matches

import yaml

from .config import ROOT

PASTA = ROOT / "areas"
PAPEIS = ("alvo", "adjacente", "ponte")
# Papel -> bônus de pontuação. Alvo: o primeiro vale mais e os seguintes descem de 2 em 2.
# Ponte é negativo de propósito: aparece no radar sem disputar o topo com o que a pessoa quer.
BONUS_ALVO = (12, 10, 8, 6)
BONUS_ADJACENTE = 3
BONUS_PONTE = -8


def listar() -> dict[str, dict]:
    """{slug: pack} de todos os packs, em ordem alfabética."""
    out = {}
    for arq in sorted(PASTA.glob("*.yaml")):
        out[arq.stem] = yaml.safe_load(arq.read_text(encoding="utf-8"))
    return out


def carregar(slug: str) -> dict:
    arq = PASTA / f"{slug}.yaml"
    if not arq.exists():
        dicas = get_close_matches(slug, [a.stem for a in PASTA.glob("*.yaml")], n=3)
        raise KeyError(f"pack '{slug}' não existe." + (f" Parecidos: {', '.join(dicas)}." if dicas else ""))
    return yaml.safe_load(arq.read_text(encoding="utf-8"))


def chave(slug: str) -> str:
    return slug.replace("-", "_")


def compor(selecao: list[tuple[str, str]]) -> dict:
    """Monta as seções do config a partir de [(slug, papel)].

    Devolve `categorias`, `termos_busca`, `excluir_titulo` (sempre vazio: as exclusões dos
    packs são por categoria; a lista global é só da pessoa) e `habilidades`. A prioridade
    segue a ordem alvo, adjacente, ponte, e dentro de cada papel a ordem informada.
    """
    for slug, papel in selecao:
        if papel not in PAPEIS:
            raise ValueError(f"papel '{papel}' inválido para '{slug}'. Use: {', '.join(PAPEIS)}.")
    ordenada = sorted(selecao, key=lambda sp: PAPEIS.index(sp[1]))  # estável: preserva a ordem dentro do papel
    categorias: dict[str, dict] = {}
    termos: list[str] = []
    excluir: list[str] = []  # fica vazia, de propósito
    habil: list[str] = []
    n_alvo = 0
    for prio, (slug, papel) in enumerate(ordenada, 1):
        pack = carregar(slug)
        if papel == "alvo":
            bonus = BONUS_ALVO[min(n_alvo, len(BONUS_ALVO) - 1)]
            n_alvo += 1
        else:
            bonus = BONUS_ADJACENTE if papel == "adjacente" else BONUS_PONTE
        categorias[chave(slug)] = {"nome": pack["nome"], "prioridade": prio, "bonus": bonus,
                                   "titulo": list(pack["titulo"]), "descricao": list(pack["descricao"])}
        # os homônimos do pack valem só para a categoria dele (ver filters.classify)
        if pack.get("excluir_titulo"):
            categorias[chave(slug)]["excluir_titulo"] = list(pack["excluir_titulo"])
        for destino, origem in ((termos, "termos_busca"), (habil, "habilidades_mercado")):
            destino.extend(t for t in pack.get(origem) or [] if t not in destino)
    return {"categorias": categorias, "termos_busca": termos, "excluir_titulo": excluir, "habilidades": habil}
