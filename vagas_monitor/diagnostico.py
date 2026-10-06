"""`doctor`: confere tudo o que precisa estar certo antes de a rodada começar.

Nasceu de três defeitos que passaram semanas sem aviso: token do Telegram revogado (401),
senha de app do Gmail ausente e endpoint da Gupy que passou a responder 404. Cada um sai
daqui como uma linha com o que está errado e como corrigir, sem esperar a rodada.

Cada verificação devolve `Item(nivel, titulo, detalhe, correcao)`; `nivel` é "ok", "aviso" ou
"erro". Só "erro" faz o comando sair com código 1.
"""
from __future__ import annotations

import json
import platform
import smtplib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import requests

from . import __version__, geografia
from .config import ROOT, avaliacao_cfg, env, load_config, load_profile
from .state import State
from .validar import validar_config

TIMEOUT = 20
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) radar-de-vagas-laplace/doctor"}
GUPY = "https://portal.gupy.io/api/job-search/jobs"
LINKEDIN = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
CAMPOS_GUPY = ("id", "name", "jobUrl", "publishedDate", "workplaceType")


@dataclass
class Item:
    nivel: str  # ok | aviso | erro
    titulo: str
    detalhe: str = ""
    correcao: str = ""


def _ok(t, d=""):
    return Item("ok", t, d)


def _aviso(t, d, c=""):
    return Item("aviso", t, d, c)


def _erro(t, d, c=""):
    return Item("erro", t, d, c)


# --------------------------------------------------------------------------- verificações
def verificar_config(cfg: dict) -> list[Item]:
    pend = validar_config(cfg)
    if not pend:
        return [_ok("config.yaml", f"{len(cfg['cidades'])} cidade(s), {len(cfg['categorias'])} categoria(s), "
                                    f"nível {cfg['alvo']['nivel']}")]
    return [_erro("config.yaml incompleto", p, "rode `python -m vagas_monitor init` ou veja guia/04-personalizar.md")
            for p in pend]


def verificar_perfil(cfg: dict) -> list[Item]:
    texto = load_profile(cfg)
    if not texto.strip():
        return [_aviso("perfil", "nenhum perfil (perfil.md ou PERFIL_MD): a avaliação por IA fica sem contexto",
                       "copie perfil.example.md para perfil.md e preencha")]
    if "[cargo ou área" in texto or "[curso, instituição" in texto:
        return [_aviso("perfil", "o perfil ainda é o modelo, com campos entre colchetes",
                       "preencha formação, experiência e habilidades em perfil.md")]
    return [_ok("perfil", f"{len(texto)} caracteres" + (" (via PERFIL_MD)" if env("PERFIL_MD") else ""))]


def verificar_telegram(rede: bool = True) -> list[Item]:
    token, chat = env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_CHAT_ID")
    if not token and not chat:
        return [_aviso("Telegram", "desligado (sem TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID)",
                       "guia/02-contas-e-credenciais.md, seção 1")]
    if not token or not chat:
        faltou = "TELEGRAM_CHAT_ID" if token else "TELEGRAM_BOT_TOKEN"
        return [_erro("Telegram", f"falta {faltou}", "rode `python -m vagas_monitor setup-telegram`" if token
                      else "crie o bot no @BotFather")]
    if not rede:
        return [_ok("Telegram", "variáveis presentes (não testado: --offline)")]
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=TIMEOUT)
    except requests.RequestException as e:
        return [_aviso("Telegram", f"sem conexão com a API: {e}")]
    if r.status_code == 401:
        return [_erro("Telegram: token inválido (401)", "o token foi revogado ou está errado",
                      "gere outro no @BotFather (/mybots > API Token) e atualize o .env E o secret do GitHub")]
    if not r.ok:
        return [_erro("Telegram", f"HTTP {r.status_code}")]
    try:
        c = requests.get(f"https://api.telegram.org/bot{token}/getChat", params={"chat_id": chat}, timeout=TIMEOUT)
    except requests.RequestException as e:
        return [_aviso("Telegram", f"bot ok, mas getChat falhou: {e}")]
    if not c.ok:
        return [_erro("Telegram: chat não encontrado", f"o bot existe, mas não enxerga o chat {chat}",
                      "mande uma mensagem ao bot e rode `python -m vagas_monitor setup-telegram`")]
    return [_ok("Telegram", f"bot @{r.json().get('result', {}).get('username', '?')} e chat ok")]


