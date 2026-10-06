"""O verificador de vazamento: acusa o que deve e deixa passar o legítimo."""
import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("leak_check", RAIZ / "tools" / "leak_check.py")
leak = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(leak)


def tipos(texto, deny=None):
    return {a.split(":")[0] for a in leak.varrer_texto(texto, deny)}


def test_acusa_chaves_e_tokens_plantados():
    assert "chave do Google/Gemini" in tipos("GEMINI=AIza" + "A" * 35)
    assert "chave da Anthropic" in tipos("k=sk-ant-" + "a1" * 15)
    assert "token de bot do Telegram" in tipos("t=123456789:" + "A" * 35)
    assert "token do GitHub" in tipos("gh=ghp_" + "a" * 36)
    assert "chave privada" in tipos("-----BEGIN PRIVATE KEY-----")


def test_acusa_dados_pessoais_plantados():
    assert "CPF" in tipos("cpf 123.456.789-09")
    assert "telefone brasileiro" in tipos("fone (11) 98765-4321")
    assert "e-mail" in tipos("fale com pessoa.real@provedor.com.br")


def test_deixa_passar_o_legitimo():
    assert not tipos("use SMTP_USER=voce@example.com e o servidor smtp.gmail.com")
    assert not tipos("co-author: 12345+bot@users.noreply.github.com")
    assert not tipos("Co-Authored-By: Claude <noreply@anthropic.com>")
    assert not tipos("score 98765 e data 2026-10-06 e versão 1.0.0")


def test_lista_de_bloqueio_pessoal_e_sem_distinguir_caixa():
    assert tipos("trabalho na Empresa Xpto", deny=["empresa xpto"]) == {"termo da lista de bloqueio pessoal"}
    assert not tipos("texto limpo", deny=["empresa xpto"])


def test_relatorio_nao_repete_o_valor_vazado():
    achado = leak.varrer_texto("GEMINI=AIza" + "B" * 35)[0]
    assert "B" * 10 not in achado


def test_varre_arquivos_e_aponta_a_linha(tmp_path):
    (tmp_path / "a.txt").write_text("ok\nchave AIza" + "C" * 35 + "\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "x").write_text("AIza" + "D" * 35, encoding="utf-8")  # ignorado
    achados = leak.varrer(tmp_path)
    assert [(a, n) for a, n, _ in achados] == [("a.txt", 2)]


def test_denylist_local_nao_e_versionada_nem_varrida():
    gitignore = (RAIZ / ".gitignore").read_text(encoding="utf-8")
    assert "tools/leak_denylist.local.txt" in gitignore


def test_o_proprio_repositorio_passa_nos_detectores_genericos():
    achados = leak.varrer(RAIZ, denylist=[])
    assert not achados, "\n".join(f"{a}:{n} {x}" for a, n, x in achados)
