# Changelog

## 0.1.0 (2026-10-06)

Primeira versão do modelo, derivada de um monitor em produção desde 09/2026.

**Configuração**
- **Zero-default:** região, nível e categorias vêm vazios; `run` lista as pendências e sai com
  código 2.
- **`init`:** gera `config.yaml`, `perfil.md` e a referência de calibração por três caminhos (IA a
  partir do currículo, manual com o catálogo de áreas, ou o Claude Code com `/personalizar`), todos
  validados da mesma forma. O currículo é **anonimizado localmente** e só vai à IA depois de você
  aprovar o texto.
- **17 packs de área** (`areas/`): 4 de TI, validados em produção, e 13 de outras áreas em fase
  `beta` (administrativo, contábil, logística, vendas, marketing, RH, indústria, construção, saúde,
  educação, jurídico, atendimento e segurança do trabalho). Os exemplos de cada pack viram teste.
- **Região por IBGE:** qualquer UF, cidade-base e alcance (`cidade`, `regiao_imediata`, `estado`,
  `lista`); vários estados; só remoto.
- **Pontuação por nível-alvo:** o degrau do seu nível soma +25; quem busca sênior não recebe o
  ranking de quem busca estágio. Remoto pontua só se `regiao.remoto: preferir`.
- **Prompt da avaliação por IA** montado a partir das categorias, do nível e do idioma, sem perfil
  fixo no código; `PERFIL_MD` com precedência sobre o `perfil.md`.
- **Exclusão de homônimos por categoria** (`categorias.<x>.excluir_titulo`): a exclusão global
  matava a vaga legítima de outra categoria (achado do teste cruzado dos packs).

**Calibração e diagnóstico**
- **`calibrar`:** recall das vagas queridas e corte das indesejadas contra um conjunto de
  referência (offline), e `--sondar` para ver o que o mercado da região tem, o que cada termo
  captura (homônimos aparecem) e que vocabulário falta.
- **`classificar`:** explica por que um título cai (ou não) numa categoria.
- **`doctor`:** confere config, perfil, Telegram (401), e-mail (senha de app), IA, o formato da
  resposta da Gupy e do LinkedIn, o estado e se há versão nova do modelo.

**Fontes e entrega**
- **Gupy** no endpoint novo do portal (`portal.gupy.io/api/job-search/jobs`); estado e locais
  recebidos por parâmetro nas três fontes.
- **Falhas visíveis:** fonte com zero vagas e notificação que falha viram aviso no relatório, no
  Telegram e no e-mail; a rodada sai com erro.
- **Painel como anexo** no e-mail e no Telegram quando não há link público (repositório privado).
- **Modelos de reserva do Gemini** (`avaliacao.gemini.modelos_reserva`) contra o 503 do nível
  gratuito.
- **`publicar-secrets`:** grava o `.env` nos secrets do GitHub pela entrada padrão do `gh`, sem
  mostrar nenhum valor.

**Projeto**
- `tools/leak_check.py` (segredos e dados pessoais; a lista de bloqueio pessoal fica fora do git).
- CI em Windows, Linux e macOS; testes de contrato ao vivo das fontes e workflow `saude-fontes`
  (só no repositório-modelo) que abre uma issue quando uma fonte muda.
- `.gitattributes` com LF, UTF-8 forçado no console, `.devcontainer`, guias 01 a 11, `CLAUDE.md` e
  os comandos `/personalizar`, `/calibrar` e `/diagnosticar`.
- **Teste corrigido:** um teste de estado dependia da data de hoje e quebrava com o tempo.
