# Arquitetura do Projeto

Este documento descreve a arquitetura alvo do projeto de automação de ofertas. Ele não substitui `AGENTS.md`; ele detalha como os módulos devem se organizar para manter o fluxo simples, seguro e automatizável.

## Objetivo arquitetural

Transformar uma entrada controlada de ofertas em mensagens auditáveis para revisão humana, mantendo chamadas reais, publicação real e credenciais protegidas por travas explícitas.

## Fluxo principal

```text
Catálogo curado
-> Collector
-> Scorer
-> Copywriter
-> Compliance
-> Publisher dry-run
-> Artefatos locais para revisão
```

No alvo operacional, o fluxo deve continuar simples:

```text
API ou catálogo curado -> lista de ofertas -> mensagens -> revisão -> publicação controlada
```

## Princípios

- O modo padrão é sempre `dry-run`.
- HTTP real deve depender de `ENABLE_REAL_HTTP=true`.
- Publicação real deve depender de `ENABLE_REAL_PUBLISH=true`, canal permitido e aprovação humana.
- Integrações externas devem ficar atrás de providers ou gateways.
- O domínio interno deve usar modelos próprios, sem vazar payload bruto de marketplace para o restante do sistema.
- O fluxo operacional principal deve ser chamado por orquestrador, agendador ou automação, não por vários comandos manuais pequenos.

## Camadas

### 1. Entrada e coleta

Responsável por carregar produtos a partir de catálogo curado, mock, fixture ou provider controlado.

Local esperado:

```text
src/ofertas_bot/agents/
src/ofertas_bot/providers/
```

### 2. Normalização

Converte dados externos para modelos internos como `Offer`, mantendo campos essenciais de preço, marketplace, link, imagem, comissão, vendas e reputação.

Local esperado:

```text
src/ofertas_bot/models.py
src/ofertas_bot/providers/*mapper*.py
```

### 3. Ranqueamento

Aplica critérios de qualidade e prioridade de negócio para selecionar as melhores ofertas.

Critérios iniciais:

- desconto percentual;
- preço válido;
- comissão;
- vendas/reputação;
- frete/prime quando existir;
- aderência ao nicho.

### 4. Copy

Gera mensagem curta, clara e rastreável, sempre com aviso de afiliado quando houver link afiliado.

Local esperado:

```text
src/ofertas_bot/agents/copywriter.py
docs/copy-guidelines.md
```

### 5. Compliance

Valida a mensagem e bloqueia saídas inseguras.

Bloqueios obrigatórios:

- mensagem sem aviso de afiliado;
- link ausente;
- preço inválido;
- desconto inconsistente;
- tentativa de publicação real com trava desligada.

### 6. Publicação ou simulação

Na fase atual, apenas simulação e geração de artefatos locais. Publicação real fica fora do padrão até existir integração permitida, logs auditáveis, canal permitido e revisão humana.

## Artefatos locais

Arquivos de execução e revisão devem ficar em `.data/` e não devem ser tratados como documentação permanente.

Exemplos:

```text
.data/review_queue.json
.data/approved_messages.json
.data/publication_manifest.json
.data/local_review_bundle.json
```

## Fora de escopo arquitetural atual

- Disparo real automático em canais sem aprovação humana.
- Persistência de segredos no repositório.
- Bypass de política, limite ou detecção de plataformas.
- Multiplicação de CLIs pequenos sem necessidade operacional.

## Relação com specs

Mudanças de comportamento devem nascer em `specs/NNN_nome.md`. A arquitetura explica o desenho geral; a spec define uma entrega implementável e testável.
