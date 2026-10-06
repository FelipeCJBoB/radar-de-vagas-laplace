"""doctor: reproduz, sem rede, os três defeitos que passaram semanas sem aviso."""
import smtplib
from pathlib import Path

import pytest
import requests
from conftest import CONFIG_TESTE

from vagas_monitor import diagnostico as d
from vagas_monitor.__main__ import main
from vagas_monitor.config import load_config

ZERO = Path(__file__).resolve().parent.parent / "config.yaml"


class Resp:
    def __init__(self, status=200, corpo=None, texto=""):
        self.status_code, self._corpo, self.text = status, corpo or {}, texto
        self.ok = status < 400

    def json(self):
        return self._corpo


def get_falso(respostas):
    """GET por trecho da URL; o que não casa devolve 200 vazio."""
    def get(url, **k):
        for trecho, r in respostas.items():
            if trecho in url:
                if isinstance(r, Exception):
                    raise r
                return r
        return Resp(200, {})
    return get


def niveis(itens):
    return [(i.nivel, i.titulo) for i in itens]


@pytest.fixture(autouse=True)
def sem_canais(monkeypatch):
    for v in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "SMTP_USER", "SMTP_PASSWORD", "EMAIL_TO", "PERFIL_MD"):
        monkeypatch.delenv(v, raising=False)


# ------------------------------------------------------------------ Telegram
def test_token_revogado_vira_erro_401_com_a_correcao(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "revogado")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setattr(d.requests, "get", get_falso({"getMe": Resp(401)}))
    [item] = d.verificar_telegram()
    assert item.nivel == "erro" and "401" in item.titulo and "secret do GitHub" in item.correcao


