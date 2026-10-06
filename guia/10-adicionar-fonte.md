# Adicionar ou consertar uma fonte

Cada fonte é um arquivo em `vagas_monitor/sources/` com uma função `collect` que devolve uma lista
de `Job` (veja `vagas_monitor/models.py`). O resto do monitor não sabe de onde a vaga veio.

## Contrato

```python
def collect(terms: list[str], ..., lookback_days: int, include_remote: bool = True, ...) -> list[Job]:
```

- Receba o que precisa da região **por parâmetro** (`estados`, `locais`), nunca de um valor
  fixo. O `pipeline.collect_all` monta e passa esses valores. Há um teste que varre o código por
  nome de estado e cidade fixos.
- Devolva só vagas **dentro da janela** (`lookback_days`).
- Preencha, quando a fonte tiver: `title`, `company`, `url`, `city`, `state`, `location`,
  `workplace` (`remote`, `hybrid`, `onsite`), `date_posted` (`AAAA-MM-DD`), `description`
  (texto, sem HTML) e `external_id` (identidade exata da vaga na fonte, ex.: `gupy:123`).
- **Nunca levante exceção por causa de uma resposta ruim**: registre um `warning` e devolva o que
  conseguiu. O pipeline já trata exceção, mas devolver vazio em silêncio é o pior caso.
- Se a fonte devolver zero vagas, o pipeline avisa no relatório, no Telegram e no e-mail.

## Passos

1. Crie `vagas_monitor/sources/minha_fonte.py` com `collect`.
2. Registre no `collect_all` de `vagas_monitor/pipeline.py` com `run_source("minha_fonte", ...)`.
3. Acrescente a fonte em `SOURCE_PT` (`report.py`), em `FONTES` (`notify/__init__.py`) e na lista
   de `--skip` (`__main__.py`).
4. Acrescente a seção `fontes.minha_fonte.ativo` no `config.yaml`.
5. Escreva testes em `tests/` com **respostas de exemplo gravadas** (sem rede). Veja
   `tests/test_gupy.py`.
6. Rode `python -m pytest -q` e `ruff check vagas_monitor tools tests`.

## Antes de propor uma fonte nova

- **Termos de uso e robots.txt.** Raspar um site que proíbe é problema seu e do projeto. Prefira
  APIs públicas e documentadas.
- **Estabilidade.** Uma API interna de um site muda sem aviso. Explique no PR como você descobriu a
  chamada, para o próximo conseguir refazer.
- **Volume.** O monitor roda a cada poucos dias; não aumente a pressão sobre o servidor.
