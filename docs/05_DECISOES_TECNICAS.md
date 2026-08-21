# Decisoes Tecnicas

## 2026-08-21 - Skill local para mensagens estaticas do grupo feminino

Decisao:

- instalar localmente a skill `grupo-ofertas-femininas-msg-estaticas-v2` em
  `C:\Users\arthu\.codex\skills\grupo-ofertas-femininas-msg-estaticas-v2`;
- ativar a skill quando o usuario chamar explicitamente
  `grupo-ofertas-femininas-msg-estaticas-v2` ou usar o prefixo
  `/ofertas-femininas`;
- usar a skill para preparar pastas `msg_XXX` com os nomes fixos `copy.txt` e
  `image.jpg`;
- manter a pasta oficial do Google Drive como destino operacional do fluxo:
  `ofertas-femininas`;
- quando o Google Drive nao estiver acessivel em uma etapa pontual, permitir
  gravacao temporaria local apenas como fallback operacional solicitado pelo
  usuario.

Motivo:

- reduzir erro manual na preparacao das mensagens estaticas consumidas pelo
  n8n;
- preservar o contrato fixo do workflow, que espera `copy.txt` e `image.jpg`;
- separar a preparacao dos arquivos do envio WhatsApp, que continua sob
  responsabilidade do n8n.

Limites:

- a skill nao envia WhatsApp;
- a skill nao modifica o workflow n8n;
- a URL normal do produto e usada apenas para extracao e validacao;
- a URL afiliada e a unica URL permitida na copy final;
- nao sobrescrever pastas `msg_XXX` existentes sem autorizacao explicita.

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
