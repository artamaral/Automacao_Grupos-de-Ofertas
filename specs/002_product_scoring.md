# SPEC 002 — Scoring e Priorização de Produtos

Status: Rascunho

## Objetivo

Definir como o projeto deve pontuar e ordenar ofertas para priorizar produtos com melhor potencial de valor para o usuário e para a operação.

## Contexto

O scoring deve ajudar a selecionar ofertas, mas não deve substituir regras mínimas de qualidade do catálogo. Produto inválido deve ser bloqueado antes de ser ranqueado.

## Entrada

Lista de ofertas normalizadas, preferencialmente já limpa pela etapa de catálogo.

Campos relevantes:

```text
price
old_price
discount_percent
commission_rate
sales_count
rating
niche
subniche
marketplace
shipping_signal
prime_signal
source_keyword
```

## Saída

Lista de ofertas com pontuação e motivos principais do ranqueamento.

Exemplo conceitual:

```text
ScoredOffer(offer=..., score=0.82, reasons=["desconto alto", "boa reputação"])
```

## Regras obrigatórias

- Não ranquear produto com preço inválido.
- Não inventar nota, vendas, frete, comissão ou desconto.
- Penalizar campos ausentes sem descartar automaticamente quando a oferta ainda for válida.
- Separar regras de qualidade mínima de regras de ranking.
- Tornar pesos configuráveis quando possível.
- Manter explicação curta dos principais motivos do score.

## Critérios iniciais

Critérios sugeridos:

- desconto percentual válido;
- comissão;
- vendas/reputação;
- aderência ao nicho/subnicho;
- sinal de frete/prime quando disponível;
- qualidade dos campos essenciais.

## Fora de escopo

- Buscar produtos em marketplace.
- Gerar copy final.
- Publicar mensagens.
- Usar preço ou reputação não fornecidos pela entrada.

## Critérios de aceite

- Dada lista com múltiplas ofertas válidas, a saída vem ordenada por score.
- Oferta com desconto inválido não recebe vantagem indevida.
- Oferta com maior comissão não vence automaticamente se a qualidade for ruim.
- O resultado inclui motivo ou sinal auditável do ranqueamento.
- Pesos não ficam espalhados sem documentação.

## Testes esperados

- Teste de ordenação básica.
- Teste de desconto válido.
- Teste de penalização por reputação ausente.
- Teste de aderência ao nicho.
- Teste garantindo que preço inválido não é ranqueado.

## Harness / validação local

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage prepare --niche maquiagem --marketplace mock --target grupo-maquiagem
```

A fila gerada deve refletir a ordem ou seleção definida pelo scorer.
