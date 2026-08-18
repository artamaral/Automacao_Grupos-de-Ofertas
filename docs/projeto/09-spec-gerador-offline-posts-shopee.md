# Spec — Gerador Offline de Posts a partir de URL Shopee

## 1. Objetivo

Criar uma ferramenta local que receba uma URL de produto da Shopee e gere materiais prontos para publicação manual em redes sociais.

O sistema **não publica automaticamente**. Ele apenas gera os arquivos necessários para upload manual.

Formatos suportados inicialmente:

- Reels;
- Carrossel;
- Story;
- todos os formatos em uma única execução.

## 2. Entradas

### 2.1 Entrada obrigatória

URL de produto Shopee, completa ou curta:

```text
https://shopee.com.br/...
https://s.shopee.com.br/...
```

### 2.2 Flags de formato

```text
--reels
--carousel
--story
--all
```

Exemplos:

```powershell
python -m ofertas_bot.post_from_url "URL_SHOPEE" --reels
python -m ofertas_bot.post_from_url "URL_SHOPEE" --carousel
python -m ofertas_bot.post_from_url "URL_SHOPEE" --story
python -m ofertas_bot.post_from_url "URL_SHOPEE" --all
```

`--all` equivale a `--reels --carousel --story`.

### 2.3 Flags opcionais

```text
--output <diretorio>
--preview
```

## 3. ProductData

A URL deve ser resolvida para um objeto normalizado `ProductData` com, quando disponíveis:

```text
marketplace
shop_id
item_id
title
price
old_price
discount_pct
images
video
product_url
affiliate_url
sales
rating
```

O mesmo `ProductData` deve alimentar todos os formatos para evitar divergências de preço, desconto, título, mídia e URL de afiliado.

## 4. Copy existente do projeto

### 4.1 Fonte de verdade

Para **Reels e Carrossel**, esta funcionalidade não deve implementar um novo sistema de geração de copy.

As referências oficiais já existentes são:

- [`src/ofertas_bot/agents/copywriter.py`](../../src/ofertas_bot/agents/copywriter.py)
- [`docs/copy-guidelines.md`](../copy-guidelines.md)
- [`tests/test_copywriter.py`](../../tests/test_copywriter.py)
- template Shopee atual: [`config/message_templates/shopee.txt`](../../config/message_templates/shopee.txt)

O gerador offline deve reutilizar a saída do mecanismo de copy existente em vez de duplicar ou reimplementar suas regras.

Os generators não devem criar lógica paralela para:

- formatação de preço;
- preço anterior;
- percentual de desconto;
- disclosure/aviso de anúncio ou afiliado;
- estrutura da mensagem base.

A documentação atual registra, entre outras regras, a linha de preço:

```text
Preço: de R$ 89.90 por R$ 49.90 (44% OFF)
```

quando existe `old_price > price`, e:

```text
Preço: R$ 49.90
```

quando não existe preço anterior válido.

Para Shopee, o caminho operacional atual também utiliza o template estático versionado em `config/message_templates/shopee.txt`.

### 4.2 Fluxo da copy

```text
ProductData
    ↓
Copywriter / template existente
    ↓
GeneratedCopy
    ↓
ReelGenerator / CarouselGenerator
```

Qualquer alteração futura nas regras oficiais de copy deve refletir automaticamente no gerador offline.

### 4.3 Exceção — Story

Story possui necessidade específica de texto curto e visual.

O `StoryGenerator` pode gerar textos visuais derivados diretamente do `ProductData`, por exemplo:

```text
ACHADINHO 🔥

de R$ 89,90
por R$ 49,90

44% OFF

👇 COMPRE AQUI 👇
```

Essa lógica é **copy visual de Story**, não substituição do mecanismo principal de copy.

## 5. Fluxo de processamento

```text
                    ┌→ Copy existente → ReelGenerator
URL → ProductData ──┼→ Copy existente → CarouselGenerator
                    └→ StoryGenerator
```

Fluxo detalhado:

