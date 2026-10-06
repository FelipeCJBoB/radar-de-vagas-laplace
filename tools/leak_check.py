"""Varre o repositório atrás de segredos e de dados pessoais. Sai com código 1 se achar algo.

    python tools/leak_check.py                 # varre o repositório inteiro
    python tools/leak_check.py --denylist meus_termos.txt

Dois tipos de verificação:

1. **Detectores genéricos** (versionados aqui): chaves de API, token de bot do Telegram,
   token do GitHub, chave privada, CPF, telefone brasileiro e endereço de e-mail.
2. **Lista de bloqueio pessoal** (NUNCA versionada): um termo por linha, em
   `tools/leak_denylist.local.txt` (ignorado pelo git) ou no arquivo apontado por
   `--denylist` / pela variável LEAK_DENYLIST. É onde ficam o seu nome, o seu e-mail,
   seu empregador, sua faculdade. Ela não pode morar no repositório: a lista de termos
   proibidos seria, ela mesma, o vazamento.

Cada pessoa mantém a própria lista. Rode antes de cada push e deixe o CI rodar só os
detectores genéricos.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DENYLIST_LOCAL = Path(__file__).resolve().parent / "leak_denylist.local.txt"

IGNORAR_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", "logs", ".ruff_cache"}
IGNORAR_EXT = {".gz", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pyc", ".zip", ".pdf"}
IGNORAR_ARQ = {"leak_check.py", "test_leak_check.py"}  # contêm os padrões e exemplos plantados

# (nome, regex). Os detectores só pegam o formato; não há como saber se o valor é real.
DETECTORES = [
    ("chave do Google/Gemini", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("chave da Anthropic", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("chave estilo OpenAI", re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    ("token de bot do Telegram", re.compile(r"\b\d{8,10}:[A-Za-z0-9_\-]{35}\b")),
    ("token do GitHub", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("chave privada", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("CPF", re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")),
    ("telefone brasileiro", re.compile(r"(?<!\d)\(?\d{2}\)?[ .-]?9?\d{4}-\d{4}(?!\d)")),
]
EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
EMAILS_PERMITIDOS = re.compile(
    r"@(example\.(com|org|net)|exemplo\.(com|org)(\.br)?|users\.noreply\.github\.com|anthropic\.com)$", re.I)


def carregar_denylist(caminho: Path | None) -> list[str]:
    candidatos = [caminho] if caminho else []
    if os.environ.get("LEAK_DENYLIST"):
        candidatos.append(Path(os.environ["LEAK_DENYLIST"]))
    candidatos.append(DENYLIST_LOCAL)
    for c in candidatos:
        if c and c.exists():
            linhas = c.read_text(encoding="utf-8").splitlines()
            return [t.strip() for t in linhas if t.strip() and not t.lstrip().startswith("#")]
    return []


def arquivos(raiz: Path):
    for p in sorted(raiz.rglob("*")):
        if not p.is_file() or p.suffix.lower() in IGNORAR_EXT or p.name in IGNORAR_ARQ:
            continue
        if any(parte in IGNORAR_DIRS for parte in p.relative_to(raiz).parts):
            continue
        if p.name == DENYLIST_LOCAL.name:
            continue
        yield p


def varrer_texto(texto: str, denylist: list[str] | None = None) -> list[str]:
    """Achados (sem o valor completo, para o relatório não repetir o vazamento)."""
    achados: list[str] = []
    for nome, rx in DETECTORES:
        for m in rx.finditer(texto):
            achados.append(f"{nome}: {_mascarar(m.group(0))}")
    for m in EMAIL.finditer(texto):
        if not EMAILS_PERMITIDOS.search(m.group(0)):
            achados.append(f"e-mail: {_mascarar(m.group(0))}")
    baixo = texto.lower()
    for termo in denylist or []:
        if termo.lower() in baixo:
            achados.append("termo da lista de bloqueio pessoal")
    return achados


def _mascarar(v: str) -> str:
    return v if len(v) <= 6 else v[:3] + "…" + v[-2:]


def varrer(raiz: Path, denylist: list[str] | None = None) -> list[tuple[str, int, str]]:
    """[(arquivo relativo, linha, achado)]."""
    out = []
    for p in arquivos(raiz):
        try:
            linhas = p.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for n, linha in enumerate(linhas, 1):
            for a in varrer_texto(linha, denylist):
                out.append((p.relative_to(raiz).as_posix(), n, a))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", type=Path, default=RAIZ)
    ap.add_argument("--denylist", type=Path, help="arquivo com um termo pessoal por linha")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    deny = carregar_denylist(a.denylist)
    achados = varrer(a.raiz, deny)
    if not deny:
        print("aviso: sem lista de bloqueio pessoal (tools/leak_denylist.local.txt); só os detectores genéricos rodaram.")
    if achados:
        print(f"{len(achados)} achado(s):")
        for arq, n, ach in achados:
            print(f"  {arq}:{n}  {ach}")
        return 1
    print("nada encontrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
