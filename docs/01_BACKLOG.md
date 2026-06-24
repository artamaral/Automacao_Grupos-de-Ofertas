# Backlog

Este arquivo registra ideias, melhorias, riscos, pendências e evoluções
possíveis do projeto.

Regras:

- backlog não define execução imediata;
- backlog pode registrar hipóteses ainda não validadas;
- itens só devem virar implementação quando forem puxados para a priorização
  operacional do projeto.

## Descoberta, classificação e roteamento

- Criar uma camada de descoberta ampla por `profile`, sem depender de
  `subgroup` como entrada principal da automação.
- Criar uma camada de classificação que atribua `subgroup`, categorias,
  aderência e sinais de contexto a cada oferta coletada.
- Criar uma camada de roteamento que decida para quais grupos uma oferta pode
  seguir.
- Permitir que uma mesma coleta ampla gere ofertas para múltiplos grupos.
- Definir estrutura intermediária para representar `offer + score +
  classification + routing`.
- Validar os `subgroups` atuais contra retorno real da Shopee antes de tratá-los
  como contrato rígido.
- Medir quais queries amplas funcionam melhor por macro-nicho.
- Medir quais `subgroups` têm cobertura útil e quais geram ruído demais.
- Adiar regra rígida de classificação e roteamento até haver dados reais
  suficientes para calibrar decisão com evidência.
- Adiar ponderação fina de score comercial até observar volume, qualidade e
  estrutura real das ofertas retornadas.

## Shopee real

- Validar categorias, coleção, marca e demais sinais reais que a API devolver.
- Confirmar quais campos da Shopee ajudam de fato na classificação de
  subnicho.
- Comparar query ampla versus query focada por subgroup.
- Definir estratégia de paginação e volume por profile.
- Definir regra de coleta incremental e frequência por nicho.
- Criar rotina de inspeção da saída real para entender cobertura, ruído e
  sinais disponíveis antes de endurecer regras de decisão.

## Scoring e decisão

- Separar score de qualidade comercial do score de aderência ao grupo.
- Criar score específico para cupom versus score para produto.
- Adicionar explicações claras de por que a oferta foi roteada para cada grupo.
- Definir score mínimo por grupo e por macro-nicho.
- Tratar conflito quando uma oferta servir para mais de um grupo.

## Mensagens

- Gerar mensagens a partir de uma lista de ofertas já selecionadas, em vez de
  acoplar tudo ao harness.
- Diferenciar mensagem de produto, cupom e mensagem contextual/humanizada.
- Ajustar variação de copy por grupo e por tipo de oferta.
- Definir quando vale mensagem única por oferta e quando vale resumo por lote.

## Operação e governança

- Criar catálogo formal de grupos de destino e regras por grupo.
- Definir manifestos mínimos para auditoria operacional sem excesso de artefato.
- Planejar evolução do config para suportar perfis ativos/inativos e prioridade.
- Decidir quando perfis e grupos saem de arquivo versionado para banco/interface.
- Definir observabilidade mínima do fluxo operacional.

## Pontos em aberto

- Qual será o escopo da coleta ampla por macro-nicho na Shopee real.
- Quais campos reais da API serão confiáveis para classificar subnicho.
- Como representar roteamento para um ou mais grupos sem complicar o fluxo.
- Como separar classificação determinística de classificação assistida por LLM.
- Quando cupons entram na mesma esteira dos produtos e quando precisam de regra
  própria.
