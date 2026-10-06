"""A documentação não pode prometer o que não existe: links, comandos e arquivos citados."""
import re
from pathlib import Path

import pytest

from vagas_monitor.__main__ import main

RAIZ = Path(__file__).resolve().parent.parent
DOCS = [RAIZ / "README.md", RAIZ / "CLAUDE.md", RAIZ / "CONTRIBUTING.md", RAIZ / "SECURITY.md", RAIZ / "ROADMAP.md",
        RAIZ / "CHANGELOG.md", *sorted((RAIZ / "guia").glob("*.md")), *sorted((RAIZ / ".claude" / "commands").glob("*.md"))]


def _links(texto):
    for m in re.finditer(r"\[[^\]]*\]\(([^)\s]+)\)", texto):
        alvo = m.group(1)
        if not alvo.startswith(("http://", "https://", "mailto:", "#")):
            yield alvo


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: p.relative_to(RAIZ).as_posix())
def test_links_relativos_apontam_para_arquivos_que_existem(doc):
    quebrados = []
    for alvo in _links(doc.read_text(encoding="utf-8")):
        caminho = alvo.split("#")[0]
        if caminho and not (doc.parent / caminho).resolve().exists():
            quebrados.append(alvo)
    assert not quebrados, f"{doc.name}: links quebrados: {quebrados}"


def _subcomandos():
    import argparse

    from vagas_monitor import __main__ as m
    capturado = {}
    original = argparse.ArgumentParser.parse_args

    def espiar(self, args=None, namespace=None):
        for acao in self._actions:
            if isinstance(acao, argparse._SubParsersAction):
                capturado["cmds"] = set(acao.choices)
        raise SystemExit(0)

    argparse.ArgumentParser.parse_args = espiar
    try:
        try:
            m.main([])
        except SystemExit:
            pass
    finally:
        argparse.ArgumentParser.parse_args = original
    return capturado["cmds"]


def test_todo_comando_citado_na_documentacao_existe():
    existentes = _subcomandos()
    assert {"init", "doctor", "calibrar", "classificar", "publicar-secrets", "run", "status"} <= existentes
    citados = set()
    for doc in DOCS:
        citados |= set(re.findall(r"python -m vagas_monitor (?:--config \S+ )?([a-z][a-z-]+)", doc.read_text(encoding="utf-8")))
    desconhecidos = citados - existentes
    assert not desconhecidos, f"comandos citados que não existem: {sorted(desconhecidos)}"


def test_todo_arquivo_de_pack_e_guia_citado_existe():
    for doc in DOCS:
        for caminho in re.findall(r"`((?:guia|areas|tools|dados|tests|calibracao)/[A-Za-z0-9_./\-]+\.[a-z]+)`",
                                  doc.read_text(encoding="utf-8")):
            if caminho.endswith(("referencia.yaml", "leak_denylist.local.txt")):
                continue  # arquivos pessoais: o `init` ou a própria pessoa os cria, e o git os ignora
            assert (RAIZ / caminho).exists(), f"{doc.name} cita {caminho}, que não existe"


def test_ajuda_do_cli_lista_os_novos_comandos(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    saida = capsys.readouterr().out
    for cmd in ("init", "doctor", "calibrar", "publicar-secrets", "classificar"):
        assert cmd in saida
