"""Regera dados/municipios.json.gz a partir da API de localidades do IBGE.

O snapshot vive no repositório para o monitor funcionar sem rede e para a
geografia ser verificável. Rode de vez em quando (municípios mudam raramente):

    python tools/atualizar_ibge.py
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import requests

URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
DESTINO = Path(__file__).resolve().parent.parent / "dados" / "municipios.json.gz"


def baixar() -> list[dict]:
    r = requests.get(URL, timeout=60)
    r.raise_for_status()
    out = []
    for m in r.json():
        ri = m["regiao-imediata"]
        uf = ri["regiao-intermediaria"]["UF"]
        out.append({"id": m["id"], "nome": m["nome"], "uf": uf["sigla"], "uf_nome": uf["nome"],
                    "ri": ri["id"], "ri_nome": ri["nome"]})
    return sorted(out, key=lambda x: (x["uf"], x["nome"]))


def main() -> int:
    dados = baixar()
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(DESTINO, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(dados, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(dados)} municípios, {len({d['uf'] for d in dados})} UFs -> {DESTINO} "
          f"({DESTINO.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
