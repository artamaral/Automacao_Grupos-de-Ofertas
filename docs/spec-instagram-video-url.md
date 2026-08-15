# Spec: post Instagram a partir de video_url

## Objetivo

Criar uma etapa de enriquecimento para posts de Instagram/Reels usando a mesma
base operacional da copy WhatsApp. O sistema deve localizar a URL publica do
video do anuncio Shopee, persistir esse metadado no Supabase e deixar o n8n
consumir apenas itens ja prontos.

Esta spec nao altera o fluxo WhatsApp vigente.

## Fluxo proposto

1. **Fonte da oferta**

   Usar o mesmo item da fila/catalogo: `profile`, `marketplace`, `item_id`,
   `shop_id`, `product_link`, `offer_link`, `image_url` e `message_text`.

2. **Resolucao de midia**

   Um script Python na VPS resolve o HTML do produto Shopee e procura URLs
   publicas de imagens e video. A entrada principal deve ser o
   `product_link` canonico (`https://shopee.com.br/product/<shop_id>/<item_id>`).
   O `offer_link` encurtado continua sendo usado na copy e no link afiliado,
   mas nao deve ser a fonte primaria do scrape de midia.

3. **Validacao**

   Antes de persistir, validar a URL com requisicao leve (`HEAD` ou `GET`
   parcial), confirmando status de sucesso, dominio permitido e tipo de
   conteudo compativel com video.

4. **Persistencia**

   Persistir apenas URLs e metadados, sem baixar ou armazenar arquivos de
   imagem/video. Para o MVP, usar tabela separada, mas simples: uma linha por
   item resolvido.

   ```text
   offers.offer_media_assets
     profile
     marketplace
     item_id
     shop_id
     product_link
     image_urls jsonb
     video_url
     source = 'shopee_product_html'
     status
     resolved_at
     last_checked_at
     error_detail
   ```

   Decisao MVP: nao criar uma linha por imagem/video nesta etapa. A lista de
   imagens fica em `image_urls`, preservando a ordem da galeria. O video
   principal fica em `video_url`. Se no futuro precisarmos auditar status,
   content-type ou falha por asset individual, esta tabela pode evoluir para
   uma estrutura normalizada.

5. **Consumo pelo n8n Instagram**

   O n8n consulta somente itens com `video_url` valido e usa essa URL para
   criar o container de publicacao no Instagram. O n8n nao deve raspar HTML,
   decidir ranking, baixar video nem reprocessar midia.

## Nichos do teste controlado

Para a primeira rodada controlada, usar ate 3 posts por dia, nesta ordem:

1. `maquiagem-geral`
2. `skincare-facial`
3. `acessorios-femininos`

Horarios fixos da rodada:

- `10:00` BRT: primeiro post elegivel;
- `14:00` BRT: segundo post elegivel;
- `18:00` BRT: terceiro post elegivel.

Se algum nicho nao tiver item elegivel com `video_url` valido, aplicar fallback
pela ordem ja disponivel em `offers.daily_dispatch_plan`, preservando a
ordenacao materializada pelo planejador (`planned_date`, `planned_hour`,
`slot_sequence` e `daily_sequence`). O resolvedor de midia nao deve recalcular
score, diversidade ou prioridade.

Adicionar tambem 1 carrossel diario para moda, separado da selecao de Reels.
Esse post deve recuperar as midias do anuncio na ordem em que aparecem,
validar as URLs e publicar nessa mesma ordem ate o limite permitido pelo
Instagram. Se houver tabela de tamanhos entre as imagens do anuncio, ela entra
junto sem classificacao especial. Se nao houver item de moda com midias
validas, aplicar fallback pela ordem ja materializada em
`offers.daily_dispatch_plan`.

## Contrato minimo para Instagram

- a conta/canal Instagram do MVP usa o email operacional
  `grupodeofertas.mktdigital.fem@gmail.com`;
- `video_url` deve estar publica no momento da publicacao.
- `caption` pode reutilizar a copy ja montada, com ajustes especificos para
  Instagram quando necessario.
- se a URL expirar, bloquear o post e marcar a midia como `stale` ou `failed`.
- se nao houver video, o item pode ficar inelegivel para Instagram/Reels ou
  cair para fluxo futuro de imagem, fora desta spec.

## Copy para Reels

