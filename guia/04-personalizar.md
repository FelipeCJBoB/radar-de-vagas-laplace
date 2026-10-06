# Personalizar o monitor

O `config.yaml` vem **vazio de propósito**: o monitor não sabe onde você mora, o que você faz nem
em que nível está, e não adivinha. Enquanto os campos obrigatórios estiverem vazios, `run` para e
lista o que falta. Este guia preenche cada um, na ordem.

**O jeito mais rápido é o `init`**, que faz tudo abaixo por você e valida o resultado:

```bash
python -m vagas_monitor init                       # pergunta e gera config.yaml e perfil.md
python -m vagas_monitor init --listar-areas        # o catálogo de 17 áreas prontas
python -m vagas_monitor init --curriculo cv.pdf    # uma IA propõe áreas e termos (currículo anonimizado e aprovado por você)
python -m vagas_monitor init --manual --estado SP --cidade Campinas --nivel pleno \
    --area administrativo-financeiro --area contabil-fiscal:adjacente \
    --quero "Analista Financeiro Pleno" --nao-quero "Fiscal de Loja"
```

Cada `--area` é `slug` ou `slug:papel`, e o papel é `alvo` (padrão), `adjacente` ou `ponte`. O
`init` guarda a versão anterior em `config.yaml.bak` e `perfil.md.bak`. Com o Claude Code, use
`/personalizar`: ele te entrevista e roda o `init` por você. O que se segue explica cada seção,
para você conferir e ajustar à mão.

> **Os packs de fora de TI são `beta`**: sementes geradas com IA, sem validação de quem trabalha
> na área. O ponto de partida é bom; a calibração com vagas **reais** ([guia 05](05-calibrar.md))
> é o que o valida para você.

## 1. Onde você busca: `regiao`

```yaml
regiao:
  estados: [PB]                  # sigla(s) da(s) UF(s)
  base: {cidade: João Pessoa, uf: PB}
  alcance: regiao_imediata       # cidade | regiao_imediata | estado | lista
  remoto: aceitar                # nao | aceitar | preferir | somente
```

- **`estados`**: onde o Indeed e a Gupy procuram. Pode ter mais de um: `[SP, RJ]`.
- **`base`**: sua cidade. Se digitar errado, a mensagem de erro sugere a grafia certa.
- **`alcance`** define quais cidades contam como "perto":
  - `cidade`: só a base;
  - `regiao_imediata`: a **área de deslocamento diário** do IBGE (a de Campinas, por exemplo,
    reúne os municípios vizinhos que dependem dela). É o padrão recomendado;
  - `estado`: o estado inteiro (centenas de cidades; o relatório mostra um resumo);
  - `lista`: você escolhe em `regiao.cidades: [...]`.
- **`remoto`**: `aceitar` inclui vagas remotas sem pontuação extra; `preferir` soma +12;
  `nao` descarta as remotas; `somente` busca só remoto (dispensa `estados` e `base`).
- **`apelidos`** (opcional): `{Camboriú: Balneário Camboriú}` faz um nome alternativo contar como
  a cidade canônica.

O LinkedIn busca por cidade, e cada cidade custa tempo de rodada. Por padrão ele usa só a
`base`; para somar outras, `fontes.linkedin.cidades_ancora: [Cidade A, Cidade B]`.

## 2. O que você busca: `alvo`

```yaml
alvo:
  nivel: pleno                   # estagio | junior | pleno | senior | lideranca
  aceita_niveis: [junior]        # opcional: níveis vizinhos que também servem
```

O nível comanda a pontuação: a vaga **no seu nível** soma +25, a de um degrau de distância +8 e a
de dois ou mais degraus −30. Quem busca vaga sênior vê as sênior no topo; quem busca estágio, os
estágios. `aceita_niveis` impede que um nível que você aceita seja penalizado.

## 3. Termos de busca

```yaml
termos_busca: [financeiro, contador]
```

São as palavras enviadas ao LinkedIn e ao Indeed (e às vagas remotas). A Gupy varre o estado
inteiro e filtra por categoria depois. Cada termo custa tempo de rodada, então use poucos e
largos. Comece com 2 a 5 e acrescente só quando uma vaga que você queria **não apareceu** por falta
dele.

## 4. Categorias: o coração da classificação

Uma categoria diz: "vaga com estes termos no **título** (ou 3 termos na **descrição**) é desta
área". Sem categoria, a vaga é descartada.

```yaml
categorias:
  financeiro:
    nome: Financeiro
    prioridade: 1                # 1 = a mais desejada
    bonus: 12                    # soma na nota da vaga
    titulo: ["analista financeiro", "assistente financeiro", tesouraria, "contas a pagar", "contas a receber"]
    descricao: ["fluxo de caixa", conciliação, "contas a pagar", "contas a receber"]
  contabil:
    nome: Contábil
    prioridade: 2
    bonus: 8
    titulo: [contador, contábil, contabilidade, "analista fiscal"]
    descricao: [balanço, escrituração, tributos, "obrigações acessórias"]
```

**Pense em três papéis**, que definem o `bonus`:

| Papel | O que é | `bonus` |
|---|---|---|
| **alvo** | o que você quer ser | positivo (8 a 12) |
| **adjacente** | vizinho legítimo | 0 |
| **ponte** | o que a sua experiência sustenta, mas não é o desejo | negativo (−6 a −10): aparece no radar sem disputar o topo |

