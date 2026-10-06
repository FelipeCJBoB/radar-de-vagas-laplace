# Segurança

## Reportar uma vulnerabilidade

Não abra uma issue pública. Use **Security → Report a vulnerability** neste repositório
(relatório privado) e descreva o que encontrou e como reproduzir. Não inclua segredos reais.

## O que nunca deve ir para o repositório

- `.env`, tokens (Telegram, GitHub), senhas de app, chaves de API
- seu currículo ou `perfil.md`, se o repositório for **público** (use o secret `PERFIL_MD`)
- relatórios e painéis, se o repositório for público e o conteúdo expuser o seu perfil

Veja [guia/06-privacidade.md](guia/06-privacidade.md). Rode `python tools/leak_check.py` antes de
cada push e ative **secret scanning** e **push protection** nas configurações do repositório.

## Se um segredo vazou

Revogue-o imediatamente e gere outro. Limpar o histórico do git não desfaz o vazamento.

## Escopo do projeto

O monitor lê páginas e APIs públicas de vagas. Ele não faz login, não envia candidaturas e não
guarda dados de terceiros além dos anúncios. Os segredos que ele usa ficam nos *secrets* do
GitHub Actions da sua cópia.