def verificar_email(rede: bool = True) -> list[Item]:
    usuario, senha, para = env("SMTP_USER"), env("SMTP_PASSWORD"), env("EMAIL_TO")
    if not usuario and not senha and not para:
        return [_aviso("E-mail", "desligado (sem SMTP_USER, SMTP_PASSWORD e EMAIL_TO)",
                       "guia/02-contas-e-credenciais.md, seção 2, ou deixe só o Telegram")]
    faltam = [n for n, v in (("SMTP_USER", usuario), ("SMTP_PASSWORD", senha), ("EMAIL_TO", para)) if not v]
    if faltam:
        return [_erro("E-mail", f"faltam: {', '.join(faltam)}",
                      "gere a senha de app em myaccount.google.com/apppasswords (exige verificação em 2 etapas LIGADA)")]
    itens = []
    if " " in senha:
        itens.append(_aviso("E-mail: SMTP_PASSWORD tem espaços", "a senha de app é de 16 letras, sem espaços",
                            "cole sem os espaços, no .env e no secret"))
    if not rede:
        return itens + [_ok("E-mail", "variáveis presentes (não testado: --offline)")]
    try:
        with smtplib.SMTP_SSL(env("SMTP_HOST", "smtp.gmail.com"), int(env("SMTP_PORT", "465")), timeout=TIMEOUT) as s:
            s.login(usuario, senha.replace(" ", ""))
    except smtplib.SMTPAuthenticationError:
        return itens + [_erro("E-mail: login recusado", "usuário ou senha de app incorretos",
                              "gere uma nova senha de app; confirme que a verificação em 2 etapas está LIGADA")]
    except (OSError, smtplib.SMTPException) as e:
        return itens + [_aviso("E-mail", f"não consegui conectar: {e}")]
    return itens + [_ok("E-mail", f"login ok como {usuario}")]


def verificar_ia(cfg: dict, chamar: bool = False) -> list[Item]:
    from .enrich import escolher_provedor
    from .providers import DISPONIVEIS

    aval = avaliacao_cfg(cfg)
    if str(aval.get("provedor", "auto")).lower() in ("nenhum", "none", "off", "false"):
        return [_ok("IA", "desligada (avaliacao.provedor: nenhum)")]
    nome = escolher_provedor(aval)
    if not nome:
        return [_aviso("IA", "nenhuma chave (GEMINI_API_KEY ou ANTHROPIC_API_KEY): o monitor roda sem notas",
                       "chave grátis do Gemini em aistudio.google.com/apikey")]
    if not chamar:
        return [_ok("IA", f"provedor {DISPONIVEIS[nome].NOME} com chave presente (use --ia para testar com uma chamada real)")]
    from .enrich import enrich
    from .models import Job
    from .validar import contexto_ia

    vaga = Job(source="teste", title="Vaga de teste", company="Empresa Exemplo", url="https://exemplo/1",
               location="Cidade Exemplo", workplace="hybrid", description="Rotina da área. Formação em andamento é aceita.")
    vaga.seniority = "junior"
    feito, motivo = enrich([vaga], load_profile(cfg) or "Perfil de teste.",
                           {**aval, "max_vagas": 1, "_contexto": contexto_ia(cfg)})
    if feito:
        return [_ok("IA", f"{DISPONIVEIS[nome].NOME} respondeu (nota de teste {vaga.fit}/10)")]
    return [_erro(f"IA: {DISPONIVEIS[nome].NOME} não respondeu", motivo or "sem resposta utilizável",
                  "confira a chave e o saldo; o monitor segue sem notas se a IA falhar")]