```text
URL Shopee
    ↓
ProductResolver
    ↓
ProductData
    ↓
AffiliateLinkResolver
    ↓
Copywriter/template existente
    ↓
ReelGenerator / CarouselGenerator

ProductData
    ↓
StoryGenerator
    ↓
Story Copy + Layout + Affiliate URL
```

## 6. Saída geral

```text
output/
  <produto_id>/
    metadata.json

    reels/
      reel.mp4
      cover.jpg
      caption.txt

    carousel/
      01.jpg
      02.jpg
      03.jpg
      04.jpg
      caption.txt

    story/
      story.jpg
      link.txt
      instructions.txt

    preview.html
```

Somente os formatos solicitados devem ser gerados.

## 7. Reels

### Entrada

- `ProductData`;
- `GeneratedCopy` proveniente do mecanismo de copy existente;
- imagens e/ou vídeo do produto.

### Saída

```text
reel.mp4
cover.jpg
caption.txt
```

Formato:

```text
1080 x 1920
9:16
```

Regras:

- `caption.txt` deve ser derivado da copy oficial existente;
- o `ReelGenerator` não deve criar uma segunda legenda independente;
- textos sobrepostos ao vídeo podem ser resumos visuais de `ProductData`;
- priorizar vídeo do produto quando disponível;
- sem vídeo, permitir composição a partir de imagens estáticas com movimentos/transições.

Estrutura audiovisual sugerida:

```text
0–2s   Hook visual
2–6s   Produto
6–10s  Preço
10–13s Desconto
13–15s CTA
```

## 8. Carrossel

### Entrada

- `ProductData`;
- `GeneratedCopy` proveniente do mecanismo de copy existente;
- imagens do produto.

### Saída

```text
01.jpg
02.jpg
03.jpg
04.jpg
caption.txt
```

Regras:

- `caption.txt` deve usar a copy oficial existente;
- os cards podem usar informações resumidas de `ProductData`;
- o texto visual dos cards não deve duplicar a lógica da legenda.

Estrutura sugerida:

```text
Card 1: Hook + produto
Card 2: Preço + desconto
Card 3: Características / benefícios disponíveis
Card 4: CTA
```

O número de cards pode variar conforme o conteúdo disponível.

## 9. Story

### Entrada

- `ProductData`;
- `affiliate_url`;
- imagem do produto.

### Saída

```text
story.jpg
link.txt
instructions.txt
```

Formato:

```text
1080 x 1920
9:16
```

A arte deve conter, quando disponível:

- hook;
- imagem do produto;
- preço atual;
- preço anterior;
- desconto;
- CTA;
- área reservada para o Link Sticker.

Exemplo conceitual:

```text
┌─────────────────────────┐
│       ACHADINHO 🔥      │
│                         │
│        PRODUTO          │
│                         │
│ de R$ 89,90             │
│ por R$ 49,90            │
│                         │
│       44% OFF           │
│                         │
│   👇 COMPRE AQUI 👇     │
│                         │
│ [ ÁREA LINK STICKER ]   │
└─────────────────────────┘
```

### Link clicável

O link clicável não é incorporado ao JPG ou MP4.

O sistema deve gerar `story/link.txt` contendo apenas a URL de afiliado:

```text
https://s.shopee.com.br/XXXXXXXX
```

Na publicação manual do Story, o usuário adiciona essa URL por meio do Link Sticker da plataforma.

`instructions.txt` deve registrar essa instrução operacional.

## 10. Metadata

Gerar `metadata.json` com os dados utilizados para criar os materiais.

Exemplo:

```json
{
  "marketplace": "shopee",
  "shop_id": "1252993709",
  "item_id": "21997761426",
  "title": "Casaco Teddy com Capuz",
  "price": 49.90,
  "old_price": 89.90,
  "discount_pct": 44,
  "affiliate_url": "https://s.shopee.com.br/xxxx",
  "formats": ["reels", "carousel", "story"]
}
```

## 11. Preview local

Com `--preview`, gerar `preview.html`.

