# Radar de Vagas Laplace

Um monitor de vagas que **você configura para a sua região e a sua área** e que roda sozinho na
nuvem, de graça. A cada 5 dias ele varre **LinkedIn, Indeed e Gupy**, pontua cada vaga contra o seu
perfil e manda o resumo das novas por **Telegram** e **e-mail**, com um relatório completo.

Funciona para qualquer estado do Brasil e qualquer área de atuação, em Windows, Linux e macOS.
Nada vem pré-definido: você informa onde busca, o que busca e em que nível.

| Canal | O que chega | O que precisa |
|---|---|---|
| Markdown | `reports/AAAA-MM-DD.md` e `reports/LATEST.md` | nada |
| Painel HTML | `docs/index.html`, com filtros por categoria, cidade e nível | nada (vira site se você ligar o GitHub Pages) |
| Telegram | resumo das melhores vagas novas | um bot (2 minutos) |
| E-mail | tabela das novas e o relatório em anexo | senha de app do Gmail |
| Nota por IA (opcional) | nota 0 a 10 e um comentário por vaga | chave grátis do Gemini ou da Anthropic |

> **Status:** versão inicial (`0.1.0`). O motor, os testes e a configuração por região já estão
> prontos. A configuração assistida a partir do currículo (`init`), o diagnóstico (`doctor`) e a
> calibração medida (`calibrar`) estão no [ROADMAP](ROADMAP.md). Por enquanto a configuração é
> feita à mão seguindo o [guia](guia/04-personalizar.md), ou com a ajuda do Claude Code.

## Como funciona

```
termos de busca × (suas cidades no LinkedIn | seu estado no Indeed | seu estado na Gupy) + vagas remotas
        │
        ▼  coleta (sources/)                     ~5 a 15 min por rodada, sem login
   deduplica: id do ATS (exato) → título+empresa → tokens parecidos
        │
        ▼  filtros: cidade ou remoto → categoria (título/descrição) → nível
        ▼  pontuação 0-100, com regras explícitas e auditáveis
        ▼  estado (o que já foi visto) → IA (opcional) → relatório → notificações
```

A pontuação é transparente: cada vaga mostra **por que** recebeu a nota (categoria no título +30,
nível-alvo +25, cidade-alvo +20, habilidades suas até +18, nível distante −30...). O nível que
vale +25 é o **seu**: quem busca vaga sênior não recebe o ranking de quem busca estágio.

## Começando

Você precisa de uma conta no GitHub. O resto é gratuito.

**1. Crie a sua cópia.** Botão **Use this template → Create a new repository**. Escolha
**privado**: o seu currículo vai ficar nela (veja [privacidade](guia/06-privacidade.md)).

**2. Instale.** Python 3.10 ou mais novo (o projeto usa 3.12).

