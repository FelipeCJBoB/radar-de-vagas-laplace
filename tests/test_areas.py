"""Packs de área: os exemplos de cada pack são a especificação dele."""
import pytest

from vagas_monitor import areas, filters
from vagas_monitor.models import Job
from vagas_monitor.text import any_term, normalize

SLUGS = sorted(areas.listar())


def _classe(titulo, cfg):
    vaga = Job(source="t", title=titulo, company="-", url="-")
    if any_term(normalize(titulo), cfg["excluir_titulo"]):
        return "EXCLUIDA"  # exclusão global (só a que a pessoa escreve)
    return filters.classify(vaga, cfg["categorias"])[0]


def test_ha_packs_de_ti_e_de_outras_areas():
    assert len(SLUGS) >= 15
    assert {"ti-dados-ia", "saude", "juridico", "logistica-suprimentos", "educacao"} <= set(SLUGS)


@pytest.mark.parametrize("slug", SLUGS)
def test_pack_tem_o_formato_esperado(slug):
    p = areas.carregar(slug)
    assert p["nome"] and p["status"] in ("beta", "validado")
    for campo in ("titulo", "descricao", "termos_busca", "exemplos_positivos", "exemplos_negativos"):
        assert p[campo], f"{slug}: {campo} vazio"
    assert len(p["exemplos_positivos"]) >= 3 and len(p["exemplos_negativos"]) >= 2


@pytest.mark.parametrize("slug", SLUGS)
def test_exemplos_positivos_classificam_no_proprio_pack(slug):
    cfg = areas.compor([(slug, "alvo")])
    chave = areas.chave(slug)
    erradas = [t for t in areas.carregar(slug)["exemplos_positivos"] if _classe(t, cfg) != chave]
    assert not erradas, f"{slug}: não classificaram: {erradas}"


@pytest.mark.parametrize("slug", SLUGS)
def test_exemplos_negativos_nao_entram(slug):
    cfg = areas.compor([(slug, "alvo")])
    entram = [t for t in areas.carregar(slug)["exemplos_negativos"] if _classe(t, cfg) is not None]
    assert not entram, f"{slug}: entraram indevidamente: {entram}"


def test_com_todos_os_packs_juntos_o_exemplo_cai_na_area_certa():
    """Colisão entre áreas é o risco de generalizar: 'fiscal' de loja não pode virar contábil."""
    cfg = areas.compor([(s, "alvo") for s in SLUGS])
    erros = []
    for slug in SLUGS:
        for t in areas.carregar(slug)["exemplos_positivos"]:
            if _classe(t, cfg) != areas.chave(slug):
                erros.append(f"{t!r} esperado {slug}, veio {_classe(t, cfg)}")
    assert not erros, "\n".join(erros)


def test_homonimo_fiscal_de_loja_sai_da_categoria():
    cfg = areas.compor([("contabil-fiscal", "alvo")])
    assert _classe("Fiscal de Loja - Vaga Natal", cfg) is None
    assert _classe("Analista Fiscal", cfg) == "contabil_fiscal"


def test_exclusao_de_um_pack_nao_mata_a_vaga_de_outro():
    """O defeito que isto previne: com exclusão global, 'segurança do trabalho' (excluída do pack de
    segurança da informação) sumia também do pack de segurança do trabalho."""
    cfg = areas.compor([("ti-infra-devops-seguranca", "alvo"), ("seguranca-trabalho", "alvo"),
                        ("engenharia-civil-construcao", "alvo"), ("contabil-fiscal", "alvo")])
    assert cfg["excluir_titulo"] == []
    assert _classe("Técnico de Segurança do Trabalho", cfg) == "seguranca_trabalho"
    assert _classe("Fiscal de Obras", cfg) == "engenharia_civil_construcao"
    assert _classe("Fiscal de Loja", cfg) is None


def test_seguranca_do_trabalho_nao_e_seguranca_da_informacao():
    cfg = areas.compor([("ti-infra-devops-seguranca", "alvo"), ("seguranca-trabalho", "adjacente")])
    assert _classe("Técnico de Segurança do Trabalho", cfg) == "seguranca_trabalho"
    assert _classe("Analista de Segurança da Informação", cfg) == "ti_infra_devops_seguranca"


# ------------------------------------------------------------------ composição e papéis
def test_papeis_definem_prioridade_e_bonus():
    c = areas.compor([("ti-sistemas-erp", "ponte"), ("ti-dados-ia", "alvo"), ("ti-desenvolvimento", "adjacente")])
    cats = c["categorias"]
    assert [cats[k]["prioridade"] for k in ("ti_dados_ia", "ti_desenvolvimento", "ti_sistemas_erp")] == [1, 2, 3]
    assert cats["ti_dados_ia"]["bonus"] == 12
    assert cats["ti_desenvolvimento"]["bonus"] == 3
    assert cats["ti_sistemas_erp"]["bonus"] < 0


def test_varios_alvos_perdem_bonus_em_ordem():
    c = areas.compor([("saude", "alvo"), ("educacao", "alvo")])["categorias"]
    assert c["saude"]["bonus"] > c["educacao"]["bonus"] > 0


def test_papel_invalido_e_pack_inexistente():
    with pytest.raises(ValueError, match="papel"):
        areas.compor([("saude", "chefe")])
    with pytest.raises(KeyError, match="saude"):
        areas.carregar("saudee")


def test_compor_junta_termos_sem_duplicar():
    c = areas.compor([("administrativo-financeiro", "alvo"), ("contabil-fiscal", "alvo")])
    assert len(c["termos_busca"]) == len(set(c["termos_busca"]))
    assert "fiscal de loja" in c["categorias"]["contabil_fiscal"]["excluir_titulo"]
    assert "excluir_titulo" not in c["categorias"]["administrativo_financeiro"]
