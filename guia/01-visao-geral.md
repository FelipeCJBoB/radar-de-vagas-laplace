# Visão geral

O Radar de Vagas Laplace procura vagas por você. Você diz **onde** busca, **o que** busca e em
**que nível**; ele varre LinkedIn, Indeed e Gupy, descarta o que não serve, dá nota ao resto e
avisa por Telegram e e-mail. Roda sozinho na nuvem (GitHub Actions), de graça.

## O caminho mais curto

```bash
pip install -r requirements-dev.txt
python -m vagas_monitor init                    # pergunta região, nível e área; gera config.yaml e perfil.md
python -m vagas_monitor doctor                  # confere credenciais, fontes e config
python -m vagas_monitor run --force --dry-run --no-notify   # ensaio: confira reports/LATEST.md
python -m vagas_monitor calibrar                # mede o acerto contra vagas que você quer e não quer
python -m vagas_monitor publicar-secrets        # grava os secrets no GitHub (sem mostrar os valores)
```

Depois, em **Actions → Monitor de vagas → Run workflow**, a primeira rodada na nuvem.

## Como uma rodada funciona

```
termos de busca × (suas cidades no LinkedIn | seu estado no Indeed | seu estado na Gupy) + remotas
   │
   ▼  deduplica (id da fonte, depois título+empresa, depois tokens parecidos)
   ▼  escopo: está numa cidade sua, ou é remota e você aceita remoto?
   ▼  categoria: o título (ou 3 termos da descrição) casa com alguma categoria sua?
   ▼  nível: júnior, pleno ou sênior (detectado no título)
   ▼  nota 0 a 100, com os motivos à vista
   ▼  só as NOVAS vão para a notificação; o relatório mostra tudo da janela
   ▼  (opcional) uma IA lê o seu perfil e dá nota 0 a 10 e um comentário às melhores novas
```

## Vocabulário

| Termo | O que é |
|---|---|
| **região** | onde você busca: UFs, cidade-base e **alcance** (`cidade`, `regiao_imediata`, `estado` ou `lista`) |
| **região imediata** | a área de deslocamento diário do IBGE ao redor da sua cidade (centenas já mapeadas) |
| **categoria** | uma área de vaga que interessa, com termos de título e de descrição |
| **papel** | `alvo` (o que você quer), `adjacente` (vizinho que também serve) ou `ponte` (o que sua experiência sustenta, mas não é o desejo) |
| **pack** | uma categoria pronta para uma área (saúde, jurídico, logística...), em `areas/` |
| **homônimo** | palavra que em outra área significa outra coisa ("fiscal de loja" × fiscal tributário) |
| **referência** | títulos de vagas que você quer e que não quer, para **medir** se o monitor acerta |
| **recall / corte** | quantas das queridas ele captura / quantas das indesejadas ele descarta |

## Onde fica cada coisa

| Arquivo | Para quê |
|---|---|
| `config.yaml` | a sua configuração (o `init` escreve) |
| `perfil.md` ou secret `PERFIL_MD` | o seu perfil, lido pela avaliação por IA |
| `.env` | as suas credenciais (nunca vai para o git) |
| `areas/*.yaml` | os packs de área |
| `calibracao/referencia.yaml` | as suas vagas de referência (pessoal, fora do git) |
| `reports/`, `docs/`, `state/` | saída: relatórios, painel e a memória do que já foi visto |
| `.github/workflows/monitor.yml` | o agendamento na nuvem |

## Onde cada coisa roda

- **No seu computador:** `init`, `doctor`, `calibrar`, ensaios, testes. Nada disso notifica nem
  grava estado (exceto `init`, que grava o `config.yaml` e o `perfil.md`).
- **Na nuvem (GitHub Actions):** a rodada de verdade, todo dia às 08:00 de Brasília; o script só
  coleta quando passaram 5 dias da última. Commita o relatório e o estado no repositório.
- **Escolha um agendador só.** Não agende também no seu computador: os dois gravariam o mesmo
  estado e disputariam o `git push`.

## Próximos passos

1. [Contas e credenciais](02-contas-e-credenciais.md)
2. [Primeira rodada](03-primeira-rodada.md)
3. [Personalizar](04-personalizar.md) e [calibrar](05-calibrar.md)
4. [Privacidade](06-privacidade.md) antes de criar o repositório