def test_telegram_ok_mostra_o_usuario_do_bot(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setattr(d.requests, "get", get_falso({"getMe": Resp(200, {"result": {"username": "meu_bot"}})}))
    [item] = d.verificar_telegram()
    assert item.nivel == "ok" and "meu_bot" in item.detalhe


def test_chat_inexistente_e_telegram_desligado(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")
    monkeypatch.setattr(d.requests, "get", get_falso({"getMe": Resp(200, {"result": {}}), "getChat": Resp(400)}))
    assert "chat não encontrado" in d.verificar_telegram()[0].titulo
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN")
    monkeypatch.delenv("TELEGRAM_CHAT_ID")
    assert d.verificar_telegram()[0].nivel == "aviso"


def test_so_um_dos_dois_do_telegram_e_erro(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    item = d.verificar_telegram()[0]
    assert item.nivel == "erro" and "TELEGRAM_CHAT_ID" in item.detalhe


# ------------------------------------------------------------------ e-mail
def test_senha_smtp_ausente_e_o_defeito_que_ficou_semanas_sem_aviso(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "eu@example.com")
    monkeypatch.setenv("EMAIL_TO", "eu@example.com")
    [item] = d.verificar_email()
    assert item.nivel == "erro" and "SMTP_PASSWORD" in item.detalhe and "2 etapas" in item.correcao


class SMTPRecusa:
    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def login(self, usuario, senha):
        raise smtplib.SMTPAuthenticationError(535, b"bad")


class SMTPOk(SMTPRecusa):
    usada: dict = {}

    def login(self, usuario, senha):
        SMTPOk.usada["senha"] = senha


def _smtp_env(monkeypatch, senha):
    for v, x in (("SMTP_USER", "eu@example.com"), ("SMTP_PASSWORD", senha), ("EMAIL_TO", "eu@example.com")):
        monkeypatch.setenv(v, x)


def test_login_recusado_e_senha_com_espacos(monkeypatch):
    _smtp_env(monkeypatch, "abcd efgh ijkl mnop")
    monkeypatch.setattr(d.smtplib, "SMTP_SSL", SMTPRecusa)
    itens = d.verificar_email()
    assert ("aviso", "E-mail: SMTP_PASSWORD tem espaços") in niveis(itens)
    assert any(i.nivel == "erro" and "login recusado" in i.titulo for i in itens)


def test_email_ok_usa_a_senha_sem_espacos_e_offline_nao_conecta(monkeypatch):
    _smtp_env(monkeypatch, "abcd efgh ijkl mnop")
    monkeypatch.setattr(d.smtplib, "SMTP_SSL", SMTPOk)
    assert d.verificar_email()[-1].nivel == "ok" and SMTPOk.usada["senha"] == "abcdefghijklmnop"
    monkeypatch.setattr(d.smtplib, "SMTP_SSL", lambda *a, **k: pytest.fail("não devia conectar"))
    assert "--offline" in d.verificar_email(rede=False)[-1].detalhe


# ------------------------------------------------------------------ fontes
def test_gupy_404_e_o_defeito_de_outubro(monkeypatch):
    monkeypatch.setattr(d.requests, "get", get_falso({"gupy": Resp(404)}))
    [item] = d.verificar_gupy(load_config(CONFIG_TESTE))
    assert item.nivel == "erro" and "404" in item.titulo and "guia/09" in item.correcao


def test_gupy_formato_mudou_e_ok(monkeypatch):
    cfg = load_config(CONFIG_TESTE)
    monkeypatch.setattr(d.requests, "get", get_falso({"gupy": Resp(200, {"data": [{"id": 1, "name": "x"}]})}))
    assert "formato mudou" in d.verificar_gupy(cfg)[0].titulo
    vaga = dict.fromkeys(d.CAMPOS_GUPY, "x")
    monkeypatch.setattr(d.requests, "get", get_falso({"gupy": Resp(200, {"data": [vaga]})}))
    assert d.verificar_gupy(cfg)[0].nivel == "ok"


def test_linkedin_429_e_aviso_e_formato_mudado_e_erro(monkeypatch):
    cfg = load_config(CONFIG_TESTE)
    monkeypatch.setattr(d.requests, "get", get_falso({"linkedin": Resp(429)}))
    assert d.verificar_linkedin(cfg)[0].nivel == "aviso"
    monkeypatch.setattr(d.requests, "get", get_falso({"linkedin": Resp(200, texto="<html>captcha</html>")}))
    assert d.verificar_linkedin(cfg)[0].nivel == "erro"
    monkeypatch.setattr(d.requests, "get", get_falso({"linkedin": Resp(200, texto='<li class="base-search-card">')}))
    assert d.verificar_linkedin(cfg)[0].nivel == "ok"


def test_sem_conexao_e_aviso_nao_erro(monkeypatch):
    monkeypatch.setattr(d.requests, "get", get_falso({"gupy": requests.ConnectionError("sem rede")}))
    assert d.verificar_gupy(load_config(CONFIG_TESTE))[0].nivel == "aviso"


# ------------------------------------------------------------------ config, perfil, versão
def test_config_vazio_lista_cada_pendencia():
    itens = d.verificar_config(load_config(ZERO))
    assert len(itens) >= 5 and all(i.nivel == "erro" and "init" in i.correcao for i in itens)


def test_perfil_ausente_modelo_e_preenchido(monkeypatch):
    cfg = {"perfil": "nao_existe.md"}
    assert d.verificar_perfil(cfg)[0].nivel == "aviso"
    monkeypatch.setenv("PERFIL_MD", "# Perfil\n**Objetivo:** [cargo ou área que você busca]")
    assert "modelo" in d.verificar_perfil(cfg)[0].detalhe
    monkeypatch.setenv("PERFIL_MD", "Analista financeira com seis anos de experiência em contas a pagar e conciliação.")
    assert d.verificar_perfil(cfg)[0].nivel == "ok"


def test_versao_atras_do_modelo_vira_aviso(monkeypatch):
    monkeypatch.setattr(d.requests, "get", get_falso({"releases/latest": Resp(200, {"tag_name": "v9.0.0"})}))
    [item] = d.verificar_versao({"modelo": {"repositorio": "alguem/radar"}})
    assert item.nivel == "aviso" and "CHANGELOG" in item.correcao
    monkeypatch.setattr(d.requests, "get", get_falso({"releases/latest": Resp(200, {"tag_name": "v0.0.1"})}))
    assert d.verificar_versao({"modelo": {"repositorio": "alguem/radar"}})[0].nivel == "ok"
    assert d.verificar_versao({}) == []  # sem repositório configurado, não pergunta nada


# ------------------------------------------------------------------ CLI
def test_cli_doctor_sai_com_1_se_houver_erro(capsys):
    assert main(["--config", str(ZERO), "doctor", "--offline"]) == 1
    saida = capsys.readouterr().out
    assert "[ERRO]" in saida and "regiao.estados" in saida


def test_cli_doctor_config_valido_offline_sai_com_0(capsys):
    rc = main(["--config", str(CONFIG_TESTE), "doctor", "--offline"])
    saida = capsys.readouterr().out
    assert rc == 0 and "[ok]" in saida and "0 erro(s)" in saida
