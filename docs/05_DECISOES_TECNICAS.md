# Decisoes Tecnicas

## 2026-08-15 - Instagram Shopee usa midia resolvida no Supabase

Decisao:

- criar `offers.offer_media_assets` como tabela separada e simples, com uma
  linha por `profile + marketplace + item_id`;
- persistir apenas URLs e metadados, sem baixar arquivos;
- expor `offers.v_instagram_dispatch_ready` como superficie pronta para n8n;
- manter o workflow Instagram separado do workflow WhatsApp;
- usar um unico workflow Instagram com ramificacoes para Reels e Carrossel;
- registrar tentativas, confirmacoes e falhas em `offers.publication_events`.

Motivo:

- preservar o Supabase como fonte operacional;
- manter n8n como consumidor de dados prontos;
- evitar que scraping, ranking ou selecao entrem no workflow;
- permitir teste real controlado sem alterar o fluxo WhatsApp vigente.

Limites:

- o workflow versionado comeca `active=false`;
- credenciais, tokens, cookies, QR codes e sessoes ficam fora do Git;
- `delivery_status` continua limitado a `confirmed`, `failed` e `cancelled`;
- estados intermediarios da Instagram Graph API entram em `payload`.