A legenda do Reel deve ser curta e direta, sem titulo separado. O emoji inicial
entra na primeira frase da descricao.

Template:

```text
🔥 [descricao curta com produto + beneficio]

💸 [preco] hoje
⭐ [avaliacao]/5 na Shopee

💬 Quer receber mais ofertas assim?
Entre no grupo do WhatsApp: [whatsapp_group_url]

⚠️ Preco e disponibilidade podem mudar.
#ad #shopee #[hashtag_nicho] #achadinhos
```

Regras:

- nao usar titulo como "Achado de maquiagem na Shopee";
- nao repetir "preco" ou "avaliacao" depois dos emojis;
- `whatsapp_group_url` e configuracao do canal/perfil, separada de
  `offer_link` e `coupon_url`;
- a descricao deve explicar o produto e o beneficio em uma frase curta;
- hashtags devem refletir o nicho/subnicho do item quando disponivel.

## Alternativa: carrossel Instagram

Quando o anuncio nao tiver video adequado, ou quando o formato de multiplas
midias for preferivel, o fluxo pode publicar um carrossel.

As imagens do carrossel tambem dependem de resolucao automatica via HTML do
anuncio. A base afiliada (`productOfferV2`) entrega somente `imageUrl`
principal; ela nao informa, de forma confiavel, se existe tabela de tamanhos ou
quais imagens secundarias merecem entrar no post.

Contrato de midia MVP:

```text
offers.offer_media_assets
  profile
  marketplace
  item_id
  shop_id
  product_link
  image_urls jsonb
  video_url
  status
  resolved_at
  last_checked_at
  error_detail
```

A tabela e separada do catalogo para manter clara a fronteira entre dado
comercial da oferta e midia resolvida para Instagram, mas permanece simples:
uma linha por item. A ordem do carrossel vem da ordem dos itens dentro de
`image_urls`.

Regras para carrossel:

- usar ate 10 midias por post;
- permitir imagens e videos no mesmo carrossel quando ambos forem resolvidos e
  validados;
- recuperar as midias na ordem em que aparecem no anuncio;
- preservar essa ordem no carrossel;
- validar cada imagem antes de criar o container;
- validar cada video antes de criar o container, quando video entrar no
  carrossel;
- nao baixar nem versionar imagens ou videos nesta etapa.

Publicacao pelo Instagram:

1. criar um container filho por imagem ou video com `is_carousel_item=true`;
2. usar `image_url` para imagens e `video_url` + tipo de midia compativel para
   videos;
3. criar o container pai com `media_type=CAROUSEL`, `children` e `caption`;
4. publicar o container pai.

O resolvedor de midia deve entregar uma lista pronta de imagens; o n8n nao deve
raspar HTML nem decidir quais imagens procurar.

## Resolvedor Shopee atual

O script implementado para a primeira validacao e:

```text
src/ofertas_bot/tools/scrape_shopee_media.py
```

Ele usa somente Python stdlib, portanto pode rodar na VPS sem navegador
headless e sem dependencias extras. A funcao do script e resolver a pagina do
produto Shopee, extrair URLs publicas de midia e salvar um CSV com metadados.
Ele nao baixa imagens nem videos.

Comando manual:

```powershell
python -m ofertas_bot.tools.scrape_shopee_media --url "https://shopee.com.br/product/296735539/7282718770" --output tmp/shopee-media.csv
```

Campos do CSV:

```text
scraped_at
source_url
item_id
shop_id
media_type
position
media_url
status
http_status
content_type
content_length
error_detail
```

### Como identifica as midias

1. Normaliza o HTML:
   remove escapes comuns (`\/`), aplica `html.unescape` e resolve escapes
   unicode simples. Isso permite ler URLs e IDs de imagem que aparecem dentro
   de JSON embutido no HTML.

2. Delimita o produto:
   usa `item_id` e, quando disponivel, `shop_id` para procurar blocos do HTML
   relacionados ao produto certo. Isso evita capturar midias de recomendacoes,
   produtos parecidos ou outros blocos da pagina.

