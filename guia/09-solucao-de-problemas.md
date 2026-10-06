# Solução de problemas

**Comece pelo diagnóstico**, que confere config, perfil, Telegram, e-mail, IA, fontes e estado e diz como
corrigir cada coisa:

```bash
python -m vagas_monitor doctor
```

Depois, se precisar, procure o sintoma na tabela. Os cinco primeiros são os que mais aparecem.

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `run` imprime "config.yaml tem N pendência(s)" e sai com código 2 | Campo obrigatório vazio (`regiao.estados`, `regiao.base`, `alvo.nivel`, `termos_busca`, `categorias`) | Preencha seguindo o [guia 04](04-personalizar.md) |
| **Uma fonte vem com zero vagas** (aviso no topo do relatório) | A API mudou. A Gupy já trocou de endereço uma vez e deu 404 | Veja "Fonte com zero vagas" abaixo |
| Telegram não chega; o log mostra `telegram 401` | Token revogado ou errado, ou o secret do GitHub está com o token antigo | Gere outro no @BotFather e atualize o `.env` **e** o secret ([guia 02](02-contas-e-credenciais.md)) |
| E-mail não chega; log `email falhou` | `SMTP_PASSWORD` vazio, com espaços, ou verificação em 2 etapas desligada | Gere a senha de app, cole **sem espaços**, confira o secret |
| A rodada fica vermelha no Actions | Uma notificação falhou (código de saída 1), ou o config está incompleto (2) | Leia o log do passo "Executar rodada"; o relatório mostra o motivo no topo |
| Vagas de outro estado | `regiao.estados` errado ou `alcance: estado` | Confira a seção `regiao` |
| Vagas que não servem entram | Termo largo demais ou homônimo | [Calibrar](04-personalizar.md#calibrar-com-vagas-reais): `classificar` e `excluir_titulo` |
| Vagas que você queria não entram | Falta o termo do título ou um termo de busca | Idem; acrescente o título que a empresa usou |
| O ranking parece invertido | `alvo.nivel` errado | Confira o nível; ele define quem leva +25 |
| Nenhuma nota de IA; relatório diz "Gemini: modelo sobrecarregado (503)" | Instabilidade do nível gratuito | O monitor tenta de novo, usa `modelos_reserva` e segue sem notas se não der. Rode `check-ia` mais tarde ([guia 07](07-ia-gratuita-e-custos.md)) |
| LinkedIn devolve 429 | IP de nuvem limitado | O coletor espera e tenta de novo; a rodada segue com as outras fontes |
| O workflow não roda | Cron só dispara no branch padrão; ou o repositório ficou 60 dias sem atividade (só repositório público) | Rode manualmente em Actions → Run workflow |
| O passo "Publicar relatórios" falha ao dar `git push` | Workflow permissions sem escrita | Settings → Actions → General → *Read and write permissions* |
| Acentos viram `?` no console do Windows | Codificação do terminal | O monitor já força UTF-8; use `chcp 65001` ou o Windows Terminal |
| Diff gigante em arquivo que você mal tocou | Fim de linha CRLF vs LF | O `.gitattributes` força LF; rode `git add --renormalize .` |
| `ModuleNotFoundError` | Ambiente virtual não ativado | Ative o `.venv` e rode `pip install -r requirements-dev.txt` |
| Cópia criada pelo modelo não roda o cron | Variável `MONITOR_ATIVO=false` copiada por engano | Apague a variável em Settings → Secrets and variables → Actions → Variables |

## Fonte com zero vagas

Gupy, Indeed e LinkedIn são APIs **não oficiais**. Quando uma delas muda, o coletor volta vazio.

1. Confirme que é a fonte e não o seu config: rode `python -m vagas_monitor run --force --dry-run
   --no-notify --skip indeed --skip linkedin` e olhe se a Gupy traz vagas.
2. Abra o site da fonte no navegador e repita a mesma busca. Se o site mostra vagas, a API mudou.
3. No navegador, abra as ferramentas do desenvolvedor, aba **Rede (Network)**, refaça a busca e
   procure a chamada que devolve as vagas em JSON. Compare o endereço e os parâmetros com
   `vagas_monitor/sources/<fonte>.py`.
4. Atualize o endereço e o mapeamento dos campos no coletor, rode `python -m pytest -q` e abra um
   PR no repositório do modelo para todos receberem a correção. O
   [guia 10](10-adicionar-fonte.md) descreve o contrato de uma fonte.

## Notas e dicas

- **Perfil sem a avaliação por IA**: o `doctor` avisa se o `perfil.md` ainda é o modelo, com campos
  entre colchetes.
- **Painel em repositório privado**: sem GitHub Pages, o painel HTML vai anexado no e-mail e no
  Telegram (`notificacoes.anexar_painel`).

## Pedir ajuda

Abra uma issue no repositório do modelo com: o sintoma, o trecho do log (**sem segredos**), a
saída de `python -m vagas_monitor status` e o seu sistema operacional.
