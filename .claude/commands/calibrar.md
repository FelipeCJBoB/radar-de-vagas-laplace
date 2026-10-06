---
description: Calibra as categorias com vagas reais: acha o que faltou e o que sobrou e explica o porquê
---

Calibre o `config.yaml` com vagas reais, seguindo a seção "Calibrar com vagas reais" do
`guia/04-personalizar.md`.

1. Peça as vagas de referência: as que a pessoa **quer** receber e as que **não** quer (títulos).
2. Rode o ensaio: `python -m vagas_monitor run --force --dry-run --no-notify` e leia o
   `reports/LATEST.md`.
3. Para cada vaga de referência e para cada falso positivo do relatório, rode
   `python -m vagas_monitor classificar "<título>"` e diga qual termo decidiu (ou faltou).
4. Proponha mudanças no `config.yaml` (termo mais específico, `excluir_titulo` para homônimo, termo
   de busca novo) e **mostre o antes e o depois** antes de aplicar.
5. Repita até as vagas queridas aparecerem e as indesejadas sumirem. Informe, no fim, quantas das
   queridas entraram e quantas das rejeitadas foram cortadas.

$ARGUMENTS
