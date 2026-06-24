# Análise operacional do projeto

Este documento passa a orientar as próximas decisões de implementação. O foco do projeto é operacional e deve seguir apenas três eixos principais:

1. Comunicador com API.
2. Geração de lista de ofertas.
3. Geração de mensagens.

Ferramentas auxiliares já criadas continuam disponíveis, mas não devem guiar novas implementações.

## 1. Comunicador com API

### O que já existe

O projeto já possui uma camada inicial para comunicação com marketplaces:

- `CollectorAgent` escolhe o provider por marketplace (`mock`, `amazon`, `shopee`).
- `ShopeeProvider` possui validação de configuração, builder de request assinado, gateway, mapper e transport injetável.
- `AmazonProvider` possui validação de configuração, builder de request, gateway e transport injetável.
- O modo HTTP real fica bloqueado por configuração e validações.
- O provider mock funciona para fluxo de desenvolvimento.

### Estado crítico

A comunicação com API existe, mas ainda está espalhada entre agent, provider, gateway, builder, mapper e harness. Isso é tecnicamente aceitável, mas ainda não está simples como contrato operacional.

O que falta para este eixo:

- Definir um contrato único de comunicador: entrada simples, saída simples, erro padronizado.
- Separar claramente `fake/mock`, `preview`, `diagnóstico` e `real HTTP`.
- Garantir que Shopee/Amazon reais continuem bloqueados enquanto não houver credenciais e aprovação.
- Evitar adicionar novos CLIs para cada detalhe de API.

### Decisão

Próximas mudanças neste eixo devem simplificar a entrada e a saída da comunicação com API. Não criar novas ferramentas auxiliares se elas não servirem diretamente à coleta de ofertas.

## 2. Geração de lista de ofertas

### O que já existe

O projeto já consegue gerar uma lista normalizada de ofertas:

- Providers retornam `Offer`.
- `ScorerAgent` transforma `Offer` em `ScoredOffer`.
- A pontuação considera desconto, comissão, vendas, avaliação e frete.
- O harness consegue salvar ofertas normalizadas em JSON.

### Estado crítico

A lista existe, mas ainda não está apresentada como produto operacional principal. Hoje ela aparece como efeito colateral do harness ou de arquivos auxiliares.

O que falta para este eixo:

- Ter uma função/serviço explícito para gerar lista de ofertas por nicho e marketplace.
- Retornar uma estrutura clara com `offer`, `score` e `reasons`.
- Definir limite padrão e ordenação como comportamento central.
- Evitar que o fluxo dependa de vários arquivos intermediários para entender quais ofertas foram selecionadas.

### Decisão

A próxima implementação deve favorecer uma camada clara de geração de lista de ofertas. Antes de qualquer publicação ou auditoria avançada, o sistema deve responder bem à pergunta: “quais ofertas foram selecionadas e por quê?”.

## 3. Geração de mensagens

### O que já existe

O projeto já possui geração de mensagens:

- `CopywriterAgent` cria `MessageDraft` a partir de `ScoredOffer`.
- Mensagens incluem preço, marketplace, link e aviso de afiliado.
- Há variações compactas por perfil de grupo.
- `ComplianceAgent` valida disclosure, link, preço e trava de publicação real.
- Mensagens aprovadas podem ser salvas em JSON/TXT.

### Estado crítico

A geração de mensagens funciona, mas está acoplada ao fluxo do harness e a várias saídas locais. Para o produto, a geração de mensagens deve ser uma etapa clara depois da lista de ofertas.

O que falta para este eixo:

- Ter uma função/serviço explícito para gerar mensagens a partir de uma lista de ofertas selecionadas.
- Manter compliance como parte obrigatória da geração de mensagens.
- Produzir saída simples para o próximo consumidor: interface, orquestrador ou publicador futuro.
- Evitar continuar aumentando fila, bundle, manifesto e relatórios antes de simplificar essa etapa.

### Decisão

A próxima implementação deve consolidar a geração de mensagens como etapa operacional clara e reaproveitável, sem criar novos formatos paralelos.

## O que fica congelado por enquanto

As seguintes peças existem e podem continuar, mas não devem ser expandidas agora:

- múltiplos CLIs pequenos;
- contadores locais;
- hashes locais;
- bundles locais;
- doctors locais;
- relatórios auxiliares;
- novos manifests ou formatos de auditoria.

Essas peças só devem receber correção de bug, lint ou teste.

## O que deve ser implementado a seguir

A ordem recomendada é:

1. Criar uma camada operacional para gerar lista de ofertas selecionadas.
2. Criar uma camada operacional para gerar mensagens a partir dessa lista.
3. Unificar o fluxo principal para automação chamar essas camadas com poucos parâmetros.
4. Só depois retomar persistência, histórico e integrações reais.

## Critério para aceitar nova implementação

Toda nova mudança deve responder “sim” a pelo menos uma destas perguntas:

- Ajuda a comunicar com API de ofertas?
- Ajuda a gerar uma lista de ofertas selecionadas?
- Ajuda a gerar mensagens a partir das ofertas?
- Reduz complexidade operacional do fluxo principal?

Se a resposta for “não”, a mudança deve ser adiada.

## Fora de escopo neste momento

- Publicação real.
- Mais ferramentas de auditoria.
- Mais flags para CLIs auxiliares.
- Integração real Shopee antes da aprovação de conta/app.
- Integração real Amazon antes da configuração formal da PA API.
- Automação de WhatsApp fora de canal permitido e opt-in.