O preview deve permitir:

- visualizar Reel, Carrossel e Story;
- copiar legenda;
- copiar link;
- abrir imagem;
- abrir vídeo.

Para Reels e Carrossel, a legenda exibida deve vir da mesma fonte oficial de copy usada pelo restante do projeto.

O preview não deve publicar conteúdo nem enviar dados para redes sociais.

## 12. Recursos necessários

### 12.1 Componentes existentes a reutilizar

Fonte de verdade:

```text
src/ofertas_bot/agents/copywriter.py
docs/copy-guidelines.md
tests/test_copywriter.py
config/message_templates/shopee.txt
```

Não criar um segundo sistema de copy.

### 12.2 Integração Shopee

Necessário mecanismo para:

- resolver URL curta e completa;
- identificar `shop_id` e `item_id`;
- obter dados do produto;
- obter preço e preço anterior;
- obter imagens;
- obter vídeo, quando disponível;
- gerar ou recuperar `affiliate_url`.

### 12.3 Processamento de imagem

Biblioteca sugerida: `Pillow`.

Responsabilidades:

- resize e crop;
- composição;
- textos e overlays;
- cards;
- Story;
- cover.

### 12.4 Processamento de vídeo

Sugestão: `FFmpeg`, opcionalmente `MoviePy`.

Responsabilidades:

- geração de Reels;
- concatenação;
- animação de imagens;
- zoom;
- transições;
- text overlays;
- conversão de formato.

### 12.5 Templates visuais

Estrutura sugerida:

```text
templates/
  reels/
  carousel/
  story/
```

Templates devem separar layout, tipografia e posicionamento dos dados do produto.

## 13. Componentes novos sugeridos

```text
post_from_url.py
product_resolver.py
affiliate_link.py
post_package.py

generators/
  reel_generator.py
  carousel_generator.py
  story_generator.py
  preview_generator.py
```

O componente existente de copy mantém sua responsabilidade atual.

## 14. Separação de responsabilidades

```text
ProductResolver
    → obtém e normaliza dados

AffiliateLinkResolver
    → obtém URL de afiliado

Copywriter/template existente
    → gera copy oficial

ReelGenerator
    → gera mídia para Reel

CarouselGenerator
    → gera cards

StoryGenerator
    → gera arte específica de Story

PreviewGenerator
    → permite inspeção local
```

Regra central:

```text
Copy existente = texto comercial oficial
Generators       = apresentação visual
```

Generators não devem se tornar novos copywriters.

## 15. Regra fundamental

```text
GERAR ≠ PUBLICAR
```

O sistema pode consultar Shopee, resolver produto, baixar mídia, obter link de afiliado, usar a copy existente, gerar imagens, vídeos, Story e preview.

O sistema não deve:

- publicar no Instagram;
- publicar no WhatsApp;
- publicar no TikTok;
- operar contas sociais.

A publicação permanece manual.

## 16. MVP

1. URL Shopee;
2. `ProductResolver`;
3. `ProductData`;
4. `affiliate_url`;
5. integração com o mecanismo de copy existente;
6. `--story`;
7. `--carousel`;
8. `--reels`;
9. `--all`;
10. `metadata.json`;
11. `preview.html`.

Prioridade sugerida:

```text
ProductResolver
      ↓
integração com copy existente
      ↓
Story
      ↓
Carousel
      ↓
Reels
      ↓
Preview
```

## 17. Critérios de aceite

### Copy

Para o mesmo `ProductData`, a legenda gerada pelo modo offline para Reels ou Carrossel deve usar a mesma fonte de regras e templates oficiais do projeto.

Nenhuma regra comercial existente deve ser reimplementada dentro dos generators.

### Story

- gerar arte vertical 9:16;
- gerar `link.txt` com a URL de afiliado;
- reservar área visual para o Link Sticker;
- não tentar incorporar link clicável no arquivo de imagem/vídeo.

### Segurança operacional

Nenhum comando desta funcionalidade deve publicar conteúdo ou autenticar em redes sociais.