3. Imagens:
   - quando existe o bloco renderizado `div role="main" class="container"` com
     `div class="flex card vr0998"`, usa esse card como fonte da galeria;
   - quando o card renderizado nao aparece no HTML inicial, usa os arrays JSON
     do produto;
   - ignora arrays de `tier_variations`, pois eles representam variacoes de
     cor/modelo e podem inflar a galeria;
   - considera `images` como galeria principal quando ela representa o conjunto
     visual do produto;
   - considera `long_images` como galeria de detalhe quando a Shopee separa as
     fotos principais/detalhes nesse campo;
   - quando `images` tem apenas uma imagem e existe `long_images`, usa
     `long_images` como galeria efetiva;
   - quando `images` parece ser variacao e `long_images` tem a galeria
     validada visualmente, usa `long_images`;
   - preserva a ordem em que as imagens aparecem no bloco escolhido.

4. Video:
   - procura URLs `.mp4` em blocos do produto, especialmente
     `video_info_list`;
   - tambem aceita o `<video class="QODm2C exqDJH" src="...mp4">` quando esse
     elemento aparece no HTML renderizado;
   - limita a dominios permitidos da Shopee/Shopee CDN, como
     `*.susercontent.com`, `*.susercontent.com.br` e `*.shopee.com.br`;
   - deduplica variantes do mesmo video, como `.default.mp4` e
     `.<timestamp>.mp4`, preservando a primeira URL encontrada.

5. Ordenacao de saida:
   imagens saem primeiro, na ordem da galeria escolhida. Videos saem depois.
   Isso facilita o uso direto em carousel e tambem permite selecionar o video
   para Reels.

6. Validacao:
   para cada URL, faz uma requisicao leve com `Range: bytes=0-0`. A URL so fica
   como `valid` quando retorna status HTTP de sucesso e `Content-Type`
   compativel com o tipo esperado (`image/*` ou `video/*`).

### Validacao manual inicial

O script foi testado em 25 itens da lista diaria local de `2026-08-15`.
Resultado apos ajustes de heuristica:

```text
base 7282718770: 9 imagens + 1 video
33: 5 imagens + 1 video
34: 6 imagens + 1 video
36: 5 imagens + 1 video
38: 8 imagens + 1 video
40: 7 imagens + 0 video
41-60: todos com video; contagens entre 3 e 9 imagens
```

Os CSVs de validacao ficaram em:

```text
tmp/shopee-media-7282718770-final.csv
tmp/shopee-media-batch-2026-08-15-product-links/
tmp/shopee-media-batch-2026-08-15-next-20/
```

Conclusao operacional: para o MVP, o resolvedor deve receber `product_link`
como fonte do scrape e persistir apenas as URLs/metadados. O `offer_link`
encurtado deve continuar separado para atribuicao afiliada e CTA.

## Persistencia MVP

O desenho escolhido e usar uma tabela separada e simples:

```text
offers.offer_media_assets
```

Granularidade:

```text
1 linha por profile + marketplace + item_id
```

Campos previstos:

```text
profile
marketplace
item_id
shop_id
product_link
image_urls jsonb
video_url text
status text
resolved_at timestamptz
last_checked_at timestamptz
error_detail text
```

Status iniciais:

```text
valid     -- tem pelo menos uma imagem valida ou um video valido
no_media  -- scrape executou, mas nao encontrou midia util
failed    -- erro de scrape ou validacao
stale     -- midia resolvida anteriormente falhou em revalidacao futura
```

Regras de consumo:

- Reels: `status = 'valid'` e `video_url is not null`;
- Carrossel: `status = 'valid'` e `jsonb_array_length(image_urls) > 0`;
- n8n nao consulta CSV, nao raspa HTML e nao recalcula selecao;
- CSV continua sendo artefato temporario de validacao/debug.

## Plano de implementacao

### A. Criar tabela `offer_media_assets`

Criar a tabela simples de midia resolvida no schema `offers`, separada do
catalogo comercial.

Entrega esperada:

- migration SQL;
- chave unica por `profile + marketplace + item_id`;
- coluna `image_urls jsonb` para a lista ordenada de imagens;
- coluna `video_url text` para o video principal, quando houver;
- colunas operacionais `status`, `resolved_at`, `last_checked_at` e
  `error_detail`;
- indices para consulta por `profile`, `marketplace`, `status` e
  `last_checked_at`.

### B. Criar persistencia real no Supabase

Adaptar a saida do resolvedor para gravar no Supabase em vez de depender de
CSV.

Entrega esperada:

