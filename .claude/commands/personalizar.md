---
description: Configura o monitor para a pessoa (região, nível, categorias, perfil) entrevistando e validando com vagas reais
---

Configure o Radar de Vagas Laplace para a pessoa que está aqui. Leia o `CLAUDE.md` e o
`guia/04-personalizar.md` antes de começar e **siga o procedimento do CLAUDE.md**, pedindo
aprovação a cada etapa:

1. Entreviste (cargo ou área, nível, UF e cidade-base, remoto, formação, experiência, ferramentas,
   registros profissionais) e peça de 3 a 10 vagas que ela gostaria de receber e algumas que rejeita.
2. Escreva o `perfil.md` só com o que ela disse. **Não invente.** Se o repositório for público,
   oriente a usar o secret `PERFIL_MD`.
3. Preencha `regiao` e `alvo` no `config.yaml`.
4. Monte `termos_busca`, `categorias` (papéis alvo, adjacente e ponte), `senioridade`,
   `excluir_titulo` e `habilidades`.
5. Rode `python -m vagas_monitor run --force --dry-run --no-notify` e mostre o resultado.
6. Calibre com as vagas de referência usando `python -m vagas_monitor classificar "<título>"`.
7. Rode `python -m pytest -q` e `python tools/leak_check.py` e resuma o que ficou.

Regras: nunca peça nem imprima segredos; não envie o currículo a nenhuma IA externa sem avisar e
sem remover nome, CPF, telefone, e-mail e endereço; não faça push nem merge sem a pessoa pedir.

$ARGUMENTS
