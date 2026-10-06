"""Contrato AO VIVO das fontes: a resposta ainda tem o formato que o coletor espera?

Estes testes usam a internet e APIs de terceiros que mudam sem aviso, por isso ficam fora do
`pytest` padrão (marcador `live`). Rodam todo dia em `.github/workflows/saude-fontes.yml`,
só no repositório-modelo, e uma falha abre uma issue "Fonte X mudou". Foi assim que a Gupy
ficou dias com zero vagas sem ninguém notar; aqui a mudança aparece em 24 horas.

    python -m pytest -m live -q
"""
import pytest
import requests

from vagas_monitor import diagnostico
from vagas_monitor.sources import gupy

pytestmark = pytest.mark.live
CIDADE_DE_TESTE = {"_estados": ["São Paulo"], "cidades": ["São Paulo"]}


def test_gupy_responde_com_os_campos_que_o_coletor_usa():
    r = requests.get(gupy.BASE, params={"jobName": "", "state": "São Paulo", "limit": 5, "offset": 0},
                     headers=gupy.HEADERS, timeout=40)
    assert r.status_code == 200, f"Gupy respondeu {r.status_code}: a API pública mudou de endereço?"
    dados = r.json().get("data") or []
    assert dados, "Gupy respondeu sem nenhuma vaga em São Paulo"
    faltam = [c for c in diagnostico.CAMPOS_GUPY if c not in dados[0]]
    assert not faltam, f"campos ausentes na resposta da Gupy: {faltam}"


def test_gupy_filtra_por_estado_e_por_remoto():
    estado = requests.get(gupy.BASE, params={"jobName": "", "state": "Paraíba", "limit": 20}, headers=gupy.HEADERS,
                          timeout=40).json().get("data") or []
    assert estado and {v["state"] for v in estado} == {"Paraíba"}, "o filtro `state` da Gupy deixou de funcionar"
    remotas = requests.get(gupy.BASE, params={"jobName": "analista", "workplaceType": "remote", "limit": 20},
                           headers=gupy.HEADERS, timeout=40).json().get("data") or []
    assert remotas and {v["workplaceType"] for v in remotas} == {"remote"}, \
        "o filtro `workplaceType=remote` da Gupy deixou de funcionar"


def test_gupy_coletor_devolve_vagas_do_estado():
    vagas = gupy.collect([], 30, include_remote=False, estados=["Paraíba"])
    assert len(vagas) > 10, f"o coletor da Gupy trouxe só {len(vagas)} vagas da Paraíba em 30 dias"
    assert all(v.title and v.url for v in vagas)


def test_linkedin_convidado_devolve_cartoes_de_vaga():
    itens = diagnostico.verificar_linkedin(CIDADE_DE_TESTE)
    assert itens[0].nivel in ("ok", "aviso"), f"{itens[0].titulo}: {itens[0].detalhe}"  # 429 é aviso, não quebra


def test_indeed_via_jobspy_devolve_vagas():
    from vagas_monitor.sources import indeed
    vagas = indeed.collect(["analista"], 3, results_wanted=5, include_remote=False, locais=["São Paulo"])
    assert vagas, "o Indeed (via jobspy) não devolveu nenhuma vaga para 'analista' em São Paulo"
    assert all(v.title and v.url for v in vagas)


def test_ibge_continua_servindo_os_municipios():
    r = requests.get("https://servicodados.ibge.gov.br/api/v1/localidades/municipios", timeout=60)
    assert r.status_code == 200 and len(r.json()) > 5500, "a API de localidades do IBGE mudou"
    assert "regiao-imediata" in r.json()[0], "o snapshot (tools/atualizar_ibge.py) depende deste campo"
