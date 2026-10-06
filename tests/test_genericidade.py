"""Genericidade: o monitor não pode assumir estado, cidade, nível nem perfil.

Cada teste aqui existe por um acoplamento que havia (ou poderia haver): estado fixo
nas três fontes, pontuação feita para quem busca vaga júnior, prompt da IA com o
perfil de uma pessoa escrito no código, config de exemplo que parecia padrão.
"""
import re
from datetime import date
from pathlib import Path

import pytest
import yaml
from conftest import CONFIG_TESTE

from vagas_monitor import config, enrich, geografia, pipeline, scoring
from vagas_monitor.config import load_config
from vagas_monitor.models import Job
from vagas_monitor.validar import (ConfigInvalida, contexto_ia, resolver_regiao, validar_config)

RAIZ = Path(__file__).resolve().parent.parent


def cfg_com(**mudancas):
    """Config de teste com a região/alvo trocados, já resolvida."""
    cfg = yaml.safe_load(CONFIG_TESTE.read_text(encoding="utf-8"))
    for chave, valor in mudancas.items():
        cfg[chave] = valor
    return resolver_regiao(cfg)


PB = {"estados": ["PB"], "base": {"cidade": "João Pessoa", "uf": "PB"}, "remoto": "aceitar"}
JUNIOR = {"nivel": "junior"}


# --------------------------------------------------------------------- geografia
def test_uf_aceita_sigla_nome_e_acento():
    assert geografia.uf_sigla("PB") == "PB" and geografia.uf_sigla("pb") == "PB"
    assert geografia.uf_sigla("Paraíba") == "PB" and geografia.uf_sigla("paraiba") == "PB"
    assert geografia.uf_nome("sp") == "São Paulo"
    assert geografia.uf_sigla("Atlantida") is None


def test_catalogo_do_ibge_esta_completo():
    assert len(geografia.municipios()) > 5500 and len(geografia.ufs()) == 27


def test_cidade_sem_acento_e_em_outra_caixa():
    assert geografia.buscar_cidade("joao pessoa", "PB")["nome"] == "João Pessoa"
    assert geografia.buscar_cidade("Santa Cruz", "PB") is None or geografia.buscar_cidade("Santa Cruz", "PB")["uf"] == "PB"


def test_regiao_imediata_inclui_a_base_e_vizinhas():
    cidades = geografia.cidades_da_regiao_imediata("Campinas", "SP")
    assert "Campinas" in cidades and len(cidades) > 3


def test_sugestao_para_cidade_digitada_errado():
    assert "João Pessoa" in geografia.sugestoes("Joao Pesoa", "PB")


def test_localidade_do_linkedin():
    assert geografia.localidade("campinas", ["São Paulo"]) == "Campinas, São Paulo, Brasil"
    assert geografia.localidade("Cidade Que Nao Existe", ["São Paulo"]) is None


# --------------------------------------------------------------------- zero-default
def test_config_do_modelo_nao_traz_nada_pre_definido():
    cfg = load_config(RAIZ / "config.yaml")
    erros = " ".join(validar_config(cfg))
    for pendencia in ("regiao.estados", "regiao.base.cidade", "alvo.nivel", "termos_busca", "categorias"):
        assert pendencia in erros, pendencia
    assert cfg["cidades"] == [] and cfg["_estados"] == []


def test_rodada_recusa_config_vazio():
    with pytest.raises(ConfigInvalida) as e:
        pipeline.run(force=True, dry_run=True, config_path=RAIZ / "config.yaml")
    assert "regiao.estados" in str(e.value)


def test_cli_run_sai_com_codigo_2_e_mostra_as_pendencias(capsys):
    from vagas_monitor.__main__ import main
    assert main(["--config", str(RAIZ / "config.yaml"), "run", "--force"]) == 2
    assert "pendência" in capsys.readouterr().out


def test_config_de_teste_e_valido():
    assert validar_config(load_config(CONFIG_TESTE)) == []


def test_cidade_inexistente_sugere_correcao():
    cfg = cfg_com(regiao={**PB, "base": {"cidade": "Joao Pesoa", "uf": "PB"}}, alvo=JUNIOR)
    erros = " ".join(validar_config(cfg))
    assert "Joao Pesoa" in erros and "João Pessoa" in erros


def test_so_remoto_dispensa_estado_e_cidade():
    cfg = cfg_com(regiao={"remoto": "somente"}, alvo=JUNIOR)
    assert not [e for e in validar_config(cfg) if "regiao" in e]


def test_nivel_e_remoto_invalidos():
    cfg = cfg_com(regiao={**PB, "remoto": "talvez"}, alvo={"nivel": "mestre"})
    erros = " ".join(validar_config(cfg))
    assert "regiao.remoto" in erros and "alvo.nivel" in erros


