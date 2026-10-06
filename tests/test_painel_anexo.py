"""Painel como anexo: em repositório privado não há GitHub Pages, então ele vai no e-mail e no Telegram."""
from email import message_from_bytes
from pathlib import Path

import pytest
import yaml
from conftest import CONFIG_TESTE

from vagas_monitor import pipeline, report
from vagas_monitor.notify import email_, telegram
from vagas_monitor.models import Job

CTX = {"run_date_br": "06/10/2026", "total": 1, "new_count": 1, "lookback_days": 7, "report_url": "",
       "categorias": {"x": {"nome": "X"}},
       "jobs": [{"is_new": True, "score": 80, "fit": None, "fit_note": "", "url": "https://x/1", "title": "Vaga",
                 "company": "ACME", "matched_city": "Cidade", "workplace": "hybrid", "location": "Cidade",
                 "seniority": "junior", "category": "x"}]}


class SMTPCaptura:
    mensagem = None
    senha = None

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def login(self, usuario, senha):
        SMTPCaptura.senha = senha

    def send_message(self, msg):
        SMTPCaptura.mensagem = msg


def test_email_leva_o_painel_html_em_anexo(monkeypatch, tmp_path):
    monkeypatch.setattr(email_.smtplib, "SMTP_SSL", SMTPCaptura)
    md, html = tmp_path / "r.md", tmp_path / "index.html"
    md.write_text("# relatório", encoding="utf-8")
    html.write_text("<html><body>painel</body></html>", encoding="utf-8")
    assert email_.send("h", 465, "eu@example.com", "abcd efgh ijkl mnop", "eu@example.com", CTX, md, html)
    nomes = [p.get_filename() for p in message_from_bytes(SMTPCaptura.mensagem.as_bytes()).walk() if p.get_filename()]
    assert nomes == ["r.md", "painel.html"]
    assert SMTPCaptura.senha == "abcdefghijklmnop"  # a senha de app vem com espaços


def test_email_sem_painel_continua_igual(monkeypatch, tmp_path):
    monkeypatch.setattr(email_.smtplib, "SMTP_SSL", SMTPCaptura)
    assert email_.send("h", 465, "u", "s", "t", CTX, None, None)
    assert not [p for p in message_from_bytes(SMTPCaptura.mensagem.as_bytes()).walk() if p.get_filename()]


def test_telegram_envia_o_painel_como_documento(monkeypatch, tmp_path):
    visto = {}

    class R:
        ok = True
        status_code = 200
        text = ""

    def post(url, data=None, files=None, timeout=None, json=None):
        visto.update(url=url, data=data, nome=files["document"][0])
        return R()

    html = tmp_path / "index.html"
    html.write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(telegram.requests, "post", post)
    assert telegram.send_document("TOKEN", "42", html, "legenda")
    assert visto["url"].endswith("/sendDocument") and visto["data"]["chat_id"] == "42" and visto["nome"] == "painel.html"


@pytest.mark.parametrize("config,url,esperado", [
    ("auto", "", True), ("auto", "https://pages", False), (True, "https://pages", True), (False, "", False)])
def test_quando_anexar(config, url, esperado):
    assert pipeline.anexar_painel({"notificacoes": {"anexar_painel": config}}, {"report_url": url}) is esperado
    assert pipeline.anexar_painel({}, {"report_url": url}) is (not url)  # padrão: auto


def _rodada(monkeypatch, tmp_path, url_publica):
    cfg = yaml.safe_load(CONFIG_TESTE.read_text(encoding="utf-8"))
    cfg["relatorio"]["url_publica"] = url_publica
    cfg["relatorio"]["html"] = "docs/index.html"
    caminho = tmp_path / "config.yaml"
    caminho.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    monkeypatch.setattr(report, "ROOT", tmp_path)
    vaga = Job(source="gupy", title="Analista de Dados Júnior", company="Portonave", url="https://g/1", city="Navegantes",
               state="Santa Catarina", workplace="hybrid", date_posted="2026-10-03", description="Python, SQL.")
    monkeypatch.setattr(pipeline, "collect_all", lambda cfg, lb, errors, skip=(): ([vaga], {"gupy": 1}))
    monkeypatch.setattr(pipeline.linkedin, "fetch_description", lambda j: False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    for v in ("SMTP_USER", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(v, raising=False)
    chamadas = {"send": 0, "doc": []}
    monkeypatch.setattr(telegram, "send", lambda *a, **k: chamadas.__setitem__("send", chamadas["send"] + 1) or 1)
    monkeypatch.setattr(telegram, "send_document", lambda tok, chat, caminho, legenda="": chamadas["doc"].append(Path(caminho).name) or True)
    pipeline.run(force=True, config_path=str(caminho))
    return chamadas


def test_sem_link_publico_o_painel_vai_no_telegram(monkeypatch, tmp_path):
    c = _rodada(monkeypatch, tmp_path, "")
    assert c["send"] == 1 and c["doc"] == ["index.html"]


def test_com_link_publico_o_painel_nao_e_anexado(monkeypatch, tmp_path):
    c = _rodada(monkeypatch, tmp_path, "https://usuario.github.io/radar/")
    assert c["send"] == 1 and c["doc"] == []
