# Primeira rodada

Antes de colocar na nuvem, rode no seu computador e confira o resultado. Os comandos abaixo não
notificam e não gravam estado, então dá para repetir à vontade.

## 1. Confira o ambiente

```bash
python -m vagas_monitor doctor
```

Cada linha começa com `[ok]`, `[aviso]` ou `[ERRO]`, e as de erro dizem como corrigir. Com tudo
sem `[ERRO]`, siga. Aviso de Telegram, e-mail ou IA desligados é normal se você ainda não os
configurou. Sem rede: `doctor --offline`.

## 2. Ensaio

```bash
python -m vagas_monitor run --force --dry-run --no-notify
```

- A **primeira** rodada usa uma janela de 30 dias para popular o relatório; as seguintes usam 7.
- Leva de 5 a 15 minutos (o LinkedIn busca a descrição de cada vaga, uma a uma, com pausas).
- Para um ensaio rápido, só com a Gupy: acrescente `--skip indeed --skip linkedin` (segundos).
- Se faltar algo no `config.yaml`, ele para e lista as pendências (código de saída 2).

## 3. Leia o relatório

Abra `reports/LATEST.md` (e `docs/index.html` no navegador). Na ordem:

1. **Linha "Problemas nesta rodada".** Fonte com zero vagas, IA indisponível ou canal que falhou
   aparece aqui. Fonte vazia quase sempre é a API que mudou ([guia 09](09-solucao-de-problemas.md)).
2. **Por categoria e por local.** Bate com o que você esperava? Uma categoria com 100 vagas e outra
   com 2 costuma indicar um termo largo demais ou estreito demais.
3. **Os destaques.** Para cada um, pergunte: é uma vaga que eu quero? Se não for, descubra o termo
   que a trouxe com `classificar` e conserte ([guia 05](05-calibrar.md)).
4. **O ranking de tecnologias** (se a sua área as tem): quais aparecem mais nas vagas da região.

Poucas vagas no total? Veja `guia/05`, seção "Quando vêm poucas vagas".

## 4. Calibre

```bash
python -m vagas_monitor calibrar            # mede contra as vagas de referência
python -m vagas_monitor calibrar --sondar   # mostra o que o mercado da região tem e o config não pega
```

Repita ensaio e calibração até as vagas que você quer aparecerem e as que não servem sumirem
([guia 05](05-calibrar.md)).

## 5. Coloque na nuvem

1. Crie o repositório a partir do modelo (**privado**, veja [privacidade](06-privacidade.md)) e
   envie a sua pasta.
2. `python -m vagas_monitor publicar-secrets` grava os secrets do `.env` no GitHub sem mostrá-los
   (precisa do `gh` autenticado). Para repositório público, acrescente `--perfil`.
3. Em **Settings → Actions → General → Workflow permissions**, marque *Read and write*.
4. **Actions → Monitor de vagas → Run workflow**, com `force` marcado.
5. Confira o Telegram, o e-mail e o commit "relatório AAAA-MM-DD" no repositório.

Se algo falhar, o job fica vermelho e o motivo está no topo do relatório e no log.

## O que esperar depois

- O cron roda todo dia às 08:00 (Brasília) e coleta a cada 5 dias (`intervalo_dias`).
- Cada notificação traz **só as vagas novas**; o relatório completo mostra tudo da janela.
- Uma vaga que sai e volta em até 30 dias não é anunciada de novo (`estado.key_ttl_days`).
