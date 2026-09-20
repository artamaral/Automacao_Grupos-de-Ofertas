# Decisoes Tecnicas

## 2026-09-18 - Piso unico de rating para elegibilidade operacional

Decisao:

- alinhar a elegibilidade operacional do ranking para `rating >= 4.5`;
- substituir o motivo canonico de inelegibilidade por rating para
  `rating_below_4_5`;
- manter `rating >= 4.5` tambem no refresh comercial, evitando que a carga seja
  aceita no catalogo e bloqueada novamente por uma regra antiga de 4.8.

Motivo:

- remover a redundancia entre catalogo, ranking productCatId e refresh;
- preservar um unico corte operacional de qualidade para itens descobertos por
  `productCatId` e por `itemId`.

## 2026-09-10 - Origem operacional dos itens do catalogo

Decisao:

- adicionar `offers.catalog_items.selection_mode` com os valores
  `productCatId`, `user_defined` ou `NULL` para legado sem origem comprovada;
- tratar a origem como imutavel: redescobrir um item existente nao altera o
  modo pelo qual ele entrou no catalogo;
- classificar os 4.511 itens automaticos ativos como `productCatId`;
- classificar e ativar como `user_defined` os 311 itens do import manual
  `503a3436-7a36-41fb-9303-1aee43e8d978`;
- manter os demais itens `legacy` sem classificacao de origem;
- adiar a divisao das 140 vagas entre os dois modos para uma decisao posterior.

Motivo:

- permitir que o planner diferencie descoberta automatica por categoria de
  curadoria manual por `itemId`, sem inferir origem para o legado;
- tornar a carga manual candidata a planejamentos futuros sem alterar planos
  ja persistidos, matriz, ranking, n8n ou regras de despacho nesta etapa.

## 2026-09-01 - Descontinuar automacao propria de comentarios e DMs Instagram

Decisao:

- despublicar o workflow n8n `OfertasInstagramInteractionsSupab1`;
- parar o servico dedicado `instagram-webhook-verifier`;
- adotar a automacao nativa do Meta Business Suite para palavra-chave,
  resposta publica e DM;
- preservar codigo, workflow, testes e migracao como legado auditavel.

Motivo:

- a automacao nativa foi configurada manualmente e passa a ser o caminho
  operacional escolhido;
- o caminho proprio dependia de autorizacao de producao do app Meta para
  receber e responder a interacoes reais de contas externas;
- a decisao evita manter infraestrutura n8n e endpoint sem uso.

Impacto:

- os workflows existentes de publicacao Instagram, WhatsApp, planner, ranking
  e tracking permanecem fora deste escopo e nao foram alterados;
- a avaliacao de remocao das tabelas esta registrada no documento legado e
  requer migracao destrutiva separada, se aprovada.

Historico detalhado:

- `docs/legacy/instagram-comentarios-dm-n8n-2026-09-01.md`.

## 2026-09-01 - Resolver Instagram apos plano diario

Decisao:

- encadear `scripts/ops/run_instagram_media_resolver.sh` ao final de
  `scripts/ops/run_shopee_refresh_plan_tracking.sh`;
- executar a resolucao de midia Instagram somente depois de refresh,
  planejamento diario e geracao dos links rastreados;
- manter o resolver com seus parametros atuais, incluindo `MEDIA_LIMIT`,
  `--apply` e `--only-missing`.

Motivo:

- em `2026-09-01`, o timer isolado `instagram-media-resolver.timer` rodou as
  `07:30` BRT, mas o `daily_dispatch_plan` do dia so foi criado as `09:45:20`
  BRT; por isso o resolver processou `0` itens e o workflow Instagram nao teve
  candidatos Reels.

## 2026-08-31 - Instagram diario somente Reels

Decisao:

- manter o workflow existente `OfertasInstagramSupab1`, sem criar workflow,
  adapter, fila ou estrutura nova;
- fazer `offers.v_instagram_dispatch_ready` retornar somente
  `instagram_format='reels'` para itens com `video_url`;
- preservar os seis horarios diarios `10:00`, `12:00`, `14:00`, `16:00`,
  `18:00` e `20:00`;
- registrar novas publicacoes diarias apenas com
  `channel_adapter='instagram_reels'`;
