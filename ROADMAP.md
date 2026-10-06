# Roadmap

O que existe hoje e o que vem. Itens com `[x]` estão no `main`.

## Pronto

- [x] Motor genérico: região por IBGE, alvo por nível, zero-default, validação com mensagens
- [x] Coleta: LinkedIn, Indeed e Gupy; deduplicação; ranking de tecnologias
- [x] Avaliação por IA (Gemini ou Claude) com prompt derivado do perfil
- [x] Notificações por Telegram e e-mail; avisos de fonte vazia e de falha de envio
- [x] `classificar` e `tools/leak_check.py`
- [x] CI (testes em 3 sistemas, vazamento, lint), guias e `CLAUDE.md`

## Próximo (ordem de prioridade)

- [ ] **`init`**: configuração a partir do currículo, com anonimização local dos dados pessoais antes
      de qualquer IA, em três níveis (Claude Code, Gemini gratuito, manual sem IA)
- [ ] **`calibrar`**: sondagem do mercado na região (títulos reais e termos candidatos, com
      amostras para expor homônimos) e métricas de acerto contra vagas de referência
- [ ] **`doctor`**: valida config, perfil, tokens, SMTP, chave de IA e o alcance e o formato de cada
      fonte; avisa quando a sua versão está atrás do modelo
- [ ] **Packs de área** (`areas/*.yaml`): categorias prontas por área, com exemplos positivos e
      negativos que viram teste. Começam como `beta` até alguém da área validar
- [ ] `publicar-secrets` em Python (hoje: interface do GitHub ou `gh secret set`)
- [ ] Painel HTML como anexo do e-mail e do Telegram, para repositório privado
- [ ] Fallback para um segundo modelo do Gemini quando o principal estiver sobrecarregado
- [ ] `saude-fontes.yml`: teste diário contra as três fontes que abre uma issue quando uma mudar
- [ ] Outras fontes (a avaliar termos de uso de cada uma)

Quer ajudar com algum item? Abra uma issue antes de começar.
