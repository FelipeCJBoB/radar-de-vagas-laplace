# Radar de Vagas Laplace

Um monitor de vagas que **você configura para a sua região e a sua área** e que roda sozinho na
nuvem, de graça. A cada 5 dias ele varre **LinkedIn, Indeed e Gupy**, pontua cada vaga contra o seu
perfil e manda o resumo das novas por **Telegram** e **e-mail**, com um relatório completo.

Funciona para **qualquer estado do Brasil e qualquer área de atuação**, em Windows, Linux e macOS.
Nada vem pré-definido: você informa onde busca, o que busca e em que nível, e o monitor se
calibra com vagas reais da sua região.

| Canal | O que chega | O que precisa |
|---|---|---|
| Markdown | `reports/AAAA-MM-DD.md` e `reports/LATEST.md` | nada |
| Painel HTML | `docs/index.html`, com filtros por categoria, cidade e nível | nada (anexado ao e-mail e ao Telegram em repositório privado; vira site com GitHub Pages) |
| Telegram | resumo das melhores vagas novas | um bot (2 minutos) |
| E-mail | tabela das novas, relatório e painel em anexo | senha de app do Gmail |
| Nota por IA (opcional) | nota 0 a 10 e um comentário por vaga | chave grátis do Gemini ou da Anthropic |

## Começando

Você precisa de uma conta no GitHub e de Python 3.10 ou mais novo. O resto é gratuito.

**1. Crie a sua cópia.** Botão **Use this template → Create a new repository**. Escolha
**privado**: o seu perfil vai ficar nela ([privacidade](guia/06-privacidade.md)). Clone-a e instale:

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

**2. Configure com `init`.** Ele pergunta a sua região, o nível e a área, e gera o `config.yaml`
e o `perfil.md`. Há três caminhos, que gravam os mesmos arquivos e passam pela mesma validação:

```bash
python -m vagas_monitor init
```

- **A partir do currículo** (`--curriculo cv.pdf`, .docx, .txt ou .md): uma IA propõe as áreas, os
  termos de busca e o perfil. O currículo é **anonimizado na sua máquina** (nome, CPF, telefone,
  e-mail e endereço saem) e só vai à IA depois que você aprova o texto na tela.
- **Manual, sem IA** (`--manual`): você escolhe áreas do catálogo (17 prontas, de TI a saúde, direito,
  logística, educação e mais) e o papel de cada uma. Veja o catálogo: `init --listar-areas`.
- **Com o Claude Code**: abra o projeto e rode `/personalizar`. Ele te entrevista e usa as mesmas
  funções.

**3. Calibre.** O passo que separa um monitor útil de um que parece certo
([guia 05](guia/05-calibrar.md)):

```bash
python -m vagas_monitor run --force --dry-run --no-notify   # ensaio: leia reports/LATEST.md
python -m vagas_monitor calibrar                            # recall e corte contra as suas vagas de referência
python -m vagas_monitor calibrar --sondar                   # o que o mercado da sua região tem e o config não pega
```

**4. Credenciais.** Telegram, Gmail e Gemini, passo a passo e com as armadilhas já conhecidas, em
[guia/02-contas-e-credenciais.md](guia/02-contas-e-credenciais.md). Copie `.env.example` para
`.env`, preencha e confira:

```bash
python -m vagas_monitor doctor
```

**5. Coloque na nuvem.**

```bash
python -m vagas_monitor publicar-secrets     # grava os secrets do .env no GitHub, sem mostrar os valores
```

Em **Settings → Actions → General → Workflow permissions** marque *Read and write*. Depois, em
**Actions → Monitor de vagas → Run workflow**, rode a primeira vez. A partir daí ele roda sozinho:
o cron dispara todo dia às 08:00 (Brasília) e o script só coleta quando passaram 5 dias da última
rodada. Detalhes em [guia/03-primeira-rodada.md](guia/03-primeira-rodada.md).

## Como funciona

```
termos de busca × (suas cidades no LinkedIn | seu estado no Indeed | seu estado na Gupy) + vagas remotas
        │
        ▼  coleta (sources/)                     ~5 a 15 min por rodada, sem login
   deduplica: id da fonte (exato) → título+empresa → tokens parecidos
        │
        ▼  filtros: cidade ou remoto → categoria (título/descrição) → nível
        ▼  pontuação 0-100, com regras explícitas e auditáveis
        ▼  estado (o que já foi visto) → IA (opcional) → relatório → notificações
```

