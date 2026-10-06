# Privacidade

O monitor guarda no repositório o seu **perfil**, as vagas que você viu e os relatórios. Decida
antes de criar a sua cópia o que isso significa para você.

## Repositório privado (recomendado)

- O `perfil.md` pode ficar no repositório sem exposição.
- O GitHub Actions é gratuito para repositório privado dentro de 2.000 minutos por mês. O monitor
  usa cerca de 100 (6 rodadas de ~14 min mais ~24 verificações de ~30 s).
- **O painel público (GitHub Pages) não existe em repositório privado no plano gratuito.** Em
  troca, o relatório em Markdown é commitado e o e-mail leva o relatório em anexo. Deixe
  `relatorio.url_publica` vazio para o link "Relatório completo" não aparecer quebrado.

## Repositório público

Só se você quer o painel online. Cuidado com o que ele revela:

- **`perfil.md`**: não commite. Guarde o texto no secret **`PERFIL_MD`** (a variável de
  ambiente tem precedência sobre o arquivo). Apague o `perfil.md` do repositório.
- **Relatórios e painel**: mostram as vagas **e os comentários da IA sobre você** ("destoando do
  seu nível", "exige experiência que você não tem"). Isso revela o seu nível e o seu perfil mesmo
  sem o currículo. Se isso incomoda, use repositório privado.
- **Histórico do git**: tudo o que já foi commitado continua visível, mesmo depois de apagar o
  arquivo. Para limpar de verdade é preciso reescrever o histórico (`git filter-repo`). Decida
  **antes** do primeiro commit.
- **Metadados dos commits** mostram o nome e o e-mail do autor. Use o e-mail `noreply` do
  GitHub (Settings → Emails → *Keep my email addresses private*).

## O que vai para as IAs

- A avaliação por IA envia a cada chamada: o anúncio da vaga e o **seu perfil**.
- No Gemini gratuito o Google **pode usar o conteúdo para treinar**. No Claude (API), não.
- Escreva o perfil pensando nisso: formação, experiência, ferramentas e objetivo bastam.
  **Não coloque** telefone, endereço, CPF, e-mail, nem nomes de pessoas.

## Antes de cada push: `tools/leak_check.py`

```bash
python tools/leak_check.py
```

Procura chaves de API, tokens, CPF, telefones e e-mails no repositório inteiro. Para procurar
também os **seus** dados (seu nome, seu empregador, sua faculdade), crie o arquivo
`tools/leak_denylist.local.txt` com um termo por linha. Esse arquivo é ignorado pelo git de
propósito: uma lista dos seus termos dentro do repositório seria, ela mesma, o vazamento.

## E se um segredo vazou?

1. **Revogue** o segredo agora (BotFather, página de senhas de app, console da chave).
2. Gere outro e atualize o `.env` e o secret do GitHub.
3. Só depois pense em limpar o histórico. Quem já viu o segredo não esquece, então o passo 1 é o que
   resolve.
