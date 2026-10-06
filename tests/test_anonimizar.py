"""Anonimização local do currículo: nenhum dado pessoal plantado pode sobreviver."""
from vagas_monitor.anonimizar import anonimizar, resumo

CV = """Maria Aparecida Souza Lima
Analista Financeira

Contato: (83) 98765-4321 | maria.lima@provedor.com.br | linkedin.com/in/maria-lima-123
Endereço: Rua das Flores, 123, Bairro Centro, João Pessoa - PB, CEP 58000-000
CPF 123.456.789-09   RG 1.234.567
Data de nascimento: 12/03/1990

Experiência
Analista Financeira Pleno, Empresa Alfa Ltda, 2019 - 2024
- Conciliação bancária, fluxo de caixa e contas a pagar, com Excel avançado e SAP.
Assistente Financeiro, Banco Beta, 2016 - 2019

Formação: Ciências Contábeis, Universidade Gama (2012 - 2016)
Portfólio: https://maria.dev/portfolio
"""


def limpo(**kw):
    return anonimizar(CV, **kw)


def test_nenhum_dado_pessoal_plantado_sobrevive():
    texto, achados = limpo()
    for vazou in ("98765-4321", "maria.lima@", "linkedin.com/in", "Rua das Flores", "58000-000",
                  "123.456.789-09", "1.234.567", "12/03/1990", "maria.dev"):
        assert vazou not in texto, vazou
    assert {"e-mail", "link", "CPF", "telefone", "CEP", "nascimento"} <= set(achados)


def test_o_nome_da_primeira_linha_sai_inclusive_pedacos_dele():
    texto, achados = limpo()
    assert "Maria" not in texto and "Aparecida" not in texto and achados["nome"] >= 1


def test_nome_informado_vale_para_o_texto_inteiro():
    texto, _ = anonimizar("Fui apresentada como Joana Prado. Joana trabalha em vendas.", nomes=["Joana Prado"])
    assert "Joana" not in texto and "Prado" not in texto


def test_o_conteudo_profissional_continua_la():
    texto, _ = limpo()
    for fica in ("Analista Financeira Pleno", "Conciliação bancária", "fluxo de caixa", "Excel", "SAP",
                 "Ciências Contábeis", "2019 - 2024", "2016 - 2019"):
        assert fica in texto, fica


def test_ocultar_empregadores_e_escolas():
    texto, achados = limpo(ocultar=["Empresa Alfa Ltda", "Banco Beta", "Universidade Gama"])
    assert "Alfa" not in texto and "Beta" not in texto and "Gama" not in texto and achados["ocultado"] == 3


def test_palavras_comuns_nao_viram_dado_pessoal():
    texto, _ = anonimizar("Responsabilidade 2020, entidade 2021 e cidade 2022. 5 anos de experiência.")
    assert "Responsabilidade 2020" in texto and "5 anos de experiência" in texto


def test_primeira_linha_que_nao_e_nome_fica():
    texto, achados = anonimizar("Analista de Dados\nPython e SQL")
    assert "Analista de Dados" in texto and "nome" not in achados


def test_resumo_legivel():
    assert "e-mail" in resumo({"e-mail": 1}) and "nenhum" in resumo({})