A pontuação é transparente: cada vaga mostra **por que** recebeu a nota (categoria no título +30,
nível-alvo +25, cidade-alvo +20, habilidades suas até +18, nível distante −30...). O nível que vale
+25 é o **seu**: quem busca vaga sênior não recebe o ranking de quem busca estágio.

## Comandos

```bash
python -m vagas_monitor init                 # configura região, nível, áreas e perfil
python -m vagas_monitor doctor               # confere config, perfil, Telegram, e-mail, IA, fontes (e como corrigir)
python -m vagas_monitor run [--force] [--dry-run] [--no-notify] [--lookback N] [--skip FONTE]
python -m vagas_monitor calibrar [--sondar]  # mede o acerto / sonda o mercado da região
python -m vagas_monitor classificar "título" # em que categoria um título cai, e por quê
python -m vagas_monitor publicar-secrets     # grava os secrets do .env no GitHub (usa o gh)
python -m vagas_monitor status | test-notify | check-ia | setup-telegram | render
python -m pytest -q                          # testes
python tools/leak_check.py                   # segredos e dados pessoais, antes de um push
```

`run` sai com código **2** e lista o que falta quando o `config.yaml` está incompleto, e com
código **1** quando um canal de notificação falha. Fonte com zero vagas aparece no topo do
relatório, no Telegram e no e-mail.

## Tecnologias mais pedidas

Cada rodada conta **em quantas vagas cada tecnologia aparece** (uma vez por vaga) e ranqueia pela
contagem, sem peso nem filtro de perfil. Sai no relatório, no painel e nas notificações. A lista
vive em `skills.yaml` (hoje voltada a tecnologia; para outra área, edite as entradas): um item é
uma tecnologia, e os termos dele são só grafias da mesma coisa. Mudou o arquivo?
`python -m vagas_monitor render` refaz o ranking da última rodada.

## Avaliação por IA (opcional)

Com uma chave, as melhores vagas novas recebem nota de 0 a 10 e um comentário, escritos a partir do
**seu** perfil. O Gemini gratuito às vezes responde 503; o monitor tenta de novo, usa um modelo de
reserva e, se não der, segue sem as notas. Custos, privacidade e limites em
[guia/07-ia-gratuita-e-custos.md](guia/07-ia-gratuita-e-custos.md).

## Limites, fontes e termos de uso

- **As fontes não são oficiais** e mudam sem aviso. A Gupy já trocou de endereço uma vez. Fonte com
  zero vagas é defeito a investigar, não um dia ruim: [guia 09](guia/09-solucao-de-problemas.md).
- **Cobertura por área.** As três fontes trazem bem escritório e tecnologia e mal vagas
  operacionais, de saúde e de comércio. O `calibrar --sondar` mostra o que existe na sua região.
- **Uso pessoal e de baixo volume.** Respeite os termos de cada site, não aumente a frequência nem
  contorne bloqueios: [guia 11](guia/11-limites-e-termos-de-uso.md).
- **Só Brasil.**

## Estrutura

```
vagas_monitor/   o motor (coleta, filtros, pontuação, relatório, notificações, init, calibrar, doctor)
areas/           17 packs de área (categorias prontas com exemplos que viram teste)
dados/           snapshot do IBGE: 5.571 municípios e as regiões imediatas
tests/           os testes (config_teste.yaml é a configuração usada por eles)
tools/           leak_check.py (segredos e dados pessoais), atualizar_ibge.py
guia/            guias passo a passo (01 a 11)
.claude/         comandos para o Claude Code (/personalizar, /calibrar, /diagnosticar)
config.yaml      a sua configuração (vem vazia de propósito)
```

## Contribuindo

Veja o [CONTRIBUTING](CONTRIBUTING.md) e o [ROADMAP](ROADMAP.md). As contribuições mais valiosas são
**consertar uma fonte que quebrou** e **validar os packs de uma área** que você conhece (todos fora
de TI estão em fase `beta`).

Quem mantém o modelo: [MANTENEDOR.md](MANTENEDOR.md).

Licença: [MIT](LICENSE).
