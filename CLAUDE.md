# CLAUDE.md — Radar de Vagas Laplace

Instruções para o Claude Code. Leia antes de agir.

## O que é

Monitor de vagas em Python que roda no GitHub Actions. Coleta LinkedIn, Indeed e Gupy, pontua
contra o perfil da pessoa e notifica por Telegram e e-mail. É um **modelo**: quem usa o configura
para a própria região, área e nível. Nada vem pré-definido, de propósito (zero-default).

## Mapa

| Caminho | O que é |
|---|---|
| `vagas_monitor/pipeline.py` | orquestra a rodada: coleta, filtra, pontua, IA, relatório, estado, notificação |
| `vagas_monitor/validar.py` | valida o `config.yaml`, resolve a região, monta o contexto da IA |
| `vagas_monitor/geografia.py` | catálogo do IBGE (UFs, municípios, região imediata) |
| `vagas_monitor/sources/` | uma fonte por arquivo: `gupy.py`, `indeed.py`, `linkedin.py` |
| `vagas_monitor/filters.py`, `scoring.py` | classificação (cidade, categoria, nível) e pontuação |
| `vagas_monitor/enrich.py`, `providers/` | avaliação por IA (Gemini ou Claude) |
| `vagas_monitor/report.py`, `notify/` | relatório, painel, Telegram, e-mail |
| `config.yaml` | configuração da pessoa (vem vazia) |
| `perfil.example.md` | modelo do perfil; o real é `perfil.md` ou o secret `PERFIL_MD` |
| `tests/config_teste.yaml` | configuração completa usada só pelos testes |

## Comandos

```bash
python -m pytest -q                                          # testes (devem passar sempre)
python tools/leak_check.py                                   # segredos e dados pessoais
python -m vagas_monitor run --force --dry-run --no-notify    # ensaio: não salva estado, não notifica
python -m vagas_monitor status | check-ia | test-notify
ruff check vagas_monitor tools tests
```

## Regras (não negociáveis)

1. **Nunca imprima, cole ou commite segredos.** `.env`, tokens, senhas de app e chaves de API
   ficam fora do chat e do git. Se a pessoa colar um segredo na conversa, diga para revogá-lo e
   gerar outro. Quem grava os secrets no GitHub é a pessoa, pela interface ou pelo `gh`.
2. **Nunca invente dados do currículo.** O que não estiver escrito fica vazio ou vira pergunta.
3. **Currículo é dado pessoal.** Antes de enviá-lo a qualquer IA externa, avise a pessoa e
   remova nome, CPF, telefone, e-mail e endereço. O Gemini gratuito pode usar o texto para treinar.
4. **Não faça merge, push forçado nem apague nada sem a pessoa pedir.** Mostre o que vai fazer.
5. **Rode `pytest` e `tools/leak_check.py` antes de propor qualquer commit.**
6. **Fim de linha LF e UTF-8** em tudo. O `.gitattributes` já força LF; não converta arquivos.
7. **Não hardcode** estado, cidade, área, nível ou nome de pessoa no código. Há um teste que
   varre o código por isso (`tests/test_genericidade.py`).
8. As fontes são APIs **não oficiais** e quebram. Fonte com zero vagas é defeito a investigar, não
   um dia ruim.

## Como configurar para a pessoa (procedimento)

Siga nesta ordem e **peça aprovação a cada etapa**. O comando `/personalizar` faz isto.

1. **Entreviste.** Pergunte: o que busca (cargo ou área), nível (estágio, júnior, pleno, sênior,
   liderança), onde mora ou aceita trabalhar (UF e cidade-base), se aceita remoto, o que já fez
   (formação, experiência, ferramentas, registros profissionais como CRC, COREN, OAB, CREA) e,
   **o mais útil**, 3 a 10 vagas que ela gostaria de receber e algumas que ela rejeita.
2. **Escreva o `perfil.md`** a partir de `perfil.example.md`, só com o que a pessoa disse. Em
   repositório público, oriente a guardá-lo no secret `PERFIL_MD` em vez de commitá-lo.
3. **Preencha a `regiao` e o `alvo`** do `config.yaml`. Cidade digitada errada é corrigida pelo
   catálogo do IBGE (`vagas_monitor.geografia.sugestoes`). Prefira `alcance: regiao_imediata`.
4. **Monte os `termos_busca`, as `categorias` e a `senioridade`.** Veja `guia/04-personalizar.md`.
   Use três papéis: **alvo** (o que ela quer ser: `bonus` positivo), **adjacente** (`bonus` 0) e
   **ponte** (o que a experiência sustenta mas não é o desejo: `bonus` negativo).
5. **Valide:** `python -m vagas_monitor run --force --dry-run --no-notify`. Se faltar algo, a
   mensagem lista a pendência.
6. **Calibre com vagas reais** (`guia/04`, seção "Calibrar"): rode o ensaio, leia o
   `reports/LATEST.md` e procure (a) as vagas que ela queria e **não** vieram, e (b) as que vieram
   e **não** servem (falsos positivos). Para cada uma, descubra qual termo pegou ou faltou
   (`filters.classify`). Homônimos são a causa mais comum: "fiscal" de loja contra fiscal
   tributário, "segurança" do trabalho contra da informação. Resolva com `excluir_titulo` ou
   troque o termo por uma expressão mais específica.
7. **Mostre o resultado** antes de colocar na nuvem: quantas vagas, por categoria, e uma amostra do
   que passou e do que foi cortado.

## Quando algo der errado

`guia/09-solucao-de-problemas.md` tem a tabela sintoma, causa e correção. Os defeitos mais
comuns: fonte com zero vagas (a API mudou), token do Telegram revogado (401), senha de app do Gmail
ausente, 503 do Gemini gratuito.
