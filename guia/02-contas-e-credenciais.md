# Contas e credenciais

Faça tudo isto **antes** de configurar o monitor. Leva cerca de uma hora e não precisa de
nenhuma IA paga. Todos os valores vão no arquivo `.env` (que o git ignora) e depois nos
**secrets** do GitHub.

> **Regra de ouro:** nunca cole um token, senha ou chave numa conversa (com pessoa, com IA ou num
> chat de suporte) nem num commit. Se acontecer, revogue e gere outro.

## 1. Telegram (recomendado)

1. No Telegram, abra o **@BotFather** e envie `/newbot`. Escolha um nome e um usuário que termine
   em `bot`. Ele devolve um **token** (algo como `1234567890:AA...`). Guarde em
   `TELEGRAM_BOT_TOKEN` no `.env`.
2. Abra a conversa com o **seu** bot e mande qualquer mensagem. Sem isso o bot não tem como achar
   você.
3. Rode `python -m vagas_monitor setup-telegram`. Ele descobre o seu `chat_id`, grava em
   `TELEGRAM_CHAT_ID` no `.env` e manda uma mensagem de teste.

**Se der erro 401 (Unauthorized):** o token está errado ou foi revogado. No @BotFather use
`/mybots`, escolha o bot, *API Token* e, se precisar, *Revoke current token* para gerar outro.
Depois atualize o `.env` **e** o secret do GitHub. É a falha mais comum depois de uma
troca de token: o `.env` local funciona e o secret da nuvem continua com o antigo.

## 2. E-mail pelo Gmail (opcional)

O monitor envia pelo SMTP do Gmail usando uma **senha de app**, que não é a senha da sua conta.

1. A **verificação em duas etapas** precisa estar **ativa**. Confira em
   <https://myaccount.google.com/signinoptions/twosv>. Na página, o botão deve dizer *Desativar*.
   Se disser **Ativar a verificação em duas etapas**, ela está desligada: clique e conclua. Ter
   segundas etapas cadastradas (celular, chave de acesso) não basta; é preciso ligar.
2. Abra <https://myaccount.google.com/apppasswords>, dê um nome (ex.: `radar-de-vagas`) e crie.
3. Copie os 16 caracteres **sem os espaços** para `SMTP_PASSWORD`. O Google mostra com espaços de
   4 em 4; o monitor usa o valor exatamente como está.
4. Preencha `SMTP_USER` (o seu Gmail) e `EMAIL_TO` (para onde enviar, pode ser o mesmo).

**Se a tela de senhas de app disser "a configuração não está disponível para sua conta":**
(a) a verificação em duas etapas está desligada (passo 1); (b) a conta é de trabalho ou escola e
o administrador bloqueou; (c) a Proteção Avançada do Google está ativa. Nesses casos, desista do
e-mail e use só o Telegram: em `config.yaml`, `notificacoes.email.ativo: false`.

Confira com `python -m vagas_monitor test-notify`.

## 3. Chave de IA (opcional)

A avaliação por IA dá uma nota e um comentário por vaga. Sem chave, o monitor funciona do mesmo
jeito, só sem as notas.

- **Gemini (gratuito):** <https://aistudio.google.com/apikey> → `GEMINI_API_KEY`. No nível
  gratuito o Google **pode usar o texto enviado para treinar**. O que trafega são anúncios de vaga
  (públicos) e o seu `perfil.md`; por isso evite colocar telefone, endereço e CPF nele.
- **Claude (pago):** <https://console.anthropic.com> → `ANTHROPIC_API_KEY`. Não usa para treinar.
- Uma **assinatura** (Gemini Pro, Claude.ai) não inclui chave de API.

Valide com `python -m vagas_monitor check-ia`. Se o Gemini devolver 503 ("modelo sobrecarregado"),
é do lado dele; o monitor tenta de novo e segue sem as notas se não der.

## 4. GitHub: secrets e permissões

No seu repositório, **Settings → Secrets and variables → Actions → New repository secret**.
Crie, com os mesmos valores do `.env`:

| Secret | Obrigatório | Observação |
|---|---|---|
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | para Telegram | |
| `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_TO` | para e-mail | `SMTP_PASSWORD` sem espaços |
| `GEMINI_API_KEY` ou `ANTHROPIC_API_KEY` | para a nota por IA | |
| `PERFIL_MD` | se o repositório for público | o texto do seu perfil (veja [privacidade](06-privacidade.md)) |

Depois, em **Settings → Actions → General → Workflow permissions**, marque **Read and write
permissions**. O monitor commita os relatórios e o estado no repositório; sem isso o passo final
falha.

Pela linha de comando, com o [GitHub CLI](https://cli.github.com) (`winget install GitHub.cli`
no Windows, `brew install gh` no macOS, `sudo apt install gh` no Debian/Ubuntu), que pede o valor
sem mostrá-lo:

```bash
gh auth login
gh secret set TELEGRAM_BOT_TOKEN
gh secret set SMTP_PASSWORD
```

Quem usa a interface do GitHub não precisa do `gh`.

## Checklist

- [ ] Bot criado, `setup-telegram` mandou a mensagem de teste
- [ ] (opcional) Verificação em duas etapas **ligada**, senha de app gerada, `test-notify` ok
- [ ] (opcional) Chave de IA, `check-ia` ok
- [ ] Secrets criados no GitHub, com os valores **atuais**
- [ ] Workflow permissions em *Read and write*
