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
| `vagas_monitor/areas.py`, `areas/*.yaml` | packs de área: categorias prontas, com exemplos que viram teste |
| `vagas_monitor/assistente.py` | `init`: gera config, perfil e referência (IA, manual) |
| `vagas_monitor/curriculo.py`, `anonimizar.py` | lê o currículo, tira dados pessoais, pede a proposta à IA |
| `vagas_monitor/calibracao.py` | `calibrar`: recall e corte contra a referência; sondagem do mercado |
| `vagas_monitor/diagnostico.py` | `doctor`: confere config, perfil, canais, IA, fontes |
| `vagas_monitor/segredos.py` | `publicar-secrets`: grava o `.env` nos secrets do GitHub, sem mostrar valores |
| `vagas_monitor/sources/` | uma fonte por arquivo: `gupy.py`, `indeed.py`, `linkedin.py` |
| `vagas_monitor/filters.py`, `scoring.py` | classificação (cidade, categoria, nível) e pontuação |
| `vagas_monitor/enrich.py`, `providers/` | avaliação por IA (Gemini ou Claude), com modelos de reserva |
| `vagas_monitor/report.py`, `notify/` | relatório, painel, Telegram, e-mail |
| `config.yaml` | configuração da pessoa (vem vazia) |
| `tests/config_teste.yaml` | configuração completa usada só pelos testes |

## Comandos

```bash
python -m pytest -q                                          # testes (devem passar sempre)
python tools/leak_check.py                                   # segredos e dados pessoais
python -m vagas_monitor init [--listar-areas]                # configura a pessoa
python -m vagas_monitor doctor [--offline] [--ia]            # diagnóstico
python -m vagas_monitor run --force --dry-run --no-notify    # ensaio: não salva estado, não notifica
python -m vagas_monitor calibrar [--sondar]                  # mede o acerto / sonda o mercado
python -m vagas_monitor classificar "título"                 # por que um título cai (ou não) numa categoria
ruff check vagas_monitor tools tests
python -m pytest -m live -q                                  # contrato ao vivo das fontes (usa a internet)
```

## Regras (não negociáveis)

1. **Nunca imprima, cole ou commite segredos.** `.env`, tokens, senhas de app e chaves de API
   ficam fora do chat e do git. Se a pessoa colar um segredo na conversa, diga para revogá-lo e
   gerar outro. Quem grava os secrets é `publicar-secrets` (lê o `.env`, não mostra valores) ou a
   própria pessoa pela interface do GitHub.
2. **Nunca invente dados do currículo.** O que não estiver escrito fica vazio ou vira pergunta.
3. **Currículo é dado pessoal.** O `init` anonimiza localmente e só envia à IA depois de a pessoa
   aprovar o texto. Se você mesmo for ler o currículo, não o repita em arquivos nem em commits. O
   Gemini gratuito pode usar o texto para treinar: avise.
4. **Não faça merge, push forçado nem apague nada sem a pessoa pedir.** Mostre o que vai fazer.
5. **Rode `pytest`, `ruff check` e `tools/leak_check.py` antes de propor qualquer commit.**
6. **Fim de linha LF e UTF-8** em tudo. O `.gitattributes` já força LF; não converta arquivos.
7. **Não hardcode** estado, cidade, área, nível ou nome de pessoa no código. Há testes que varrem
   isso (`tests/test_genericidade.py`).
8. **Testes não escrevem no repositório real.** Quem grava `config.yaml`, `perfil.md` etc. usa uma
   pasta temporária (veja `tests/test_init_calibrar.py`). Um teste que ignorou isso já sobrescreveu
   o `config.yaml` do repositório.
9. As fontes são APIs **não oficiais** e quebram. Fonte com zero vagas é defeito a investigar, não
   um dia ruim. Corrigido o endereço, acrescente um teste (veja `tests/test_gupy.py`).
10. **Exclusão de homônimo é por categoria** (`categorias.<x>.excluir_titulo`), não global: a global
    mata a vaga legítima de outra categoria.

## Como configurar para a pessoa (procedimento)

Siga nesta ordem e **peça aprovação a cada etapa**. O comando `/personalizar` faz isto.

1. **Entreviste.** Pergunte: o que busca (cargo ou área), nível (estágio, júnior, pleno, sênior,
   liderança), onde mora ou aceita trabalhar (UF e cidade-base), se aceita remoto e, **o mais útil**,
   3 a 10 vagas que ela gostaria de receber e algumas que rejeita. Se ela tiver o currículo em
   arquivo, pergunte o caminho (não peça para colar o texto).
2. **Rode o `init`** com o que ela respondeu. Sem chave de IA, use `--manual` e escolha as áreas do
   catálogo (`init --listar-areas`) com o papel de cada uma: **alvo** (o que ela quer ser),
   **adjacente** (vizinho que também serve) ou **ponte** (o que a experiência sustenta, mas não é o
   desejo). Passe as vagas de referência com `--quero` e `--nao-quero`. Com currículo e chave de IA,
   mostre o texto anonimizado e só envie com a aprovação dela (`--sim`).
3. **Preencha o `perfil.md`** (o `init` manual deixa um esqueleto) só com o que ela disse. Em
   repositório público, oriente a guardá-lo no secret `PERFIL_MD`.
4. **Calibre** ([guia 05](guia/05-calibrar.md)): `calibrar` (recall e corte contra a referência),
   `classificar` para cada erro, `calibrar --sondar` para ver o que o mercado da região tem. Corrija
   o `config.yaml` e repita até bater a meta (80%). Homônimos são a causa mais comum.
5. **Ensaie:** `run --force --dry-run --no-notify`, leia o `reports/LATEST.md` com ela e confira
   categorias, locais e destaques.
6. **`doctor`** para as credenciais; ajude a gerar as que faltam pelo [guia 02](guia/02-contas-e-credenciais.md).
7. **Mostre o resultado** antes de colocar na nuvem: quantas vagas, por categoria, e uma amostra do
   que passou e do que foi cortado. Os packs fora de TI são `beta`: diga isso.

## Quando algo der errado

`guia/09-solucao-de-problemas.md` tem a tabela sintoma, causa e correção. Comece pelo `doctor`. Os
defeitos mais comuns: fonte com zero vagas (a API mudou), token do Telegram revogado (401), senha de
app do Gmail ausente, 503 do Gemini gratuito.
