# Para quem mantém o modelo

Este arquivo é para quem cuida do **repositório-modelo** (o que as pessoas copiam com *Use this
template*). Quem só usa o monitor não precisa dele.

## Estado das configurações

| Item | Como | Observação |
|---|---|---|
| Template repository | `gh repo edit DONO/REPO --template` | feito: é o que habilita o botão *Use this template* |
| Variável `MONITOR_ATIVO=false` | `gh variable set MONITOR_ATIVO --body false` | **obrigatória**: sem ela o cron do `monitor.yml` rodaria no próprio modelo. Variáveis não são copiadas para quem usa o modelo, então as cópias rodam sozinhas |
| Tópicos e descrição | `gh repo edit --add-topic ...` | feito |
| Secret scanning e push protection | só em repositório **público** (no plano gratuito) | veja abaixo |
| Proteção do `main` | só em repositório **público** (no plano gratuito) | veja abaixo |

## Ao tornar o repositório público

1. Rode `python tools/leak_check.py` (com a sua lista em `tools/leak_denylist.local.txt`) e confira
   `git log -p` por dados pessoais. Tornar público expõe **todo o histórico**.
2. Torne público:

   ```bash
   gh repo edit DONO/REPO --visibility public --accept-visibility-change-consequences
   ```

3. Ative a varredura de segredos e a proteção no push:

   ```bash
   gh api -X PATCH repos/DONO/REPO -f "security_and_analysis[secret_scanning][status]=enabled" -f "security_and_analysis[secret_scanning_push_protection][status]=enabled"
   ```

4. Proteja o `main`, exigindo o CI (o nome de cada verificação é o do job em `ci.yml`):

   ```bash
   gh api -X PUT repos/DONO/REPO/branches/main/protection --input protecao.json
   ```

   com `protecao.json`:

   ```json
   {
     "required_status_checks": {
       "strict": false,
       "contexts": ["pytest (ubuntu-latest)", "pytest (windows-latest)", "pytest (macos-latest)",
                    "segredos e dados pessoais", "lint"]
     },
     "enforce_admins": false,
     "required_pull_request_reviews": null,
     "restrictions": null
   }
   ```

5. Em **Settings → Code security**, ative também o Dependabot alerts.

## Publicar uma versão

O `doctor` das cópias compara a versão local com a **última release** daqui. A cada correção
relevante (principalmente de fonte):

1. Atualize `__version__` em `vagas_monitor/__init__.py` e o `CHANGELOG.md` (diga o que mudou nas
   fontes).
2. `git tag vX.Y.Z && git push --tags`, e crie a release com as notas do `CHANGELOG`:

   ```bash
   gh release create vX.Y.Z --title "vX.Y.Z" --notes-file notas.md
   ```

## Quando uma fonte quebrar

O workflow `saude-fontes.yml` roda todo dia **só aqui** (onde existe `MONITOR_ATIVO=false`) e abre uma
issue `fonte-quebrada` quando um teste de contrato falha. Conserte o coletor
([guia 10](guia/10-adicionar-fonte.md)), acrescente um teste, publique uma versão nova e feche a
issue (ela também fecha sozinha quando os testes voltam a passar).

## Verificações antes de cada push

```bash
python -m pytest -q
ruff check vagas_monitor tools tests
python tools/leak_check.py
```

O CI repete as três em Windows, Linux e macOS.