- store/repository Python para upsert em `offers.offer_media_assets`;
- conversao de `MediaAsset` para `image_urls` e `video_url`;
- consolidacao de status por item;
- idempotencia no upsert;
- `dry-run` como padrao, com `--apply` para escrita real.

### C. Criar script em lote para itens do `daily_dispatch_plan`

O scraper unitario ja existe. Este ponto cria a camada de lote que busca itens
planejados e chama o scraper atual para cada `product_link`.

Entrega esperada:

- CLI de lote;
- leitura de itens por `profile`, `marketplace`, `planned_date` e `limit`;
- uso de `product_link` como fonte do scrape;
- opcao `--only-missing` para evitar reprocessamento desnecessario;
- resumo final com processados, validos, com video, somente imagem, sem midia e
  falhas;
- CSV opcional apenas para debug.

### D. Criar view/query de midia pronta para n8n

Criar uma consulta estavel para o n8n consumir somente itens ja enriquecidos e
validos.

Entrega esperada:

- view ou query documentada juntando plano diario + midia resolvida;
- campos minimos para o n8n: `dispatch_plan_id`, `item_id`, `product_name`,
  `offer_link`, `image_urls`, `video_url`, `caption`, `planned_hour`;
- filtro de `status = 'valid'`;
- filtro especifico para Reels quando exigir `video_url is not null`;
- filtro especifico para Carrossel quando exigir imagens;
- ordenacao preservando `planned_date`, `planned_hour`, `slot_sequence` e
  `daily_sequence`.

### E/F. Criar workflow unico n8n Instagram

Criar apenas um workflow n8n para Instagram, com nodes separados para Reels e
Carrossel. A selecao e preparacao continuam fora do n8n; o workflow so consome
itens prontos.

Fluxo do workflow:

```text
Trigger horario
  -> buscar proximo item pronto no Supabase
  -> validar allowlist/config do canal Instagram
  -> revalidar midia
  -> IF formato = reels
       -> nodes Reels
     ELSE IF formato = carousel
       -> nodes Carrossel
  -> checar status do container
  -> publicar
  -> registrar resultado em publication_events
```

Nodes Reels:

- montar payload com `media_type=REELS`;
- usar `video_url`;
- aplicar caption de Reels;
- criar container;
- consultar status do container ate `FINISHED`;
- publicar container.

Nodes Carrossel:

- limitar `image_urls` a ate 10 midias;
- criar containers filhos com `is_carousel_item=true`;
- criar container pai com `media_type=CAROUSEL`;
- aplicar caption;
- consultar status do container pai ate `FINISHED`;
- publicar container pai.

### G. Revalidar midia antes da publicacao

Antes de criar container no Instagram, o n8n deve confirmar que as URLs ainda
estao acessiveis.

Entrega esperada:

- request leve para `video_url` e/ou `image_urls`;
- confirmacao de HTTP sucesso;
- confirmacao de `Content-Type` compativel;
- bloqueio do item quando a URL falhar;
- atualizacao do status da midia no Supabase.

Decisao MVP: nao criar etapa de rascunho visivel no Instagram. Como nao ha base
de seguidores nem trafego pago neste momento, vamos aprender com publicacao
controlada e validacao automatica.

### H. Registrar falhas de midia expirada

Quando a revalidacao falhar, registrar a falha sem tentar publicar.

Entrega esperada:

- atualizar `offers.offer_media_assets.status` para `stale` ou `failed`;
- preencher `last_checked_at`;
- preencher `error_detail`;
- registrar evento de falha em `offers.publication_events`;
- liberar o fluxo para tentar outro item elegivel, se houver.

### I. Testar criacao real de container Instagram

Validar a primeira integracao real com a API do Instagram sem publicar de forma
automatica em massa.

Entrega esperada:

- teste controlado com 1 Reel;
- teste controlado com 1 Carrossel;
- criacao de container;
- consulta de status do container;
- publicacao somente se o container retornar `FINISHED`;
- registro dos IDs retornados pela API.

### J. Registrar publicacao/falha em `publication_events`

Toda tentativa do workflow Instagram deve gerar evidencia operacional, assim
como no fluxo WhatsApp.

Entrega esperada:

- registrar tentativa antes/depois da chamada externa, conforme padrao atual;
- registrar canal/formato: `instagram_reels` ou `instagram_carousel`;
- registrar `dispatch_plan_id`, `item_id`, status, erro e resposta resumida da
  API;