```powershell
# Windows (PowerShell)
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

```bash
# Linux e macOS
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
```

**3. Crie as credenciais.** Telegram, Gmail e Gemini, passo a passo e com as armadilhas já
conhecidas, em [guia/02-contas-e-credenciais.md](guia/02-contas-e-credenciais.md). Copie
`.env.example` para `.env` e preencha.

**4. Configure.** Copie `perfil.example.md` para `perfil.md` e preencha. Depois edite o
`config.yaml`: região, nível, termos de busca e categorias. Guia completo, com um exemplo
pronto, em [guia/04-personalizar.md](guia/04-personalizar.md). Ou abra o projeto no Claude Code e
peça "leia o CLAUDE.md e configure o monitor para mim" (ele vai te entrevistar).

**5. Ensaie.** Não salva estado e não notifica:

```bash
python -m vagas_monitor run --force --dry-run --no-notify
```

Confira o `reports/LATEST.md`. As vagas que apareceram são as que você quer? As que você queria
e não vieram? Ajuste o `config.yaml` e repita. É a etapa que mais importa
([guia/04](guia/04-personalizar.md#calibrar-com-vagas-reais)).

**6. Coloque na nuvem.** Em **Settings → Secrets and variables → Actions**, crie os secrets
(`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_TO`,
`GEMINI_API_KEY` e, se o repositório for público, `PERFIL_MD`). Em **Settings → Actions →
General → Workflow permissions**, marque *Read and write*. Depois, em **Actions → Monitor de
vagas → Run workflow**, rode a primeira vez. A partir daí ele roda sozinho: o cron dispara todo
dia às 08:00 (Brasília) e o script só coleta quando passaram 5 dias da última rodada.

## Comandos

```bash
python -m vagas_monitor run [--force] [--dry-run] [--no-notify] [--lookback N] [--skip FONTE]
python -m vagas_monitor status         # última execução e se já é hora de rodar
python -m vagas_monitor test-notify    # manda uma mensagem de teste nos canais configurados
python -m vagas_monitor check-ia       # valida a chave da IA com uma chamada real
python -m vagas_monitor setup-telegram # descobre o chat_id do seu bot e grava no .env
python -m vagas_monitor render         # regera Markdown e painel a partir do último JSON
python -m pytest -q                    # testes
python tools/leak_check.py             # procura segredos e dados pessoais antes de um push
```

`run` sai com código 2 e lista o que falta quando o `config.yaml` está incompleto, e com código 1
quando um canal de notificação falha. Quando uma fonte volta com zero vagas, o aviso aparece no
topo do relatório, no Telegram e no e-mail.

## Tecnologias mais pedidas

Cada rodada conta **em quantas vagas cada tecnologia aparece** (uma vez por vaga) e ranqueia pela
contagem, sem peso nem filtro de perfil. Sai no relatório, no painel e nas notificações. A lista
de tecnologias vive em `skills.yaml`; um item é uma tecnologia, e os termos dele são só grafias da
mesma coisa. Mudou o arquivo? `python -m vagas_monitor render` refaz o ranking da última rodada.

## Avaliação por IA (opcional)

Com uma chave, as melhores vagas novas recebem nota de 0 a 10 e um comentário, escritos a
partir do **seu** perfil. `avaliacao.provedor: auto` usa o primeiro provedor que achar chave,
preferindo o Gemini.

| | Gemini (Google AI Studio) | Claude (Anthropic) |
|---|---|---|
| Custo | nível gratuito | pré-pago, centavos por rodada |
| Chave | <https://aistudio.google.com/apikey> | <https://console.anthropic.com> |
| Privacidade | no nível gratuito o Google **pode usar o texto para treinar** | não usa para treinar |
| Variável | `GEMINI_API_KEY` | `ANTHROPIC_API_KEY` |

Uma assinatura (Gemini Pro, Claude.ai) **não** dá chave de API: são cobranças separadas. O
nível gratuito do Gemini às vezes responde 503 por sobrecarga; o monitor tenta de novo e, se não
der, segue sem as notas (o motivo aparece no relatório). A avaliação nunca derruba a rodada.

## Limites, fontes e termos de uso

- **LinkedIn:** endpoint público de convidado. Em IP de nuvem pode devolver 429; o coletor espera
  e tenta de novo.
- **Indeed:** via `python-jobspy`. Às vezes publica sem o nome da empresa.
- **Gupy:** API pública do portal, muito usada por empresas médias e grandes. **Não é uma API
  oficial**: já mudou de endereço uma vez e vai mudar de novo. Se uma fonte vier com zero vagas,
  veja [guia/09](guia/09-solucao-de-problemas.md).
- **Cobertura por área:** as três fontes não servem igual para todas as áreas. Vagas
  operacionais e de saúde aparecem menos que as de escritório e tecnologia. Confira no ensaio.
- **Uso pessoal.** O monitor foi feito para uso pessoal e de baixo volume. Respeite os termos de
  uso de cada site, não aumente a frequência além de uma rodada a cada poucos dias e não use
  proxy para contornar bloqueio. A responsabilidade pelo uso é de quem roda.
- **Só Brasil.** A Gupy é brasileira e as buscas do Indeed e do LinkedIn estão configuradas
  para o Brasil.

## Estrutura

```
vagas_monitor/   o motor (coleta, filtros, pontuação, relatório, notificações)
dados/           snapshot do IBGE: 5.571 municípios e as regiões imediatas
tests/           os testes (config_teste.yaml é a configuração usada por eles)
tools/           leak_check.py (segredos e dados pessoais), atualizar_ibge.py
guia/            guias passo a passo
.claude/         comandos para o Claude Code (/personalizar, /calibrar, /diagnosticar)
config.yaml      a sua configuração (vem vazia de propósito)
perfil.example.md  modelo do seu perfil
```

## Contribuindo

Veja o [CONTRIBUTING](CONTRIBUTING.md). As contribuições mais valiosas são **corrigir uma fonte
que quebrou** e **validar categorias para uma área de atuação** que você conhece.

Licença: [MIT](LICENSE).
