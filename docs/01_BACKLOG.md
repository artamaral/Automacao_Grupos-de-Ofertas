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
- Refinar keywords e taxonomia de `auto-e-moto` após a primeira limpeza real,
  porque a rodada atual ainda concentrou muitos itens em subnichos genéricos
  e deixou volume alto de `unmapped_source_keywords` para revisão posterior.
- Revisar a qualidade semântica dos subnichos nos catálogos operacionais `4.8+`,
  porque preenchimento completo de `subniches` não garante coerência real do
  item com o subnicho atribuído.
- Levantar e corrigir falsos positivos semânticos nos tops por subnicho,
  principalmente quando keyword ampla ou genérica puxa item para um grupo
  plausível no texto, mas incorreto no contexto comercial.
- Revisar a base de palavras-chave e a lógica de classificação usando como
  evidência os artefatos `top10_por_subnicho.csv` gerados para
  `mae-e-bebe`, `auto-e-moto` e `feminino`.
- Reduzir casos em que um item entra em subnicho tecnicamente preenchido, mas
  semanticamente fraco, ambíguo ou fora do contexto principal do nicho.

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
- Criar um script local iniciado pelo operador para atualizar o catalogo ativo
  diretamente no ambiente do `n8n`, garantindo sincronizacao do CSV curado por
  `profile` antes das rodadas.
- Deixar essa sincronizacao de catalogo mais ergonomica no fluxo operacional do
  `n8n`, reduzindo dependencia de passos manuais e tratando isso como melhoria
  operacional ainda em aberto.
- Avaliar aprovação operacional via WhatsApp, tratando o canal apenas como
  interface de decisão humana (aprovar/rejeitar/ajustar), com trilha de auditoria,
  idempotência e reconciliação posterior no fluxo local.

## Pontos em aberto

- Qual será o escopo da coleta ampla por macro-nicho na Shopee real.
- Quais campos reais da API serão confiáveis para classificar subnicho.
- Como endurecer a taxonomia sem perder cobertura, reduzindo falsos positivos
  semânticos nos subnichos mais amplos.
- Quais regras devem prevalecer quando keyword, nome do produto e contexto
  comercial sugerirem subnichos diferentes.
- Como medir qualidade semântica da classificação de subnicho de forma
  recorrente sem travar o fluxo operacional.
- Como representar roteamento para um ou mais grupos sem complicar o fluxo.
- Como separar classificação determinística de classificação assistida por LLM.
- Quando cupons entram na mesma esteira dos produtos e quando precisam de regra
  própria.
