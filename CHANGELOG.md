# Changelog

## 0.1.0 (2026-10-06)

Primeira versão do modelo, derivada de um monitor em produção desde 09/2026.

- **Zero-default:** região, nível e categorias vêm vazios; `run` lista as pendências e sai com
  código 2.
- **Região por IBGE:** qualquer UF, cidade-base e alcance (`cidade`, `regiao_imediata`, `estado`,
  `lista`); vários estados; só remoto.
- **Pontuação por nível-alvo:** o degrau do seu nível soma +25; quem busca sênior não recebe o
  ranking de quem busca estágio.
- **Prompt da avaliação por IA** montado a partir das categorias, do nível e do idioma, sem
  perfil fixo no código; `PERFIL_MD` com precedência sobre o `perfil.md`.
- **Fontes:** Gupy no endpoint novo do portal (`portal.gupy.io/api/job-search/jobs`); estado e
  locais recebidos por parâmetro nas três fontes.
- **Falhas visíveis:** fonte com zero vagas e notificação que falha viram aviso no relatório, no
  Telegram e no e-mail; a rodada sai com erro.
- **Ferramentas:** `classificar` (explica por que um título cai numa categoria) e
  `tools/leak_check.py` (segredos e dados pessoais).
- **Multiplataforma:** `.gitattributes` com LF, UTF-8 forçado no console, CI em Windows, Linux e
  macOS.
- **Teste corrigido:** um teste de estado dependia da data de hoje e quebrava com o tempo.
