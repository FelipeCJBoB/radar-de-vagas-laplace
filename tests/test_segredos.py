"""publicar-secrets: o valor sai do .env para o gh por entrada padrão e nunca é impresso."""
from types import SimpleNamespace

from vagas_monitor import segredos
from vagas_monitor.__main__ import main

ENV = """# comentário
TELEGRAM_BOT_TOKEN=123456789:token_secreto_de_teste
TELEGRAM_CHAT_ID=42
SMTP_HOST=smtp.gmail.com
SMTP_USER=voce@example.com
SMTP_PASSWORD="abcd efgh ijkl mnop"
EMAIL_TO=voce@example.com
GEMINI_API_KEY=chave_gemini_de_teste
ANTHROPIC_API_KEY=
"""


def env_arquivo(tmp_path):
    p = tmp_path / ".env"
    p.write_text(ENV, encoding="utf-8")
    return p


def test_le_o_env_ignora_vazio_e_placeholder(tmp_path):
    valores, ignorados = segredos.coletar(env_arquivo(tmp_path))
    assert valores["TELEGRAM_CHAT_ID"] == "42" and valores["GEMINI_API_KEY"] == "chave_gemini_de_teste"
    assert "SMTP_USER" not in valores and "EMAIL_TO" not in valores  # voce@example.com é exemplo
    assert "ANTHROPIC_API_KEY" in ignorados
    assert valores["SMTP_PASSWORD"] == "abcdefghijklmnop"  # sem os espaços da senha de app


def test_perfil_so_entra_se_pedido_e_se_tiver_conteudo(tmp_path):
    perfil = tmp_path / "perfil.md"
    perfil.write_text("# Perfil\nAnalista.", encoding="utf-8")
    assert segredos.coletar(env_arquivo(tmp_path), perfil)[0]["PERFIL_MD"].startswith("# Perfil")
    assert "PERFIL_MD" not in segredos.coletar(env_arquivo(tmp_path))[0]
    perfil.write_text("  ", encoding="utf-8")
    assert "PERFIL_MD" in segredos.coletar(env_arquivo(tmp_path), perfil)[1]


class RunFalso:
    def __init__(self, falha_em=()):
        self.chamadas, self.falha_em = [], falha_em

    def __call__(self, cmd, input=None, capture_output=True, text=True):
        self.chamadas.append((cmd, input))
        if cmd[:3] == ["gh", "secret", "set"] and cmd[3] in self.falha_em:
            return SimpleNamespace(returncode=1, stderr="HTTP 403")
        return SimpleNamespace(returncode=0, stderr="")


def test_valor_vai_por_entrada_padrao_e_nunca_na_linha_de_comando():
    run = RunFalso()
    r = segredos.publicar({"TELEGRAM_BOT_TOKEN": "valor-secreto"}, "dono/repo", run=run, which=lambda x: "/usr/bin/gh")
    assert all(x.ok for x in r)
    cmd, entrada = run.chamadas[-1]
    assert cmd == ["gh", "secret", "set", "TELEGRAM_BOT_TOKEN", "--repo", "dono/repo"]
    assert entrada == "valor-secreto" and "valor-secreto" not in " ".join(cmd)


def test_sem_gh_ou_sem_login_explica_o_que_fazer():
    r = segredos.publicar({"A": "1"}, which=lambda x: None)
    assert not r[0].ok and "gh" in r[0].detalhe

    class SemLogin(RunFalso):
        def __call__(self, cmd, **k):
            return SimpleNamespace(returncode=1, stderr="") if cmd[:3] == ["gh", "auth", "status"] else super().__call__(cmd, **k)

    r = segredos.publicar({"A": "1"}, run=SemLogin(), which=lambda x: "gh")
    assert not r[0].ok and "gh auth login" in r[0].detalhe


def test_falha_de_um_nao_derruba_os_outros():
    r = segredos.publicar({"A": "1", "B": "2"}, run=RunFalso(falha_em=("A",)), which=lambda x: "gh")
    assert [(x.nome, x.ok) for x in r] == [("A", False), ("B", True)] and "403" in r[0].detalhe


def test_ensaio_nao_chama_o_gh():
    r = segredos.publicar({"A": "1"}, dry_run=True, run=lambda *a, **k: (_ for _ in ()).throw(AssertionError("chamou")))
    assert r[0].ok


def test_cli_nunca_imprime_o_valor(tmp_path, capsys):
    rc = main(["publicar-secrets", "--env", str(env_arquivo(tmp_path)), "--dry-run"])
    saida = capsys.readouterr().out
    assert rc == 0 and "TELEGRAM_BOT_TOKEN" in saida and "GEMINI_API_KEY" in saida
    for valor in ("token_secreto_de_teste", "chave_gemini_de_teste", "abcdefghijklmnop", "abcd efgh"):
        assert valor not in saida


def test_cli_sem_env_ou_vazio_orienta(tmp_path, capsys):
    assert main(["publicar-secrets", "--env", str(tmp_path / "nao.env")]) == 2
    vazio = tmp_path / "vazio.env"
    vazio.write_text("TELEGRAM_BOT_TOKEN=\n", encoding="utf-8")
    assert main(["publicar-secrets", "--env", str(vazio)]) == 2
    assert "Nada a publicar" in capsys.readouterr().out
