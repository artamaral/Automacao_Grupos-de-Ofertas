# Backlog

Este arquivo registra ideias, melhorias, riscos, pendências e evoluções
possíveis do projeto.

Regras:

- backlog não define execução imediata;
- backlog pode registrar hipóteses ainda não validadas;
- itens só devem virar implementação quando forem puxados para a priorização
  operacional do projeto.

## Descoberta, classificação e roteamento

- Reaproveitar os codigos existentes de descoberta e classificacao semantica
  quando essa frente sair do backlog; eles ja rodam, mas devem ser simplificados
  e melhorados antes de virar parte do fluxo operacional recorrente.
- Manter local a camada de descoberta ampla por `profile`, sem depender de
  `subgroup` como entrada principal.
- Criar importacao idempotente dos catalogos locais validados para o Supabase,
  sem executar descoberta no runtime em nuvem.
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
- Tornar a publicacao do catalogo curado no Supabase uma operacao local
  explicita, validada, auditavel e idempotente.
- Modelar no Supabase catalogo, snapshots, estado de selecao, mensagens e
  tentativas de disparo.
- Criar view de ranking e elegibilidade com componentes e versao do score.
- Endurecer TLS da credencial Postgres do Supabase no n8n: substituir
  `Ignore SSL Issues (Insecure)` por validacao completa da cadeia via CA
  confiavel quando a UI/container permitir.
- Atualizar `offers.offer_selection_state` no MVP apos envio confirmado,
  registrando `selected_at`, `last_sent_at`, `cooldown_until` e
  `selection_count`, para evitar que a mesma oferta elegivel volte em loop em
  toda rodada.
- Implementar no Cloud Run geracao e disparo de mensagens sem incluir
  descoberta.
- Endurecer a operacao do n8n apos a primeira subida do MVP: revisar firewall
  sem bloquear SSH ou servicos Hostinger, fixar e atualizar a versao do
  Traefik, configurar backup externo com teste de restore e remover a stack
  legada depois do periodo de estabilizacao. Manter a porta `5678` restrita ao
  loopback; dominio, HTTPS e `N8N_WEBHOOK_URL` ja estao configurados.
- Avaliar aprovação operacional via WhatsApp, tratando o canal apenas como
  interface de decisão humana (aprovar/rejeitar/ajustar), com trilha de auditoria,
  idempotência e reconciliação posterior no fluxo local.

- Modelar depois uma camada de "produto equivalente / anuncios concorrentes"
  para comparar o mesmo item comercial vendido por lojas diferentes.
- Separar explicitamente a definicao do catalogo base da escolha de "anuncio
  vencedor", para nao travar a curadoria inicial por causa da competicao entre
  lojas.
- Criar criterio de anuncio vencedor com evidencias reais de tracao,
  equilibrando vendas, nota, preco, comissao, loja e estabilidade do anuncio.
- Evitar troca automatica para o menor preco ou para a maior comissao quando
  anuncios equivalentes mostrarem historico comercial muito diferente.

## Concluidos a partir da validacao operacional n8n

- Ajustado o workflow MVP do n8n para registrar `delivery_status=confirmed`
  somente depois de aceite do adapter WAHA. Evidencia: rodadas reais
  `grupo-real` com `endpoint=sendImage`, `send_result=sent_to_adapter`,
  `adapter_response_type=image` e `delivery_status=confirmed` nas execucoes
  `46`, `47`, `48` e `49`.
- Atualizado o JSON versionado do workflow `ofertas-mvp-supabase` para substituir
  os nodes `Set` que importaram com output vazio no n8n 2.32.6 por nodes `Code`
  equivalentes, preservando os nomes `Set Contexto MVP` e `Simular Envio MVP`.
- Ajustado `sent_at` no workflow MVP para permanecer `null` quando
  `dry_run=true`. Evidencia: rodada `dry-run` validada com
  `delivery_status=cancelled` e `send_result=dry_run_not_sent`, sem envio pelo
  adapter.

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
