# IA gratuita, limites e custos

A IA é **opcional**. Sem chave, o monitor coleta, filtra, pontua e notifica do mesmo jeito, só sem
a nota de 0 a 10 e o comentário por vaga. Com chave, as melhores vagas **novas** de cada rodada
(até `avaliacao.max_vagas`, padrão 25) recebem a avaliação, escrita a partir do seu perfil.

## O que é enviado

A cada chamada: o **anúncio da vaga** (público) e o **seu perfil** (`perfil.md` ou `PERFIL_MD`).
Nada além disso. Por isso o perfil não deve ter telefone, endereço, CPF nem e-mail.

## Gemini (gratuito) ou Claude (pago)

| | Gemini (Google AI Studio) | Claude (Anthropic) |
|---|---|---|
| Custo | nível gratuito | pré-pago; poucos centavos a cerca de US$ 0,30 por rodada, conforme o modelo |
| Chave | <https://aistudio.google.com/apikey> | <https://console.anthropic.com> |
| Treino | no nível gratuito o Google **pode usar o texto enviado para treinar** | a API não usa para treinar |
| Limite | por minuto (10 por minuto no Flash gratuito) | pelo saldo da conta |
| Variável | `GEMINI_API_KEY` | `ANTHROPIC_API_KEY` |

`avaliacao.provedor: auto` usa o primeiro que achar chave, preferindo o Gemini. Para fixar:
`gemini`, `anthropic` ou `nenhum`.

Uma **assinatura** (Gemini Pro, Claude.ai) **não** dá chave de API: são cobranças separadas.

## Quanto uma rodada consome

Até 25 chamadas a cada 5 dias. As chamadas são espaçadas conforme `avaliacao.gemini.rpm` para não
esbarrar no limite por minuto: 25 vagas a 10 por minuto levam pouco mais de 2 minutos, irrelevante
numa rodada que já gasta vários coletando. É muito abaixo do limite diário gratuito.

## Quando o Gemini fica sobrecarregado (503)

No nível gratuito o modelo principal às vezes responde **503 "modelo sobrecarregado"**, às vezes
por horas. O monitor se defende em três camadas:

1. **Tenta de novo** a mesma vaga, com esperas crescentes (2, 6 e 15 segundos).
2. **Modelo de reserva.** Esgotadas as tentativas, tenta `avaliacao.gemini.modelos_reserva` (por
   padrão `gemini-flash-lite-latest`, mais leve e quase sempre de pé). Depois do primeiro socorro
   que funciona, a rodada **segue no reserva** em vez de pagar de novo as esperas.
3. **Disjuntor.** Depois de 3 vagas seguidas sem resposta (reserva incluída), desiste: a rodada
   segue sem notas e o motivo aparece no topo do relatório. A avaliação **nunca** derruba a rodada.

Erros definitivos (chave inválida, modelo inexistente, sem saldo) desistem na hora, sem esperar.

## Validar e diagnosticar

```bash
python -m vagas_monitor check-ia        # uma chamada real com uma vaga de teste
python -m vagas_monitor doctor --ia     # idem, dentro do diagnóstico completo
```

Mostram quais chaves foram encontradas, qual provedor seria usado e o resultado da chamada.

## Trocar de modelo

Em `config.yaml`:

```yaml
avaliacao:
  provedor: auto
  max_vagas: 25
  gemini:
    modelo: gemini-flash-latest              # alias que o Google mantém apontando para o Flash atual
    modelos_reserva: [gemini-flash-lite-latest]
    rpm: 10
  anthropic:
    modelo: claude-opus-5
    esforco: low
```

Fixar uma versão (`gemini-3.5-flash`) evita mudança de comportamento, mas quebra sozinho quando
aquela versão sai do ar. O alias acompanha o Google.

## Desligar

`avaliacao.provedor: nenhum`. O resto do monitor não muda.
