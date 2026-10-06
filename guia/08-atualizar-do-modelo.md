# Atualizar a partir do modelo

As fontes de vagas são APIs não oficiais e mudam sem aviso. Quando uma muda, a correção sai no
repositório do modelo. A sua cópia **não se atualiza sozinha** (um repositório criado por
"Use this template" não guarda vínculo com o original), então você traz a correção quando precisar.

## Como saber que há versão nova

- `python -m vagas_monitor doctor` compara a sua versão com a última *release* do modelo e avisa.
  Para isso, preencha em `config.yaml`:

  ```yaml
  modelo:
    repositorio: usuario/radar-de-vagas-laplace
  ```

- Ou acompanhe as *releases* e as issues `fonte-quebrada` do repositório do modelo (use **Watch →
  Custom → Releases**).
- Uma fonte que vem com **zero vagas** aparece no topo do relatório e nas notificações: é o sinal
  de que o endereço ou o formato mudou.

## Trazer as correções

Uma vez, adicione o modelo como remoto:

```bash
git remote add modelo https://github.com/usuario/radar-de-vagas-laplace.git
```

Cada vez que quiser atualizar:

```bash
git fetch modelo
git merge modelo/main --allow-unrelated-histories    # só a primeira vez; depois: git merge modelo/main
```

A primeira mesclagem acusa conflitos em arquivos que existem nos dois lados. **A regra:** o que é
seu fica com você, o que é do motor vem do modelo.

| Mantenha o SEU | Aceite o do MODELO |
|---|---|
| `config.yaml`, `perfil.md`, `.env` | `vagas_monitor/`, `tests/`, `tools/` |
| `state/`, `reports/`, `docs/` | `areas/`, `dados/`, `guia/` |
| `calibracao/referencia.yaml` | `.github/workflows/`, `requirements*.txt`, `pyproject.toml` |

```bash
# em conflito, para manter a sua versão (ours = a sua branch):
git checkout --ours config.yaml perfil.md state reports docs

# para aceitar a do modelo (theirs = a que está sendo mesclada):
git checkout --theirs vagas_monitor tests tools areas dados guia .github requirements.txt requirements-dev.txt pyproject.toml

git add -A
git commit
```

Depois:

```bash
python -m pytest -q
python -m vagas_monitor doctor
python -m vagas_monitor run --force --dry-run --no-notify
```

## Seu `config.yaml` é uma cópia dos packs

O `init` **copia** os termos dos packs para o seu `config.yaml`. Se o modelo melhorar um pack, a
melhoria **não** chega ao seu arquivo sozinha. Para aproveitá-la, olhe o que mudou em `areas/` no
`CHANGELOG` e copie os termos que interessam, ou rode `init` de novo (ele guarda a versão anterior
em `config.yaml.bak`). Prefira conferir com `calibrar` depois.

## Quem tem o repositório como fork

Se você criou a cópia por **fork** (e não por template), `Sync fork` no GitHub traz as correções.
Lembre que fork de repositório público é público: leia o [guia de privacidade](06-privacidade.md).

## Contribuir de volta

Consertou uma fonte ou validou um pack? Abra um PR no modelo ([CONTRIBUTING](../CONTRIBUTING.md)).
Todo mundo que usa o modelo recebe a correção.