- diferenciar container criado, publicacao confirmada, falha de validacao e
  falha de publicacao;
- nao tratar sucesso do n8n como prova unica de publicacao.

## Resolvedor em lote

O scraper unitario ja existe e resolve midias a partir de um `product_link`.
O proximo passo nao e criar outro scraper, mas criar uma camada de lote com
leitura do plano diario e escrita no Supabase.

Nome sugerido do comando:

```powershell
python -m ofertas_bot.tools.resolve_instagram_media_batch --profile feminino --marketplace shopee --date 2026-08-15 --limit 20 --dry-run
```

Fluxo esperado:

```text
offers.daily_dispatch_plan / offers.v_daily_dispatch_ready
  -> selecionar itens candidatos
  -> obter product_link canonico
  -> chamar scrape_shopee_media para cada item
  -> transformar resultado em image_urls + video_url
  -> upsert em offers.offer_media_assets
  -> emitir resumo operacional
```

### Alterar

- ajustar o script atual para expor uma funcao reutilizavel que retorne o
  resultado em memoria, nao apenas CSV;
- manter a escrita em CSV como opcional para debug/validacao manual;
- garantir que o resolvedor aceite `product_link` como fonte principal;
- manter `offer_link` fora do scrape, usando-o apenas para copy/CTA;
- transformar a lista de assets em:
  - `image_urls`: array ordenado das imagens validas;
  - `video_url`: primeiro video valido, quando existir;
  - `status`: status consolidado do item;
  - `error_detail`: erro consolidado, quando houver;
- preservar modo `dry-run` como padrao operacional seguro.

### Criar

- migration SQL para `offers.offer_media_assets`;
- store/repository Supabase para upsert da midia resolvida;
- CLI/job de lote para processar itens do dia;
- consulta de entrada usando `profile`, `marketplace`, `planned_date` e limite;
- filtro `--only-missing` para evitar reprocessar itens com midia recente;
- filtro opcional por nicho/subnicho quando o teste controlado de Instagram
  exigir;
- relatorio final do lote com:
  - itens processados;
  - itens com video;
  - itens apenas com imagens;
  - itens sem midia;
  - itens com erro;
  - total de imagens validas;
- testes unitarios do mapeamento `MediaAsset -> offer_media_assets`;
- teste do modo `dry-run`, garantindo que nao escreve no banco;
- teste do upsert, garantindo idempotencia por
  `profile + marketplace + item_id`.

### Parametros minimos

```text
--profile
--marketplace
--date
--limit
--dry-run / --apply
--only-missing
--output
```

### Regras de status consolidado

```text
valid     -- tem pelo menos uma imagem valida ou um video valido
no_media  -- scrape executou, mas nao encontrou imagem nem video valido
failed    -- erro de acesso, parse ou validacao
stale     -- midia existente falhou em revalidacao futura
```

### Saida esperada do lote

Mesmo quando escrever no Supabase, o job deve emitir um resumo legivel:

```text
processed=20
valid=20
with_video=20
image_only=0
no_media=0
failed=0
```

O CSV permanece util para auditoria manual, mas nao deve ser dependencia do
n8n.

## Operacao na VPS

O resolvedor deve rodar fora do n8n, preferencialmente antes da janela de
publicacao Instagram. Ele pode ser executado por comando manual no MVP:

```powershell
python -m ofertas_bot.tools.scrape_shopee_media --url "https://shopee.com.br/product/296735539/7282718770" --output tmp/shopee-media.csv
```

Depois, pode evoluir para lote dos itens planejados para Instagram.

## Criterios de aceite

- o item Shopee existente e localizado por `profile + marketplace + item_id`;
- a URL `.mp4` e encontrada sem baixar o video completo;
- a URL e validada antes de persistir;
- o Supabase guarda apenas metadados e URL;
- o n8n Instagram consome somente midia ja resolvida;
- falhas de resolucao nao afetam a fila WhatsApp.

## Fora de escopo

- publicar automaticamente no Instagram nesta primeira etapa;
- baixar, editar, transcodificar ou hospedar o video;
- usar cookies, sessoes, QR codes ou credenciais de navegador;
- colocar scraper ou regras de selecao dentro do n8n;
- alterar cooldown ou historico de publicacao WhatsApp.

## Commit sugerido

```text
docs(media): especifica video_url para instagram
```
