# Contribuindo

Obrigado por querer melhorar o Radar de Vagas Laplace. As contribuições mais valiosas:

1. **Consertar uma fonte que quebrou** (Gupy, Indeed ou LinkedIn mudam sem aviso). Veja
   [guia/09](guia/09-solucao-de-problemas.md) e [guia/10](guia/10-adicionar-fonte.md).
2. **Validar categorias para uma área** que você conhece (saúde, direito, indústria, comércio...).
   Conhecimento de quem trabalha na área vale mais que qualquer IA.
3. **Testes, documentação e portabilidade** (Windows, Linux, macOS).

## Ambiente

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1     Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
ruff check vagas_monitor tools tests
python tools/leak_check.py
```

## Regras

- **Fim de linha LF e UTF-8.** O `.gitattributes` cuida disso; não converta arquivos.
- **Nada de dado pessoal ou segredo** em código, testes, exemplos, issues ou PRs. Rode
  `python tools/leak_check.py` antes de cada push.
- **Nada de valor fixo de região, área ou pessoa** no código. Há testes que varrem por isso
  (`tests/test_genericidade.py`).
- **Todo defeito corrigido ganha um teste** que falharia sem a correção.
- Testes não usam rede. Use respostas gravadas.
- Mantenha o PR pequeno e explique o **porquê**, não só o quê.

## Pull request

1. Abra uma issue se a mudança for grande, antes de escrever.
2. Faça o PR contra `main` com a descrição do problema, da mudança e de como você verificou.
3. O CI roda os testes em Windows, Linux e macOS, o `leak_check` e o `ruff`. Precisa passar.

## Commits e segurança

Use o e-mail `noreply` do GitHub nos commits. Veja o [SECURITY](SECURITY.md) para reportar
vulnerabilidades.
