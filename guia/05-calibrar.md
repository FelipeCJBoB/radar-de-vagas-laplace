# Calibrar: transformar "parece certo" em medida

Um monitor configurado "no olho" parece certo e erra em silêncio. O primeiro monitor deste
projeto só descobriu que ignorava "Implantador de Sistemas" e as vagas de SAP **depois de a
pessoa comparar à mão** o que ele capturava com as vagas em que ela se candidatou. A calibração
faz essa comparação por comando e dá um número.

## As três ferramentas

| Comando | Precisa de rede | O que responde |
|---|---|---|
| `classificar "título"` | não | em qual categoria um título cai, por qual termo, e por que não caiu |
| `calibrar` | não | quantas das vagas que você **quer** o monitor captura (recall) e quantas das que você **não quer** ele descarta (corte) |
| `calibrar --sondar` | sim | o que o mercado da sua região tem, o que cada termo seu captura (homônimos aparecem) e que vocabulário pode estar faltando |

## 1. O conjunto de referência

Junte títulos de vagas:

- **`quero`**: vagas que você gostaria de receber. As melhores fontes são as **candidaturas que
  você já fez** e as vagas que você achou à mão e achou boas.
- **`nao_quero`**: vagas que você descartaria, de preferência as parecidas com o que você quer
  (é nelas que os erros estão).

Informe no `init` (`--quero "..." --nao-quero "..."`, repetíveis) ou escreva em
`calibracao/referencia.yaml`:

```yaml
quero:
  - Analista Financeiro Pleno
  - Assistente de Contas a Pagar
nao_quero:
  - Fiscal de Loja
  - Dev Power Builder PL - Segmento Financeiro
```

Quanto mais exemplos, mais confiável a medida; **5 de cada** já mostram o rumo. O arquivo é pessoal
e fica fora do git.

## 2. Meça

```bash
python -m vagas_monitor calibrar
```

```
Recall das vagas queridas : 67%  (2/3)
Corte das indesejadas     : 50%  (1/2)
Meta: 80%

FALTARAM (você queria, o monitor descarta):
  - Assistente de Cobrança Jr: nenhuma categoria casou
  -> acrescente o título em `titulo` da categoria certa, ou um termo de busca.

SOBRARAM (você não quer, o monitor aceita):
  - Dev Power Builder PL - Segmento Financeiro: Financeiro por título: financeiro
  -> troque o termo por uma expressão mais específica ou use excluir_titulo na categoria.
```

O comando sai com código 1 abaixo da meta (padrão 80%, `--meta 0.9` para exigir mais). Cada erro
traz o **motivo** e o que fazer.

## 3. Corrija

| Erro | Causa | Correção |
|---|---|---|
| **Faltou**: "nenhuma categoria casou" | o título da empresa usa uma palavra que você não tem | acrescente a expressão em `titulo` da categoria certa |
| **Sobrou**: caiu por um termo largo | o termo casa com outra área (`financeiro`, `fiscal`, `segurança`) | troque por uma expressão específica (`"analista financeiro"`) |
| **Sobrou**: homônimo | a palavra é a mesma, a função é outra | coloque a expressão em `excluir_titulo` **da categoria** |

`excluir_titulo` dentro de uma categoria só tira a vaga **dela**: "fiscal de loja" sai de Contábil
mas continuaria entrando noutra categoria que a queira. O `excluir_titulo` global do config vale
para todas e é para o que você **nunca** quer.

```yaml
categorias:
  contabil_fiscal:
    nome: Contábil e Fiscal
    titulo: [contador, "analista fiscal"]
    excluir_titulo: ["fiscal de loja", "fiscal de obra"]
```

Para entender um caso: `python -m vagas_monitor classificar "Fiscal de Loja"`. Repita até bater a
meta.

## 4. Sonde o mercado

A referência mede o que você **sabe** querer. A sondagem mostra o que você **não sabia**:

```bash
python -m vagas_monitor calibrar --sondar                 # só Gupy, últimos 30 dias (segundos)
python -m vagas_monitor calibrar --sondar --fontes gupy,indeed,linkedin   # leva minutos
```

Ela coleta os títulos reais da região e mostra duas listas.

**Termos atuais e o que cada um captura**, com amostras. É aqui que os homônimos aparecem:

```
[Contábil e Fiscal] 'contabilidade': 4 vaga(s)
    ex.: Estágio em Contabilidade: Dados e Inteligência Artificial
    ex.: Analista de Suporte Jr – Área Contabilidade
```

Duas vagas de TI entrando por um termo contábil largo. A correção foi trocar `contabilidade` por
`"analista de contabilidade"`.

**Candidatos**: expressões frequentes nos títulos que o seu config **descarta**. Se alguma é uma
vaga que você quer, ela vira termo. A lista já tira os nomes de cidade, estado e nível, e junta
pedaços repetidos (`atendente restaurante` em vez de `atendente` e `restaurante` separados).

## Quando vêm poucas vagas

1. Rode `calibrar --sondar`: quantos títulos a região tem e quantos o seu config pega?
2. Aumente o **alcance** (`regiao_imediata` → `estado`) ou aceite **remoto** (`regiao.remoto`).
3. Amplie a **janela** (`lookback_days`) para ver mais vagas por rodada.
4. Verifique a **cobertura das fontes**: Gupy, Indeed e LinkedIn trazem pouca vaga operacional,
   de saúde e de comércio. Se o seu setor vive de outros canais (SINE, grupos, agências), o monitor
   vai ver pouco, e isso não é defeito do config.
5. Veja se o `doctor` aponta alguma fonte vazia.

## Quando repetir

Depois de **algumas rodadas** e sempre que mudar de objetivo. O relatório mostra o que entrou; uma
vaga boa que você achou por outro caminho e o monitor não trouxe vira uma linha nova em `quero`, e
uma que não serviu, em `nao_quero`. A referência só cresce, e a medida fica mais confiável.

## Limites

- Recall e corte medem **títulos**. Uma vaga com título certo e descrição que não serve passa; a
  nota da IA e o seu olhar cuidam disso.
- O corte só vale para os `nao_quero` que você listou. Vagas que você nunca viu não entram na conta.
- Packs `beta` (todos fora de TI) são pontos de partida: a calibração com vagas **reais** é o que
  os valida para você.