- manter `instagram_carousel` como historico/legado fora do caminho diario.

Motivo:

- simplificar a operacao diaria do Instagram sem alterar planner, ranking,
  tracking, WhatsApp, cooldown ou coleta de videos;
- impedir fallback de produtos sem video para carrossel.

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

## 2026-09-18 - ProductCatId generico para descoberta manual por itemId

Decisao:

- criar a categoria operacional generica Shopee `999999` com o caminho
  `no_productcatId` em `offers.shopee_product_categories`;
- usar `productCatId=999999` somente para itens descobertos manualmente por
  `itemId` quando a API retorna apenas categorias que nao existem na taxonomia
  operacional do Supabase;
- manter `selection_mode='user_defined'` para essas cargas manuais;
- preservar o array original `productCatIds` retornado pela API no
  `source_payload` do snapshot/import para auditoria futura;
- nao usar `999999` na matriz automatica de quotas por `productCatId`.

Motivo:

- evitar descartar itens manuais validos por falta de uma categoria operacional
  singular no Supabase;
- manter os itens elegiveis para ranking manual sem inventar uma categoria real
  da Shopee;
- separar claramente origem manual (`user_defined`) de descoberta automatica por
  matriz (`productCatId`).

Limites:

- `999999` nao representa uma categoria oficial da Shopee;
- itens com rating abaixo de `4.5` continuam fora da carga;
- se a taxonomia operacional passar a conter uma categoria real aplicavel, ela
  deve substituir `999999` em cargas futuras.

## 2026-09-10 - Daily Dispatch híbrido por origem do catálogo

- O plano diário do perfil `feminino` continua com 140 vagas e mantém os
  horários e o sequenciamento existentes.
- A matriz habilitada de `productCatId` passa a ter 13 categorias e 78 vagas.
  As 62 vagas restantes são preenchidas por itens com
  `selection_mode='user_defined'`.
- O pool `productCatId` usa quotas por categoria e fallback global somente
  entre itens `selection_mode='productCatId'`.
- O pool `user_defined` usa o ranking comercial global e limita a seleção a
  três itens por `product_cat_id` no dia. Não há fallback entre os pools.
- O plano registra itens manuais com `selection_bucket='user_defined_rank'` e
  `selection_reason='user_defined:commercial_score'`.
- O refresh operacional prioriza cobertura dos dois pools antes da reserva.
  O wrapper e o timer da VPS permanecem os mesmos; a nova lógica entra em
  vigor após a atualização do checkout e será usada no próximo ciclo regular.
- Imports manuais futuros devem chamar `scripts/supabase/import_catalog.py`
  com `--selection-mode user_defined`; o valor só é atribuído a itens novos e
  não sobrescreve a origem de itens já cadastrados.
- O valor persistido para a origem automática permanece exatamente
  `productCatId`; não foi introduzido o alias `catid` no banco.

## 2026-09-20 - Falha de overlay Reels usa vídeo original

- Se o renderizador falhar, o fluxo não bloqueia a publicação.
- O Instagram recebe o `video_url` original da Shopee, sem overlay.
- O evento existente registra `render_status`, código e log sanitizado do
  erro, além de `overlay_applied=false` e
  `published_video_source='shopee_original'`.
- Não será adicionado retry no n8n para falha de submissão do job; essa regra
  permanece como fallback imediato para o vídeo original.

## 2026-09-20 - Primeira publicação real do Reels com renderer

- A primeira publicação produtiva controlada foi concluída na execução n8n
  `1164`, com um único item (`19997638584`) e template `1`.
- O renderer retornou MP4 com overlay, o container Instagram terminou em
  `FINISHED` e o media ID publicado foi `18170997604458269`.
- O n8n registrou `delivery_status=confirmed` e `publish_id`
  `e4523991-cef2-447e-a27f-a3ba06c9835a`.
- As 17 marcações observadas na execução anterior eram consultas de
  polling do mesmo job, não 17 Reels nem 17 publicações.
- O contexto manual deve carregar `instagram_business_account_id`; o
  restaurador de contexto também deve preservá-lo após a resposta do
  renderer para impedir URL `/null/media`.
- Valores textuais `None`, `null` e `undefined` em `primary_subniche` são
  normalizados para `ofertas` antes da geração da hashtag.
