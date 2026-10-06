---
description: Configura o monitor para a pessoa (região, nível, áreas, perfil) entrevistando e calibrando com vagas reais
---

Configure o Radar de Vagas Laplace para a pessoa que está aqui. Leia o `CLAUDE.md`, o
`guia/04-personalizar.md` e o `guia/05-calibrar.md` antes de começar e **siga o procedimento do
CLAUDE.md**, pedindo aprovação a cada etapa:

1. Entreviste (cargo ou área, nível, UF e cidade-base, remoto) e peça de 3 a 10 vagas que ela
   gostaria de receber e algumas que rejeita. Se ela tiver o currículo em arquivo, peça o **caminho**
   (não o texto).
2. Rode `python -m vagas_monitor init --listar-areas` e escolha, com ela, as áreas e o papel de
   cada uma (alvo, adjacente, ponte). Rode o `init` com as respostas: `--manual` se não houver chave
   de IA ou se ela não quiser enviar o currículo; com `--curriculo`, mostre o texto anonimizado e só
   passe `--sim` depois de ela aprovar. Passe as vagas de referência com `--quero` e `--nao-quero`.
3. Complete o `perfil.md` só com o que ela disse. **Não invente.** Se o repositório for público,
   oriente a usar o secret `PERFIL_MD`.
4. Rode `python -m vagas_monitor calibrar`. Para cada erro, use
   `python -m vagas_monitor classificar "<título>"`, proponha a correção no `config.yaml` e mostre o
   antes e o depois. Repita até a meta. Rode também `calibrar --sondar` e discuta os candidatos.
5. Rode `python -m vagas_monitor run --force --dry-run --no-notify` e leia o relatório com ela.
6. Rode `python -m vagas_monitor doctor` e ajude com as credenciais que faltam (guia 02).
7. Rode `python -m pytest -q` e `python tools/leak_check.py` e resuma o que ficou.

Regras: nunca peça nem imprima segredos; não envie o currículo a nenhuma IA externa sem avisar e
sem a aprovação do texto anonimizado; avise que os packs fora de TI são `beta`; não faça push nem
merge sem a pessoa pedir.

$ARGUMENTS
