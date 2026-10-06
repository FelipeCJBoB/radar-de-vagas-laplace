"""Geografia do Brasil a partir do snapshot do IBGE (dados/municipios.json.gz).

O monitor não assume estado nem cidade: quem configura informa a UF e uma
cidade-base, e as cidades de interesse saem daqui. O catálogo é o do IBGE, com a
Região Geográfica Imediata, que é a área de deslocamento diária real: reúne a
cidade-base e os municípios vizinhos que dependem dela para trabalho e serviços.

Também concentra as duas constantes de país, para que nenhuma fonte tenha
"Brasil" escrito à mão.
"""
from __future__ import annotations

import gzip
import json
from difflib import get_close_matches
from functools import lru_cache
from pathlib import Path

from .text import normalize

PAIS_NOME = "Brasil"      # sufixo das buscas por localidade (LinkedIn, Indeed)
PAIS_INDEED = "brazil"    # parâmetro `country_indeed` do jobspy

ALCANCES = ("cidade", "regiao_imediata", "estado", "lista")
SNAPSHOT = Path(__file__).resolve().parent.parent / "dados" / "municipios.json.gz"


@lru_cache(maxsize=1)
def municipios() -> tuple[dict, ...]:
    with gzip.open(SNAPSHOT, "rt", encoding="utf-8") as f:
        return tuple(json.load(f))


@lru_cache(maxsize=1)
def ufs() -> dict[str, str]:
    """{sigla: nome} das 27 UFs."""
    return {m["uf"]: m["uf_nome"] for m in municipios()}


def uf_sigla(valor: str) -> str | None:
    """Aceita 'SP', 'sp' ou 'São Paulo' (com ou sem acento) e devolve a sigla."""
    v = normalize(valor or "")
    for sigla, nome in ufs().items():
        if v in (sigla.lower(), normalize(nome)):
            return sigla
    return None


def uf_nome(valor: str) -> str | None:
    sigla = uf_sigla(valor)
    return ufs()[sigla] if sigla else None


def buscar_cidade(nome: str, uf: str | None = None) -> dict | None:
    """Município pelo nome (sem distinguir acento nem caixa), opcionalmente numa UF."""
    alvo = normalize(nome or "")
    sigla = uf_sigla(uf) if uf else None
    achados = [m for m in municipios()
               if normalize(m["nome"]) == alvo and (sigla is None or m["uf"] == sigla)]
    return achados[0] if achados else None


def sugestoes(nome: str, uf: str | None = None, n: int = 3) -> list[str]:
    """Nomes parecidos, para a mensagem de erro de quem digitou errado."""
    sigla = uf_sigla(uf) if uf else None
    base = {normalize(m["nome"]): m["nome"] for m in municipios() if sigla is None or m["uf"] == sigla}
    return [base[k] for k in get_close_matches(normalize(nome), list(base), n=n, cutoff=0.7)]


def cidades_da_regiao_imediata(cidade: str, uf: str) -> list[str]:
    base = buscar_cidade(cidade, uf)
    if not base:
        return []
    return [m["nome"] for m in municipios() if m["ri"] == base["ri"]]


def cidades_do_estado(uf: str) -> list[str]:
    sigla = uf_sigla(uf)
    return [m["nome"] for m in municipios() if m["uf"] == sigla]


def expandir(alcance: str, base_cidade: str, base_uf: str, estados: list[str],
             manual: list[str] | None = None) -> list[str]:
    """Cidades de interesse conforme o alcance escolhido."""
    if alcance == "cidade":
        c = buscar_cidade(base_cidade, base_uf)
        return [c["nome"]] if c else []
    if alcance == "regiao_imediata":
        return cidades_da_regiao_imediata(base_cidade, base_uf)
    if alcance == "estado":
        return [c for e in estados for c in cidades_do_estado(e)]
    if alcance == "lista":
        out = []
        for nome in manual or []:
            achada = next((buscar_cidade(nome, e) for e in estados if buscar_cidade(nome, e)), None)
            out.append(achada["nome"] if achada else nome)
        return out
    return []


def localidade(cidade: str, estados: list[str]) -> str | None:
    """'Campinas, São Paulo, Brasil', para o campo de local do LinkedIn."""
    for e in estados:
        c = buscar_cidade(cidade, e)
        if c:
            return f"{c['nome']}, {c['uf_nome']}, {PAIS_NOME}"
    return None
