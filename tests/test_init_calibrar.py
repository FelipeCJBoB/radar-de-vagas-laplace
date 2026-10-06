"""init (três caminhos), leitura de currículo, proposta da IA e calibração."""
import json
import zipfile
from pathlib import Path

import pytest
import yaml
from conftest import CONFIG_TESTE

from vagas_monitor import assistente, calibracao, curriculo
from vagas_monitor.__main__ import main
from vagas_monitor.config import load_config
from vagas_monitor.validar import validar_config

RAIZ = Path(__file__).resolve().parent.parent
ZERO = RAIZ / "config.yaml"


@pytest.fixture
def raiz(tmp_path):
    """Pasta de trabalho com o config zero-default, como a de quem acabou de criar a cópia."""
    (tmp_path / "config.yaml").write_text(ZERO.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


BASE = {"estados": ["PB"], "cidade": "João Pessoa", "uf": "PB", "nivel": "pleno", "objetivo": "área financeira"}


# ------------------------------------------------------------------ init manual
def test_init_manual_gera_config_valido_e_roda(raiz):
    r = assistente.executar_init({**BASE, "manual": True, "areas": ["administrativo-financeiro", "contabil-fiscal:adjacente"]},
                                 raiz=raiz)
    assert r["pendencias"] == []
    cfg = load_config(raiz / "config.yaml")
    assert validar_config(cfg) == [] and "João Pessoa" in cfg["cidades"]
    assert cfg["categorias"]["administrativo_financeiro"]["bonus"] == 12
    assert cfg["categorias"]["contabil_fiscal"]["bonus"] == 3
    assert (raiz / "perfil.md").read_text(encoding="utf-8").count("área financeira") >= 1


def test_init_preserva_o_resto_do_config_e_guarda_backup(raiz):
    cfg = yaml.safe_load((raiz / "config.yaml").read_text(encoding="utf-8"))
    cfg["intervalo_dias"] = 9
    (raiz / "config.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    assistente.executar_init({**BASE, "manual": True, "areas": ["saude"]}, raiz=raiz)
    assert yaml.safe_load((raiz / "config.yaml").read_text(encoding="utf-8"))["intervalo_dias"] == 9
    assert (raiz / "config.yaml.bak").exists()


def test_init_avisa_que_pack_beta_nao_foi_validado(raiz):
    r = assistente.executar_init({**BASE, "manual": True, "areas": ["saude"]}, raiz=raiz)
    assert any("beta" in a for a in r["avisos"]) and any("esqueleto" in a for a in r["avisos"])


def test_init_exige_area_e_nivel(raiz):
    with pytest.raises(assistente.InitErro, match="área"):
        assistente.executar_init({**BASE, "manual": True}, raiz=raiz)
    with pytest.raises(assistente.InitErro, match="nível"):
        assistente.executar_init({**BASE, "nivel": None, "manual": True, "areas": ["saude"]}, raiz=raiz)
    with pytest.raises(assistente.InitErro, match="não existe"):
        assistente.executar_init({**BASE, "manual": True, "areas": ["saudee"]}, raiz=raiz)


def test_init_so_remoto_nao_pede_estado(raiz):
    r = assistente.executar_init({"remoto": "somente", "nivel": "junior", "manual": True, "areas": ["ti-desenvolvimento"]},
                                 raiz=raiz)
    assert r["pendencias"] == []


def test_init_mede_a_referencia_e_grava_o_arquivo(raiz):
    r = assistente.executar_init({**BASE, "manual": True, "areas": ["contabil-fiscal"],
                                  "quero": ["Contador Pleno", "Analista Fiscal"],
                                  "nao_quero": ["Fiscal de Loja", "Enfermeiro"]}, raiz=raiz)
    assert r["medicao"]["ok"] and r["medicao"]["recall"] == 1.0 and r["medicao"]["corte"] == 1.0
    assert (raiz / "calibracao" / "referencia.yaml").exists()


# ------------------------------------------------------------------ init com IA
def _proposta(**kw):
    base = {"perfil_md": "# Perfil\nAnalista financeira com 6 anos.", "nivel_sugerido": "pleno",
            "ocupacoes": [], "formacao": ["Ciências Contábeis"], "ferramentas": ["Excel"], "registros": [],
            "areas": [{"slug": "administrativo-financeiro", "papel": "alvo", "motivo": "objetivo"},
                      {"slug": "contabil-fiscal", "papel": "ponte", "motivo": "formação"},
                      {"slug": "pack-inexistente", "papel": "alvo", "motivo": "?"}],
            "categorias_extras": [{"nome": "Tesouraria Corporativa", "papel": "adjacente",
                                   "titulo": ["analista de tesouraria"], "descricao": ["caixa"]}],
            "termos_busca": ["analista financeiro", "tesouraria"], "excluir_titulo": ["fiscal de loja"],
            "habilidades": ["excel", "conciliação"], "avisos": ["anos de experiência não informados"]}
    base.update(kw)
    return curriculo.validar_proposta(base)


def test_init_com_ia_usa_a_proposta_e_ignora_area_fora_do_catalogo(raiz, tmp_path):
    cv = tmp_path / "cv.txt"
    cv.write_text("Analista financeira.\nExcel e conciliação bancária.", encoding="utf-8")
    vistos = {}

    def falsa(texto, objetivo, nivel):
        vistos["texto"], vistos["objetivo"] = texto, objetivo
        return _proposta()

    r = assistente.executar_init({**BASE, "curriculo": str(cv), "aprovado": True}, raiz=raiz, proposta_fn=falsa)
    cfg = load_config(raiz / "config.yaml")
    assert validar_config(cfg) == []
    assert set(cfg["categorias"]) == {"administrativo_financeiro", "contabil_fiscal", "tesouraria_corporativa"}
    assert cfg["categorias"]["contabil_fiscal"]["bonus"] < 0  # ponte
    assert "fiscal de loja" in cfg["excluir_titulo"] and cfg["termos_busca"][0] == "analista financeiro"
    assert "Analista financeira com 6 anos" in (raiz / "perfil.md").read_text(encoding="utf-8")
    assert any("fora do catálogo" in a for a in r["avisos"]) and any("IA:" in a for a in r["avisos"])
    assert vistos["objetivo"] == "área financeira"


def test_curriculo_so_vai_para_a_ia_depois_de_aprovado(raiz, tmp_path):
    cv = tmp_path / "cv.txt"
    cv.write_text("texto", encoding="utf-8")
    chamou = []
    with pytest.raises(assistente.InitErro, match="aprovar"):
        assistente.executar_init({**BASE, "curriculo": str(cv)}, raiz=raiz, proposta_fn=lambda *a: chamou.append(1))
    assert not chamou


def test_texto_enviado_a_ia_sai_anonimizado(raiz, tmp_path):
    cv = tmp_path / "cv.txt"
    fone = "(83) 9" + "8765-4321"  # em duas partes: o leak_check não deve achar telefone no repositório
    cv.write_text(f"Maria Souza Lima\nContato: {fone} maria@exemplo.com\nAnalista financeira.", encoding="utf-8")
    vistos = {}

    def falsa(texto, objetivo, nivel):
        vistos["texto"] = texto
        return _proposta()

    assistente.executar_init({**BASE, "curriculo": str(cv), "aprovado": True}, raiz=raiz, proposta_fn=falsa)
    for vazou in ("98765", "maria@", "Maria", "Souza"):
        assert vazou not in vistos["texto"]
    assert "Analista financeira" in vistos["texto"]


# ------------------------------------------------------------------ leitura do currículo
def test_le_txt_docx_e_recusa_formato_estranho(tmp_path):
    t = tmp_path / "a.txt"
    t.write_text("Analista de Dados", encoding="utf-8")
    assert curriculo.ler_texto(t) == "Analista de Dados"
    d = tmp_path / "b.docx"
    with zipfile.ZipFile(d, "w") as z:
        z.writestr("word/document.xml", '<w:document><w:p><w:r><w:t>Contador &amp; Auditor</w:t></w:r></w:p>'
                                        '<w:p><w:r><w:t>Excel</w:t></w:r></w:p></w:document>')
    assert curriculo.ler_texto(d).splitlines() == ["Contador & Auditor", "Excel"]
    with pytest.raises(ValueError, match="não suportado"):
        curriculo.ler_texto(tmp_path / "x.xyz") if (tmp_path / "x.xyz").write_text("a") else None
    with pytest.raises(FileNotFoundError):
        curriculo.ler_texto(tmp_path / "nao_existe.txt")


def test_pdf_sem_pypdf_explica_o_que_fazer(tmp_path, monkeypatch):
    import builtins
    real = builtins.__import__

    def sem_pypdf(nome, *a, **k):
        if nome == "pypdf":
            raise ImportError
        return real(nome, *a, **k)

    (tmp_path / "c.pdf").write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(builtins, "__import__", sem_pypdf)
    with pytest.raises(RuntimeError, match="pypdf"):
        curriculo.ler_texto(tmp_path / "c.pdf")


# ------------------------------------------------------------------ proposta da IA
class ProvFalso:
    NOME = "Falso"

    def __init__(self, respostas):
        self.respostas, self.chamadas = list(respostas), 0

    def criar_cliente(self, cfg):
        return object()

    def avaliar(self, cliente, system, texto, cfg, schema=None, max_tokens=800):
        self.chamadas += 1
        assert schema is curriculo.PROPOSTA_SCHEMA and max_tokens > 800
        r = self.respostas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def classificar_erro(self, exc):
        return str(exc), False


def test_prompt_traz_catalogo_regras_e_nao_inventar():
    s = curriculo.montar_system()
    assert "saude" in s and "ti-dados-ia" in s and "Não invente" in s and "alvo" in s and "ponte" in s


def test_propor_tenta_de_novo_depois_de_resposta_invalida():
    prov = ProvFalso(["isto não é json", RuntimeError("503"), json.dumps(_proposta())])
    p = curriculo.propor("cv", "obj", {}, prov=prov, dormir=lambda s: None)
    assert prov.chamadas == 3 and p["nivel_sugerido"] == "pleno"


def test_propor_desiste_depois_das_tentativas():
    prov = ProvFalso([RuntimeError("503")] * 4)
    with pytest.raises(RuntimeError, match="503"):
        curriculo.propor("cv", "obj", {}, prov=prov, dormir=lambda s: None)
    assert prov.chamadas == 4


def test_propor_sem_chave_de_ia_manda_usar_o_modo_manual(monkeypatch):
    for v in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(RuntimeError, match="--manual"):
        curriculo.propor("cv", "obj", {"provedor": "auto"})


def test_proposta_sem_area_nenhuma_e_invalida():
    with pytest.raises(curriculo.PropostaInvalida):
        curriculo.validar_proposta({"areas": [{"slug": "nao-existe", "papel": "alvo", "motivo": ""}]})


# ------------------------------------------------------------------ calibração
def cfg_teste():
    return load_config(CONFIG_TESTE)


def test_medir_acha_o_que_faltou_e_o_que_sobrou():
    m = calibracao.medir(cfg_teste(), ["Analista de Dados Júnior", "Padeiro Noturno"],
                         ["Analista SAP SD", "Cozinheiro"])
    assert m["recall"] == 0.5 and m["corte"] == 0.5 and not m["ok"]
    assert m["perdidas"][0][0] == "Padeiro Noturno" and "nenhuma categoria" in m["perdidas"][0][1]
    assert m["vazaram"][0][0] == "Analista SAP SD" and "Sistemas e ERP" in m["vazaram"][0][1]
    texto = "\n".join(calibracao.relatorio_medicao(m))
    assert "FALTARAM" in texto and "SOBRARAM" in texto and "abaixo da meta" in texto


def test_medir_sem_exemplos_nao_aprova():
    assert not calibracao.medir(cfg_teste(), [], [])["ok"]


def test_sondar_acha_vocabulario_que_falta_e_expoe_homonimo():
    cfg = cfg_teste()
    titulos = (["Analista de Dados Pleno"] * 2 + ["Implantador de Sistemas", "Implantador de Sistemas Jr",
               "Implantador de Software", "Operador de Empilhadeira"] + ["Padeiro Noturno"] * 3)
    s = calibracao.sondar(cfg, titulos, minimo=3)
    candidatos = {g for g, _, _ in s["candidatos"]}
    assert "padeiro noturno" in candidatos or "padeiro" in candidatos
    assert s["capturados"] >= 2 and s["descartados"] >= 3
    dados = next(t for t in s["termos"] if t["termo"] == "dados")
    assert dados["n"] == 2 and dados["amostra"][0].startswith("Analista de Dados")
    assert "CANDIDATOS" in "\n".join(calibracao.relatorio_sondagem(s))


# ------------------------------------------------------------------ CLI
def test_cli_init_manual_nao_interativo(raiz, capsys):
    cfg = raiz / "config.yaml"
    antes = ZERO.read_bytes()
    rc = main(["--config", str(cfg), "init", "--nao-interativo", "--manual", "--estado", "PB", "--cidade", "João Pessoa",
               "--nivel", "pleno", "--area", "contabil-fiscal", "--quero", "Contador Pleno", "--nao-quero", "Fiscal de Loja"])
    out = capsys.readouterr().out
    assert rc == 0 and "Gravado" in out and "100%" in out
    assert validar_config(load_config(cfg)) == []
    # o `init` escreve ao lado do --config informado e NUNCA no repositório real
    assert ZERO.read_bytes() == antes and not (RAIZ / "perfil.md").exists()


def test_cli_init_sem_area_no_modo_nao_interativo_falha(raiz, capsys):
    rc = main(["--config", str(raiz / "config.yaml"), "init", "--nao-interativo", "--manual", "--estado", "PB",
               "--cidade", "João Pessoa", "--nivel", "pleno"])
    assert rc == 2 and "--area" in capsys.readouterr().out


def test_cli_listar_areas(capsys):
    assert main(["init", "--listar-areas"]) == 0
    assert "saude" in capsys.readouterr().out


def test_cli_calibrar_offline(tmp_path, capsys):
    ref = tmp_path / "ref.yaml"
    calibracao.gravar_referencia(ref, ["Analista de Dados Júnior"], ["Cozinheiro"])
    assert main(["--config", str(CONFIG_TESTE), "calibrar", "--referencia", str(ref)]) == 0
    assert "dentro da meta" in capsys.readouterr().out
    calibracao.gravar_referencia(ref, ["Padeiro Noturno"], [])
    assert main(["--config", str(CONFIG_TESTE), "calibrar", "--referencia", str(ref)]) == 1


def test_cli_calibrar_sem_referencia_orienta(tmp_path, capsys):
    assert main(["--config", str(CONFIG_TESTE), "calibrar", "--referencia", str(tmp_path / "nao.yaml")]) == 2
    assert "quero" in capsys.readouterr().out


def test_cli_calibrar_recusa_config_vazio(capsys):
    assert main(["--config", str(ZERO), "calibrar"]) == 2
    assert "incompleto" in capsys.readouterr().out


def test_cli_sondar_usa_os_titulos_coletados(monkeypatch, capsys):
    monkeypatch.setattr(calibracao, "coletar_titulos", lambda cfg, dias, fontes: (["Analista de Dados"] * 3, {}))
    assert main(["--config", str(CONFIG_TESTE), "calibrar", "--sondar", "--fontes", "gupy"]) == 0
    assert "TERMOS ATUAIS" in capsys.readouterr().out


def test_sondagem_ignora_nome_de_lugar_e_colapsa_pedaco_redundante():
    cfg = cfg_teste()
    cfg.update(cidades=["João Pessoa", "Cabedelo"], _estados=["Paraíba"])  # a região da pessoa
    titulos = ["ATENDENTE DE RESTAURANTE (JOÃO PESSOA/PB)"] * 4 + ["Padeiro Pleno - Cabedelo/PB"] * 3
    cand = {g for g, _, _ in calibracao.sondar(cfg, titulos, minimo=3)["candidatos"]}
    assert "atendente restaurante" in cand and "padeiro" in cand  # a função fica; nível e lugar saem
    assert "restaurante" not in cand and "atendente" not in cand  # pedaços redundantes do maior
    assert not any(w in g.split() for g in cand for w in ("joao", "pessoa", "pb", "cabedelo", "pleno"))


class ProvPorModelo(ProvFalso):
    """Registra o modelo de cada chamada; `principal` está sobrecarregado, o resto responde."""

    def __init__(self, respostas, modelos_ruins=("principal",)):
        super().__init__(respostas)
        self.modelos, self.ruins = [], modelos_ruins

    def avaliar(self, cliente, system, texto, cfg, schema=None, max_tokens=800):
        modelo = (cfg.get("falso") or {}).get("modelo", "principal")
        self.modelos.append(modelo)
        if modelo in self.ruins:
            raise RuntimeError("503 sobrecarregado")
        return super().avaliar(cliente, system, texto, cfg, schema, max_tokens)

    def classificar_erro(self, exc):
        return str(exc), False


def test_propor_usa_o_modelo_de_reserva_quando_o_principal_esta_fora(monkeypatch):
    """O 503 do Gemini gratuito durou horas; o `init` não pode depender do modelo principal."""
    from vagas_monitor import providers

    prov = ProvPorModelo([json.dumps(_proposta())])
    monkeypatch.setitem(providers.DISPONIVEIS, "falso", prov)
    cfg = {"falso": {"modelos_reserva": ["leve"]}}
    p = curriculo.propor("cv", "obj", cfg, prov=prov, dormir=lambda s: None)
    assert p["nivel_sugerido"] == "pleno"
    assert prov.modelos == ["principal"] * 4 + ["leve"]  # 1 + 3 tentativas no principal, depois a reserva


def test_propor_erro_fatal_nao_tenta_reserva(monkeypatch):
    from vagas_monitor import providers

    class Fatal(ProvPorModelo):
        def classificar_erro(self, exc):
            return "chave inválida", True

    prov = Fatal([])
    monkeypatch.setitem(providers.DISPONIVEIS, "falso", prov)
    with pytest.raises(RuntimeError, match="chave inválida"):
        curriculo.propor("cv", "obj", {"falso": {"modelos_reserva": ["leve"]}}, prov=prov, dormir=lambda s: None)
    assert prov.modelos == ["principal"]


def test_exclusao_da_ia_que_mata_a_propria_area_e_ignorada_com_aviso(raiz, tmp_path):
    """Caso real: a IA mandou excluir 'técnico de enfermagem' de quem é técnica e quer ser enfermeira."""
    cv = tmp_path / "cv.txt"
    cv.write_text("Técnica de Enfermagem.", encoding="utf-8")
    prop = _proposta(areas=[{"slug": "saude", "papel": "alvo", "motivo": "objetivo"}], categorias_extras=[],
                     excluir_titulo=["técnico de enfermagem", "cuidador de idosos", "fiscal de loja"])
    r = assistente.executar_init({**BASE, "curriculo": str(cv), "aprovado": True}, raiz=raiz, proposta_fn=lambda *a: prop)
    cfg = load_config(raiz / "config.yaml")
    assert cfg["excluir_titulo"] == ["fiscal de loja"]  # os dois da própria área saíram
    assert any("ponte" in a and "técnico de enfermagem" in a for a in r["avisos"])
    assert calibracao.decide("Técnico de Enfermagem Plantonista", cfg)[0]  # a profissão atual continua entrando


def test_com_curriculo_as_habilidades_sao_so_as_da_pessoa_e_no_manual_vem_as_do_pack(raiz, tmp_path):
    cv = tmp_path / "cv.txt"
    cv.write_text("Analista financeira.", encoding="utf-8")
    prop = _proposta(habilidades=["excel", "conciliação"])
    assistente.executar_init({**BASE, "curriculo": str(cv), "aprovado": True}, raiz=raiz, proposta_fn=lambda *a: prop)
    assert load_config(raiz / "config.yaml")["habilidades"] == ["excel", "conciliação"]

    r = assistente.executar_init({**BASE, "manual": True, "areas": ["saude"]}, raiz=raiz)
    assert "tasy" in load_config(raiz / "config.yaml")["habilidades"]  # ponto de partida do pack
    assert any("habilidades" in a and "SUAS" in a for a in r["avisos"])


def test_area_repetida_vale_so_a_primeira_vez(raiz):
    r = assistente.executar_init({**BASE, "manual": True, "areas": ["saude:alvo", "saude:ponte", "educacao:adjacente"]},
                                 raiz=raiz)
    cfg = load_config(raiz / "config.yaml")
    assert list(cfg["categorias"]) == ["saude", "educacao"] and cfg["categorias"]["saude"]["bonus"] > 0
    beta = next(a for a in r["avisos"] if "beta" in a)
    assert beta.count("Saúde") == 1