A **ponte** importa: quem trabalha com ERP e quer migrar para análise de dados ganha muito ao
ver vagas de ERP também, só que abaixo das de dados.

**Dicas para os termos:**
- Escreva **expressões específicas**, não palavras soltas. `"analista financeiro"` é melhor que
  `financeiro`, que casa com "Dev Power Builder, segmento financeiro" (vaga de TI).
- A busca ignora acento e caixa e respeita fronteira de palavra (`sap` não casa em "sapataria").
- Termo curto que também é palavra comum (como `ia`, `bi`) casa fácil demais no título. Prefira a
  expressão inteira (`"inteligência artificial"`). O prefixo `=` (exige a grafia exata, como
  `=React`) existe só no `skills.yaml`, não nas categorias.

## 5. Nível, exclusões e habilidades

```yaml
senioridade:                     # já vem preenchido com os termos comuns; ajuste se precisar
  junior: [júnior, junior, jr, estágio, estagiário, trainee, assistente]
  pleno: [pleno, plena, pl]
  senior: [sênior, senior, sr, especialista, coordenador, gerente, supervisor]

excluir_titulo: ["fiscal de loja", "fiscal de prevenção"]   # NUNCA interessam
habilidades: [excel, conciliação, sap]                       # cada acerto soma pontos (máx. +18)
```

`excluir_titulo` é onde você mata os **homônimos**: palavras que, em outra área, significam outra
coisa. "Segurança do trabalho" não é "segurança da informação"; "fiscal de loja" não é "fiscal
tributário"; "agente de negócios" não é "agente de IA".

Há duas listas, e a diferença importa:

- **`excluir_titulo` dentro de uma categoria** tira a vaga **só daquela categoria**. É o que os
  packs usam: "fiscal de loja" sai de Contábil, mas outra categoria sua ainda pode querer a vaga.
- **`excluir_titulo` na raiz do config** descarta a vaga **em qualquer categoria**. Use para o que
  você nunca quer ("vendedor", "motorista", se não for a sua área).

```yaml
categorias:
  contabil_fiscal:
    nome: Contábil e Fiscal
    titulo: [contador, "analista fiscal"]
    excluir_titulo: ["fiscal de loja"]      # só desta categoria
excluir_titulo: [estágio de verão]          # global: nunca interessa
```

## 6. O perfil

Copie `perfil.example.md` para `perfil.md` e preencha. É o texto que a IA lê para dar a nota.
Escreva só o que é verdade e evite telefone, endereço e CPF. Em repositório **público**, guarde o
texto no secret `PERFIL_MD` em vez de commitar ([privacidade](06-privacidade.md)).

## Calibrar com vagas reais

Este é o passo que separa um monitor útil de um monitor que parece certo. O guia completo, com
as métricas (`calibrar`) e a sondagem do mercado (`calibrar --sondar`), é o [guia 05](05-calibrar.md).
Em resumo, o método:

1. **Junte vagas de referência.** De 3 a 10 vagas que você **quer** receber (de candidaturas
   passadas ou achadas à mão) e algumas que você **não quer**.
2. **Rode o ensaio:** `python -m vagas_monitor run --force --dry-run --no-notify`. Ele não
   notifica nem salva estado. Abra o `reports/LATEST.md`.
3. **Procure dois erros.**
   - *Faltou*: uma vaga que você queria e não veio. Descubra por quê com o comando abaixo.
   - *Sobrou*: uma vaga que veio e não serve.
4. **Diagnostique cada erro** com o `classificar`, que mostra qual termo decidiu:

   ```bash
   python -m vagas_monitor classificar "Fiscal de Loja - Vaga Natal" "Analista Fiscal"
   ```

   ```
   título: Fiscal de Loja - Vaga Natal
     Contábil (+30) por título: fiscal <- principal
   ```

5. **Corrija o `config.yaml`** e repita. Para "Fiscal de Loja" entrando em Contábil: troque o
   termo `fiscal` por `"analista fiscal"` e coloque `"fiscal de loja"` em `excluir_titulo`. Para uma
   vaga que faltou: acrescente o título que a empresa usou, ou um termo de busca.
6. **Quando as vagas que você queria aparecem e as que não servem somem, está calibrado.**

Um exemplo real desse ciclo: num teste com `estados: [PB]`, área financeira e nível pleno, o termo
`financeiro` soltinho trouxe "Dev Power Builder PL - Segmento Financeiro" (uma vaga de TI) e o
termo `fiscal` trouxe "Fiscal de Loja". Trocar `financeiro` por `"analista financeiro"` e
`fiscal` por `"analista fiscal"`, mais as exclusões, resolveu os dois sem perder
"Analista Financeiro Pleno", "Analista Fiscal" nem "Contador Pleno".

**Repita a calibração** depois de algumas rodadas: o relatório mostra o que entrou, e o que você
percebe que falta vira um termo novo.

## Verificação rápida

```bash
python -m vagas_monitor run --force --dry-run --no-notify   # lista o que falta, ou roda o ensaio
python -m vagas_monitor status
python -m pytest -q                                         # se você mexeu no código
```