def verificar_gupy(cfg: dict) -> list[Item]:
    estado = (cfg.get("_estados") or ["São Paulo"])[0]
    try:
        r = requests.get(GUPY, params={"jobName": "", "state": estado, "limit": 5, "offset": 0},
                         headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as e:
        return [_aviso("Gupy", f"sem conexão: {e}")]
    if r.status_code == 404:
        return [_erro("Gupy: endpoint não existe (404)", "a Gupy mudou a API pública",
                      "guia/09-solucao-de-problemas.md, seção 'Fonte com zero vagas'; confira se há versão nova do modelo")]
    if not r.ok:
        return [_erro("Gupy", f"HTTP {r.status_code}")]
    dados = (r.json() or {}).get("data") or []
    if not dados:
        return [_aviso("Gupy", f"a API respondeu, mas sem vagas em {estado}")]
    faltam = [c for c in CAMPOS_GUPY if c not in dados[0]]
    if faltam:
        return [_erro("Gupy: formato mudou", f"campos ausentes: {', '.join(faltam)}",
                      "o coletor (sources/gupy.py) precisa ser atualizado")]
    return [_ok("Gupy", f"API respondendo, {estado} com vagas")]


def verificar_linkedin(cfg: dict) -> list[Item]:
    estado = (cfg.get("_estados") or ["São Paulo"])[0]
    try:
        r = requests.get(LINKEDIN, params={"keywords": "analista", "location": f"{estado}, {geografia.PAIS_NOME}",
                                           "start": 0}, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as e:
        return [_aviso("LinkedIn", f"sem conexão: {e}")]
    if r.status_code == 429:
        return [_aviso("LinkedIn", "limite de requisições (429); o coletor espera e tenta de novo na rodada")]
    if not r.ok:
        return [_erro("LinkedIn", f"HTTP {r.status_code}", "o endpoint público de convidado pode ter mudado")]
    if "base-search-card" not in r.text and "job-search-card" not in r.text:
        return [_erro("LinkedIn: formato mudou", "a resposta não tem cartões de vaga",
                      "o coletor (sources/linkedin.py) precisa ser atualizado")]
    return [_ok("LinkedIn", "endpoint de convidado respondendo")]


def verificar_estado() -> list[Item]:
    arq = ROOT / "state" / "seen.json"
    if not arq.exists():
        return [_aviso("estado", "state/seen.json não existe", "a primeira rodada o cria")]
    try:
        st = State(arq)
    except (json.JSONDecodeError, OSError) as e:
        return [_erro("estado corrompido", str(e), "restaure state/seen.json do git (git checkout state/seen.json)")]
    if st.first_run:
        return [_ok("estado", "nenhuma rodada ainda: a primeira usa a janela de 30 dias")]
    return [_ok("estado", f"última rodada {st.data.get('last_run')}, {len(st.data['jobs'])} vagas conhecidas")]


def verificar_segredos_no_git() -> list[Item]:
    if not (ROOT / ".git").exists():
        return []
    try:
        r = subprocess.run(["git", "ls-files", "--error-unmatch", ".env"], cwd=ROOT, capture_output=True, text=True)
    except OSError:
        return []
    if r.returncode == 0:
        return [_erro(".env está versionado", "tokens e senhas estão no git",
                      "git rm --cached .env, REVOGUE as credenciais e gere outras")]
    return [_ok("segredos", ".env fora do git")]


def verificar_versao(cfg: dict) -> list[Item]:
    repo = ((cfg.get("modelo") or {}).get("repositorio") or "").strip()
    if not repo:
        return []
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}/releases/latest", timeout=TIMEOUT)
    except requests.RequestException:
        return []
    if not r.ok:
        return []
    ultima = str(r.json().get("tag_name", "")).lstrip("v")
    if ultima and tuple(map(int, (ultima.split(".") + ["0", "0"])[:3])) > tuple(map(int, __version__.split(".")[:3])):
        return [_aviso(f"versão {__version__} atrás da {ultima}",
                       "o modelo tem correções (fontes mudam e são consertadas lá)",
                       f"veja o CHANGELOG em github.com/{repo} e guia/08-atualizar-do-modelo.md")]
    return [_ok("versão", f"{__version__} (a mais recente)")]


# --------------------------------------------------------------------------- orquestração
def diagnosticar(cfg: dict, rede: bool = True, ia: bool = False) -> list[Item]:
    itens = [_ok("ambiente", f"Python {sys.version.split()[0]} em {platform.system()}, modelo {__version__}")]
    itens += verificar_config(cfg)
    itens += verificar_perfil(cfg)
    itens += verificar_telegram(rede)
    itens += verificar_email(rede)
    itens += verificar_ia(cfg, ia)
    if rede and not validar_config(cfg):
        fontes = cfg.get("fontes") or {}
        if (fontes.get("gupy") or {}).get("ativo", True):
            itens += verificar_gupy(cfg)
        if (fontes.get("linkedin") or {}).get("ativo", True):
            itens += verificar_linkedin(cfg)
        itens += verificar_versao(cfg)
    itens += verificar_estado()
    itens += verificar_segredos_no_git()
    return itens


def formatar(itens: list[Item]) -> list[str]:
    marca = {"ok": "[ok]   ", "aviso": "[aviso]", "erro": "[ERRO] "}
    linhas = []
    for i in itens:
        linhas.append(f"{marca[i.nivel]} {i.titulo}" + (f": {i.detalhe}" if i.detalhe else ""))
        if i.correcao:
            linhas.append(f"         -> {i.correcao}")
    erros = sum(i.nivel == "erro" for i in itens)
    avisos = sum(i.nivel == "aviso" for i in itens)
    linhas += ["", f"{erros} erro(s), {avisos} aviso(s)." + (" Corrija os erros antes de rodar." if erros else "")]
    return linhas


def executar(config_path: str | Path | None = None, rede: bool = True, ia: bool = False) -> tuple[list[Item], int]:
    cfg = load_config(config_path)
    itens = diagnosticar(cfg, rede, ia)
    return itens, 1 if any(i.nivel == "erro" for i in itens) else 0
