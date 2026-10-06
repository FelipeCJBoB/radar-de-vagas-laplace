"""`classificar`: a ferramenta que explica por que um título cai (ou não) numa categoria."""
from conftest import CONFIG_TESTE

from vagas_monitor.__main__ import explicar_titulo, main
from vagas_monitor.config import load_config


def texto(titulo, **cfg_extra):
    cfg = load_config(CONFIG_TESTE)
    cfg.update(cfg_extra)
    return "\n".join(explicar_titulo(titulo, cfg))


def test_mostra_o_termo_que_decidiu():
    t = texto("Analista de Dados Júnior - Itajaí")
    assert "Dados (+30) por título: dados <- principal" in t
    assert "nível detectado: junior" in t and "cidade-alvo no título: Itajaí" in t


def test_titulo_sem_categoria_diz_que_sera_descartado():
    assert "SEM CATEGORIA" in texto("Cozinheiro de restaurante")


def test_exclusao_aparece_antes_da_categoria():
    t = texto("Analista de Dados Júnior", excluir_titulo=["analista de dados"])
    assert "EXCLUÍDA por excluir_titulo: analista de dados" in t and "Dados (+30)" not in t


def test_comando_roda_pelo_cli(capsys):
    assert main(["--config", str(CONFIG_TESTE), "classificar", "Analista SAP SD"]) == 0
    assert "Sistemas e ERP" in capsys.readouterr().out
