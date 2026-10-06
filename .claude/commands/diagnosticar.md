---
description: Diagnostica por que o monitor não roda, não notifica ou não traz vagas
---

Diagnostique o problema usando o `guia/09-solucao-de-problemas.md`. Colete, nesta ordem, **sem
imprimir segredos**:

1. `python -m vagas_monitor status`
2. `python -m vagas_monitor run --force --dry-run --no-notify` (mostra pendências do config e
   fontes com zero vagas)
3. `python -m vagas_monitor test-notify` e `python -m vagas_monitor check-ia`, se o problema for de
   notificação ou de nota
4. Se for na nuvem, o log do último run no GitHub Actions (peça à pessoa o trecho, ou use o `gh` se
   ela já estiver autenticado)

Traduza cada falha em uma ação concreta e aponte a linha da tabela do guia 09. Não revele nem peça
tokens, senhas ou chaves; se algum precisar ser trocado, diga como e deixe a pessoa fazer.

$ARGUMENTS
