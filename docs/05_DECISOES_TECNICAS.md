# Decisoes Tecnicas

## 2026-08-30 - Catalogo feminino por ProductCatId singular

Decisao:

- usar somente o `productCatId` singular definido no request como categoria
  operacional do novo catalogo feminino;
- manter `productCatIds`, retornado pela Shopee, fora de classificacao,
  persistencia operacional, ranking, refresh, planner e fila;
- adotar uma unica tabela persistente de catalogo, com status `current` e
  `legacy`, promovendo novamente para `current` qualquer item legacy encontrado
  no catalogo novo;
- usar a matriz canonica de 53 categorias e quotas que somam 140 itens por dia;
- integrar o planner de `productCatId` fornecido pelo usuario e preservar a
  grade atual de 14 janelas, das 08h as 21h;
- quando uma categoria da matriz nao tiver candidatos aptos suficientes,
  completar a lacuna com os melhores candidatos gerais disponiveis, mantendo
  `selection_bucket='productcatid_exact'` e auditando o desvio em
  `selection_reason='productcatid:<id>:top_score_fallback'`;
- alterar o piso de elegibilidade de rating de 4.8 para 4.5 e manter os termos
  proibidos como unico filtro semantico textual;
- executar o cutover somente depois das 21h BRT, como ultima etapa, sem alterar
  o plano encerrado do dia e sem hard delete de catalogo ou snapshots;
- propagar `product_cat_id` ate `v_daily_dispatch_ready_tracked`, preservando
  tracking, copy, cooldown, allowlist, claim e idempotencia existentes.

Motivo:

- assumir a taxonomia oficial Shopee como fonte canonica e remover a
  classificacao dos novos itens por taxonomia interna;
- manter o restante da operacao comercial e de publicacao no estado atual;
- permitir segregacao, auditoria, refresh forcado e rollback controlado no
  cutover.

Contrato detalhado:

- `docs/projeto/12-spec-catalogo-productcatid-shopee.md`.

## 2026-08-27 - Publicacao controlada do workflow Instagram

Decisao:

- publicar a versao de producao de `OfertasInstagramSupab1` somente apos seis
  entregas manuais confirmadas no ledger, tres Reels e tres Carrosseis;
- manter a ativacao do agendamento separada da comprovacao de entrega: o
  workflow foi publicado, mas o processo n8n ainda precisa ser reiniciado para
  carregar o cron ativo;
- nao alterar o workflow WhatsApp, migrations pendentes fora do escopo ou a
  regra de selecao editorial nesta etapa.

Motivo:

- os eventos confirmados provaram a alternancia Reel/Carrossel, o polling de
  container e o registro no ledger sem reutilizar o mesmo plano de despacho;
- o aviso do CLI torna o reinicio uma dependencia tecnica real para a
  ativacao do scheduler, e nao apenas uma formalidade documental.

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
