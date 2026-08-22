# Reconciliacao de migrations Instagram

## Contexto

Na VPS, o schema efetivo do Supabase ja continha `offers.offer_media_assets` e
as colunas mais recentes de `offers.v_instagram_dispatch_ready`, mas
`offers.schema_migrations` nao registrava algumas migrations historicas.

O runner sequencial tentou executar novamente
`202608150003_instagram_media_ready_view.sql`. Essa versao antiga da view nao
contem colunas introduzidas por migrations posteriores; o PostgreSQL bloqueou a
operacao com `cannot drop columns from view`. A execucao foi transacional e nao
alterou o banco.

## Regra operacional

Nao reaplicar migrations historicas somente porque estao ausentes do historico.
Antes, verificar se seu efeito material ja existe no schema. Quando comprovado,
registrar somente essas migrations com o checksum do arquivo versionado. A
reconciliacao nao executa o SQL historico.

Para este caso, a validacao exige:

- tabela `offers.offer_media_assets` com o contrato de midia resolvida;
- `offers.v_instagram_dispatch_ready` com os campos de observabilidade da
  versao desacoplada do WhatsApp;
- `offers.v_daily_dispatch_ready` com os campos de freshness operacional.

Depois da reconciliacao, o runner versionado pode aplicar somente a migration
realmente nova `202608220001_instagram_reels_carousel.sql`.

## Isolamento WhatsApp

Eventos Instagram nao devem usar `publication_events.dispatch_plan_id`, pois o
trigger desse campo sincroniza `daily_dispatch_plan` para o fluxo WhatsApp.
O workflow Instagram registra a origem em `payload.source_dispatch_plan_id` e
a migration nova cria idempotencia parcial por formato Instagram e origem.
