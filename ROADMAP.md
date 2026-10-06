# Roadmap

O que existe hoje e o que vem. Itens com `[x]` estão no `main`.

## Pronto

- [x] Motor genérico: região por IBGE, alvo por nível, zero-default, validação com mensagens
- [x] Coleta: LinkedIn, Indeed e Gupy; deduplicação; ranking de tecnologias
- [x] Avaliação por IA (Gemini ou Claude) com prompt derivado do perfil e modelos de reserva
- [x] Notificações por Telegram e e-mail; avisos de fonte vazia e de falha de envio; painel como anexo
- [x] `init` (IA, manual), com anonimização local do currículo
- [x] `calibrar` (recall e corte; sondagem do mercado), `classificar` e `doctor`
- [x] 17 packs de área, com exemplos que viram teste e exclusão de homônimos por categoria
- [x] `publicar-secrets`, `tools/leak_check.py`
- [x] CI em 3 sistemas, testes de contrato ao vivo, `saude-fontes`, guias 01 a 11, `CLAUDE.md`

## Próximo (ordem de prioridade)

- [ ] **Validar os packs beta** com quem trabalha em cada área. É a melhor contribuição possível:
      todos fora de TI nasceram de IA e não foram revisados por especialista
- [ ] **`novo-pack`**: gerar um pack para uma ocupação fora do catálogo a partir de amostragem do
      mercado, exigindo exemplos positivos e negativos antes de aceitar (hoje o `init` com IA já
      cria categorias extras, mas sem os exemplos que viram teste)
- [ ] **Referência a partir das candidaturas**: importar do LinkedIn/Gupy as vagas em que você já se
      candidatou, em vez de digitar os títulos
- [ ] **Feedback contínuo**: marcar vagas como boas ou ruins nas notificações e propor termos e
      exclusões novos com base nisso
- [ ] **`doctor` com chamada real para as três fontes**, incluindo o Indeed (hoje só Gupy e LinkedIn)
- [ ] **Configuração em camadas** (`config.default.yaml` + o seu), para receber melhorias dos packs
      sem conflito de merge ([guia 08](guia/08-atualizar-do-modelo.md))
- [ ] **Skills por área** (`skills.yaml`): o ranking de tecnologias hoje é voltado a TI
- [ ] Outras fontes (a avaliar o termo de uso de cada uma): SINE, InfoJobs, Vagas.com, Catho
- [ ] Outros países

Quer ajudar com algum item? Abra uma issue antes de começar.
