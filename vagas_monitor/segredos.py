"""`publicar-secrets`: grava no GitHub os secrets que estão no `.env`, sem passar pelo chat.

Colar token ou senha numa conversa (com pessoa, com IA) é o jeito mais comum de vazar
credencial. Aqui o valor sai do `.env` direto para o `gh secret set`, por entrada padrão
(não aparece na linha de comando nem na lista de processos) e NUNCA é impresso.

Precisa do GitHub CLI autenticado (`gh auth login`). Instalação: winget (Windows), brew
(macOS) ou apt (Debian/Ubuntu); veja guia/02-contas-e-credenciais.md.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

SEGREDOS = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
            "EMAIL_TO", "GEMINI_API_KEY", "ANTHROPIC_API_KEY")


@dataclass
class Resultado:
    nome: str
    ok: bool
    detalhe: str = ""


def ler_env(caminho: str | Path) -> dict[str, str]:
    """Pares CHAVE=valor do .env, sem aspas e sem comentários."""
    out: dict[str, str] = {}
    for linha in Path(caminho).read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        out[chave.strip()] = valor.strip().strip('"').strip("'")
    return out


def eh_placeholder(valor: str) -> bool:
    v = valor.strip().lower()
    return not v or "example.com" in v or v.startswith(("seu", "sua", "preencha", "cole", "xxx", "..."))


def coletar(env_path: str | Path, perfil_path: str | Path | None = None) -> tuple[dict[str, str], list[str]]:
    """(valores a publicar, nomes ignorados por vazio ou placeholder)."""
    env = ler_env(env_path)
    valores, ignorados = {}, []
    for nome in SEGREDOS:
        v = env.get(nome, "")
        if eh_placeholder(v):
            ignorados.append(nome)
            continue
        valores[nome] = v.replace(" ", "") if nome == "SMTP_PASSWORD" else v  # senha de app: sem espaços
    if perfil_path:
        p = Path(perfil_path)
        if p.exists() and p.read_text(encoding="utf-8").strip():
            valores["PERFIL_MD"] = p.read_text(encoding="utf-8")
        else:
            ignorados.append("PERFIL_MD")
    return valores, ignorados


def publicar(valores: dict[str, str], repo: str | None = None, dry_run: bool = False,
             run=subprocess.run, which=shutil.which) -> list[Resultado]:
    """Publica cada segredo com `gh secret set`. Nunca devolve nem imprime o valor."""
    if dry_run:
        return [Resultado(n, True, "seria publicado (ensaio)") for n in valores]
    if not which("gh"):
        return [Resultado(n, False, "GitHub CLI (gh) não encontrado: instale e rode `gh auth login`") for n in valores]
    auth = run(["gh", "auth", "status"], capture_output=True, text=True)
    if auth.returncode != 0:
        return [Resultado(n, False, "gh não está autenticado: rode `gh auth login`") for n in valores]
    out = []
    for nome, valor in valores.items():
        cmd = ["gh", "secret", "set", nome] + (["--repo", repo] if repo else [])
        r = run(cmd, input=valor, capture_output=True, text=True)
        out.append(Resultado(nome, r.returncode == 0, "" if r.returncode == 0 else (r.stderr or "").strip()[:200]))
    return out