def test_resolucao_da_regiao_para_outro_estado():
    cfg = cfg_com(regiao={**PB, "alcance": "regiao_imediata"}, alvo=JUNIOR)
    assert cfg["_estados"] == ["Paraíba"] and "João Pessoa" in cfg["cidades"]
    assert not any(c in cfg["cidades"] for c in ("Itajaí", "Blumenau"))


def test_alcance_estado_inteiro():
    cfg = cfg_com(regiao={**PB, "alcance": "estado"}, alvo=JUNIOR)
    assert "João Pessoa" in cfg["cidades"] and len(cfg["cidades"]) > 200


# --------------------------------------------------------------------- fontes recebem a região
def _espiar(monkeypatch):
    visto = {}
    monkeypatch.setattr(pipeline.gupy, "collect", lambda terms, lb, remoto, estados=None, **k: visto.update(gupy=(remoto, estados)) or [])
    monkeypatch.setattr(pipeline.indeed, "collect", lambda terms, lb, n, remoto, locais=None, **k: visto.update(indeed=(remoto, locais)) or [])
    monkeypatch.setattr(pipeline.linkedin, "collect", lambda terms, locais, lb, remoto, pags, **k: visto.update(linkedin=(remoto, locais)) or [])
    return visto


def test_estado_chega_as_tres_fontes(monkeypatch):
    visto = _espiar(monkeypatch)
    cfg = cfg_com(regiao=PB, alvo=JUNIOR, fontes={})
    pipeline.collect_all(cfg, 7, {})
    assert visto["gupy"] == (True, ["Paraíba"])
    assert visto["indeed"] == (True, ["Paraíba"])
    assert visto["linkedin"] == (True, ["João Pessoa, Paraíba, Brasil"])


def test_varios_estados(monkeypatch):
    visto = _espiar(monkeypatch)
    cfg = cfg_com(regiao={**PB, "estados": ["PB", "PE"]}, alvo=JUNIOR, fontes={})
    pipeline.collect_all(cfg, 7, {})
    assert visto["gupy"][1] == ["Paraíba", "Pernambuco"]


def test_cidades_ancora_configuradas_viram_locais_do_linkedin(monkeypatch):
    visto = _espiar(monkeypatch)
    cfg = cfg_com(regiao=PB, alvo=JUNIOR, fontes={"linkedin": {"cidades_ancora": ["Campina Grande", "João Pessoa"]}})
    pipeline.collect_all(cfg, 7, {})
    assert visto["linkedin"][1] == ["Campina Grande, Paraíba, Brasil", "João Pessoa, Paraíba, Brasil"]


def test_somente_remoto_nao_faz_busca_presencial(monkeypatch):
    visto = _espiar(monkeypatch)
    cfg = cfg_com(regiao={"remoto": "somente"}, alvo=JUNIOR, fontes={})
    pipeline.collect_all(cfg, 7, {})
    assert visto["gupy"] == (True, []) and visto["indeed"] == (True, []) and visto["linkedin"] == (True, [])


def test_sem_remoto_as_fontes_nao_buscam_remotas(monkeypatch):
    visto = _espiar(monkeypatch)
    pipeline.collect_all(cfg_com(regiao={**PB, "remoto": "nao"}, alvo=JUNIOR, fontes={}), 7, {})
    assert visto["gupy"][0] is False and visto["linkedin"][0] is False


# --------------------------------------------------------------------- escopo por modo remoto
def _vaga(workplace="onsite", city="João Pessoa", title="Analista de Dados"):
    return Job(source="gupy", title=title, company="ACME", url="https://g/1", city=city,
               state="Paraíba", workplace=workplace, description="sql python")


@pytest.mark.parametrize("remoto,workplace,cidade,fica", [
    ("aceitar", "remote", "", True), ("preferir", "remote", "", True),
    ("nao", "remote", "", False), ("nao", "onsite", "João Pessoa", True),
    ("somente", "remote", "", True), ("somente", "onsite", "João Pessoa", False),
])
def test_modo_remoto_define_o_escopo(remoto, workplace, cidade, fica):
    cfg = cfg_com(regiao={**PB, "remoto": remoto}, alvo=JUNIOR)
    assert pipeline.annotate(_vaga(workplace, cidade), cfg, date(2026, 10, 1)) is fica


# --------------------------------------------------------------------- pontuação por nível
def _pontos(alvo, vaga, aceita=None, remoto="aceitar"):
    cfg = cfg_com(regiao={**PB, "remoto": remoto}, alvo={"nivel": alvo, "aceita_niveis": aceita or []})
    return scoring._pontos_nivel(vaga, cfg)[0]


