# Análise operacional do projeto

Este documento orienta as próximas decisões de implementação. A definição de
objetivo, escopo e modelo operacional está em `docs/objetivo-operacional.md`.
O foco de implementação é operacional e deve seguir apenas três eixos
principais:

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

Além disso, a automação não deve depender de `--subgroup` como forma principal
de descoberta. `Profile` e `subgroup` ajudam na organização, no debug e no
recorte controlado, mas o fluxo operacional alvo precisa aceitar coleta ampla
por macro-nicho, seguida de classificação e roteamento.

O que falta para este eixo:

- Ter uma função/serviço explícito para gerar lista de ofertas por nicho e marketplace.
- Retornar uma estrutura clara com `offer`, `score` e `reasons`.
- Definir limite padrão e ordenação como comportamento central.
- Evitar que o fluxo dependa de vários arquivos intermediários para entender quais ofertas foram selecionadas.
- Criar uma camada de classificação para atribuir `subgroup` e sinais de
  aderência depois da coleta.
- Criar uma camada de roteamento para indicar para quais grupos cada oferta pode
  seguir.

### Decisão

A próxima implementação deve favorecer uma camada clara de geração de lista de ofertas. Antes de qualquer publicação ou auditoria avançada, o sistema deve responder bem à pergunta: “quais ofertas foram selecionadas e por quê?”.

Também fica registrada a decisão arquitetural:

- `subgroup` não é o motor principal da automação;
- `subgroup` é apoio para taxonomia, debug, coleta dirigida e futura
  catalogação;
- a automação principal deve preferir coleta ampla por `profile`;
- depois da coleta, o sistema deve classificar a oferta e só então decidir seu
  roteamento.

Nova decisão operacional desta etapa:

- o `Scorer` continua rankeando a base elegível;
- o `Copywriter GPT` não deve receber automaticamente todos os itens pontuados;
- entre score e copy deve existir um gate de seleção configurável;
- esse gate deve concentrar regras temporais, bandas por nicho/subnicho,
  diversidade por similaridade e refresh final de preço/comissão.

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

Fronteira registrada para GPT:

- GPT não escolhe a oferta;
- GPT não aplica banda;
- GPT não decide similaridade;
- GPT não resolve staleness de preço/comissão;
- GPT recebe apenas `CopyBrief` de itens já aprovados pela seleção.

## Regras de seleção antes do copy

As próximas implementações do fluxo principal devem tratar a seleção como camada
própria de negócio, com config explícito.

### 1. Janela temporal

- persistir `selected_at` por oferta;
- aplicar `cooldown` simples como regra temporária;
- depois do vencimento, a oferta volta a ficar elegível;
- manter essa regra em config, e não hardcoded.

Config esperado:

- `selection.cooldown_hours_default`

### 2. Banda por nicho e subnicho

- a rodada não deve distribuir volume igual entre subnichos por padrão;
- cada nicho/subnicho deve ter uma banda percentual do total da rodada;
- a calibração deve usar histograma de vendas por nicho/subnicho;
- a banda limita volume máximo, mas não obriga preencher cota com item fraco.

Config esperado:

- `selection.band_allocation`

### 3. Similaridade e diversidade

- usar regra de similaridade por descrição normalizada + vendedor;
- manter o melhor item do cluster e suprimir os demais na rodada;
- registrar essa supressão como motivo operacional próprio;
- não usar essa supressão como rejeição definitiva para calibragem de score.

Config esperado:

- `selection.similarity`

### 4. Refresh final antes do copy

- todo item selecionado deve ter preço e comissão rechecados via API;
- se algum item mudar, a lista precisa ser reordenada e reavaliada;
- repetir o ciclo até a saída estabilizar ou atingir o limite configurado;
- bloquear ida para copy quando a lista continuar stale além do limite.

Config esperado:

- `selection.refresh_before_copy`

### Registro obrigatório

Independentemente da implementação concreta, essa camada deve registrar:

- `selected_at`
- `cooldown_until`
- `selection_reason`
- `similarity_status`
- `refresh_iteration`
- `fields_changed`
- `stability_reached`

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

1. Criar uma camada operacional de descoberta ampla por `profile`.
2. Criar uma camada operacional de classificação e roteamento das ofertas
   coletadas.
3. Criar uma camada operacional para gerar lista de ofertas selecionadas com
   `offer + score + classification + routing`.
4. Criar uma camada operacional para gerar mensagens a partir dessa lista.
5. Unificar o fluxo principal para automação chamar essas camadas com poucos
   parâmetros.
6. Só depois retomar persistência, histórico e integrações reais.

## Próxima etapa de maior valor operacional

A camada completa de classificação, roteamento e decisão deve ser adiada até a
entrada de dados reais.

Motivos registrados:

1. a estrutura real de saída da API ainda não está suficientemente conhecida;
2. sem dados reais, fica frágil definir regra de score, aderência e ponderação
   do que é uma boa oferta.

Decisão:

- manter a taxonomia de `subgroups` como escopo inicial e apoio de catalogação;
- não transformar isso ainda em motor definitivo de decisão;
- adiar regra rígida de classificação e roteamento até existir retorno real da
  Shopee.

Assim, a próxima etapa de maior valor operacional passa a ser:

criar uma camada operacional de coleta ampla e inspeção estruturada da saída.

Saída esperada dessa etapa:

- coletar mais ofertas por `profile`;
- salvar saída normalizada de forma consistente;
- preservar sinais úteis para análise posterior;
- facilitar leitura do que a API realmente devolve por nicho;
- preparar base para calibrar score e roteamento com evidência real.

Sem esse passo, o projeto corre o risco de sofisticar regras sobre hipóteses em
vez de sobre dados observados.

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