@pytest.mark.parametrize("alvo,vaga,esperado", [
    ("junior", "junior", 25), ("junior", "pleno", 8), ("junior", "senior", -30),   # idêntico ao comportamento antigo
    ("pleno", "pleno", 25), ("pleno", "junior", 8), ("pleno", "senior", 8),
    ("senior", "senior", 25), ("senior", "pleno", 8), ("senior", "junior", -30),
    ("estagio", "junior", 25), ("lideranca", "senior", 25),
    ("junior", "unknown", 5),
])
def test_pontos_pela_distancia_do_nivel(alvo, vaga, esperado):
    assert _pontos(alvo, vaga) == esperado


def test_nivel_aceito_nunca_fica_abaixo_do_vizinho():
    assert _pontos("pleno", "junior", aceita=["junior"]) == 8
    assert _pontos("junior", "senior", aceita=["senior"]) == 8


def test_para_quem_busca_senior_a_vaga_junior_nao_lidera():
    """O bug que isto previne: com as constantes antigas o ranking de um sênior saía invertido."""
    cfg = cfg_com(regiao=PB, alvo={"nivel": "senior"})
    j = _vaga()
    j.category, j.categories, j.seniority = "dados", ["dados"], "junior"
    s_junior, _ = scoring.score_job(j, cfg, {"dados": 30}, date(2026, 10, 1))
    j.seniority = "senior"
    s_senior, _ = scoring.score_job(j, cfg, {"dados": 30}, date(2026, 10, 1))
    assert s_senior > s_junior


def test_remoto_so_pontua_quando_preferido():
    j = _vaga("remote", "")
    j.category, j.categories, j.seniority = "dados", ["dados"], "junior"
    pref = scoring.score_job(j, cfg_com(regiao={**PB, "remoto": "preferir"}, alvo=JUNIOR), {"dados": 30}, date(2026, 10, 1))[0]
    aceita = scoring.score_job(j, cfg_com(regiao={**PB, "remoto": "aceitar"}, alvo=JUNIOR), {"dados": 30}, date(2026, 10, 1))[0]
    assert pref - aceita == 12


# --------------------------------------------------------------------- perfil e prompt da IA
def test_perfil_md_tem_precedencia_sobre_o_arquivo(monkeypatch):
    monkeypatch.setenv("PERFIL_MD", "perfil vindo do secret")
    assert config.load_profile({"perfil": "perfil.md"}) == "perfil vindo do secret"


def test_sem_perfil_nem_variavel_devolve_vazio(monkeypatch):
    monkeypatch.delenv("PERFIL_MD", raising=False)
    assert config.load_profile({"perfil": "arquivo_que_nao_existe.md"}) == ""


def test_prompt_da_ia_vem_do_contexto_e_nao_de_um_perfil_fixo():
    ctx = contexto_ia(cfg_com(regiao=PB, alvo={"nivel": "senior"}, categorias={
        "fin": {"nome": "Financeiro", "prioridade": 1, "titulo": ["financeiro"]}}))
    sistema = enrich.montar_system(ctx)
    assert "Financeiro" in sistema and "sênior" in sistema and "pt-BR" in sistema
    for resto_do_perfil_antigo in ("ADS", "Python", "Power BI", "transição de carreira", "júnior"):
        assert resto_do_perfil_antigo not in sistema


def test_prompt_sem_contexto_continua_generico():
    assert "área de atuação do candidato" in enrich.montar_system(None)


# --------------------------------------------------------------------- nada geográfico fixo no código
# Só geografia. Termos PESSOAIS (nome, empregador, e-mail) não podem aparecer nem aqui: eles
# vivem numa lista de bloqueio local, fora do git (veja tools/leak_check.py).
PROIBIDOS = re.compile(r"Itaja[ií]|Santa Catarina|Blumenau|Joinville|Norte de SC|\bSC\b")


def test_nenhum_literal_geografico_no_codigo():
    achados = []
    for arq in sorted((RAIZ / "vagas_monitor").rglob("*.py")):
        for n, linha in enumerate(arq.read_text(encoding="utf-8").splitlines(), 1):
            if PROIBIDOS.search(linha):
                achados.append(f"{arq.relative_to(RAIZ)}:{n}: {linha.strip()[:80]}")
    assert not achados, "literal pessoal/geográfico no código:\n" + "\n".join(achados)


def test_config_e_skills_do_modelo_nao_tem_regiao_fixa():
    for nome in ("config.yaml", "skills.yaml", "pyproject.toml"):
        texto = (RAIZ / nome).read_text(encoding="utf-8")
        assert not PROIBIDOS.search(texto), nome
