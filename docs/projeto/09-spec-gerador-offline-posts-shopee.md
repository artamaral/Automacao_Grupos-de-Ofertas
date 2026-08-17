# Spec — Gerador Offline de Posts a partir de URL Afiliada Shopee

## 1. Objetivo

Criar uma ferramenta local que receba **somente uma URL afiliada da Shopee** e gere materiais prontos para publicação manual.

O sistema não publica automaticamente e não depende de banco, catálogo, API autenticada ou credenciais Shopee.

Formatos suportados:

- Reels;
- Carrossel;
- Story;
- todos os formatos em uma única execução.

## 2. Contrato de isolamento

### Entrada de negócio única

```text
URL afiliada Shopee
```

Exemplo:

```text
https://s.shopee.com.br/XXXXXXXX
```

A URL fornecida pelo usuário:

- deve ser preservada como `affiliate_url`;
- deve ser usada nos posts e em `story/link.txt`;
- nunca deve ser substituída por um link gerado pelo sistema.

### Dependências externas permitidas

O script pode acessar apenas recursos públicos necessários para resolver a própria URL:

- seguir redirects da URL afiliada;
- carregar a página pública do produto;
- baixar imagens públicas;
- baixar vídeos públicos quando disponíveis.

### Dependências proibidas

Este fluxo não deve usar:

```text
SHOPEE_PARTNER_ID
SHOPEE_SECRET_KEY
SHOPEE_TRACKING_ID
ShopeeProvider
productOfferV2 autenticado
generateShortLink
Supabase
Postgres
SQLite
Google Sheets
catálogo local
fila de ofertas
storage do projeto
histórico de publicações
```

`shop_id` e `item_id` são auxiliares e opcionais. A geração deve funcionar mesmo quando eles não puderem ser extraídos.

## 3. Entradas

### Entrada obrigatória

```text
URL afiliada Shopee
```

### Flags

```text
--reels
--carousel
--story
--all
--output <diretorio>
--preview
```

Exemplos:

```powershell
python -m ofertas_bot.post_from_url "URL_AFILIADA" --story
python -m ofertas_bot.post_from_url "URL_AFILIADA" --carousel
python -m ofertas_bot.post_from_url "URL_AFILIADA" --reels
python -m ofertas_bot.post_from_url "URL_AFILIADA" --all --preview
```

## 4. Extração pública de dados

A partir da URL fornecida, o resolver deve seguir redirects e extrair da página pública tudo que estiver disponível e for necessário para copy e mídia.

Campos normalizados:

```text
affiliate_url       # exatamente a URL fornecida
resolved_url        # destino final do redirect
title
description
price
old_price
discount_pct
rating
rating_count
sales
images[]
videos[]
shop_name
shop_id             # opcional
item_id             # opcional
```

Fontes públicas de extração podem incluir:

- JSON-LD;
- Open Graph / meta tags;
- dados estruturados presentes no HTML público.

O sistema não deve buscar dados ausentes em banco ou API autenticada.

Quando um campo opcional não estiver disponível, deve permanecer ausente/nulo. Não inventar valores.

`title` e `price` são necessários para produzir a copy atual; se não puderem ser extraídos, o resolver deve falhar com erro explícito.

## 5. ProductData

O mesmo `ProductData` deve alimentar todos os formatos para impedir divergências entre preço, título, mídia e URL.

A URL de afiliado original é a fonte oficial de link do pacote.

Quando `item_id` não existir, o diretório do pacote deve usar uma chave estável derivada da URL, sem consultar nenhuma base.

## 6. Copy existente do projeto

Para **Reels e Carrossel**, não criar um novo sistema de copy.

Referências oficiais:

- [`src/ofertas_bot/agents/copywriter.py`](../../src/ofertas_bot/agents/copywriter.py)
- [`docs/copy-guidelines.md`](../copy-guidelines.md)
- [`tests/test_copywriter.py`](../../tests/test_copywriter.py)
- [`config/message_templates/shopee.txt`](../../config/message_templates/shopee.txt)

Fluxo:

```text
ProductData
    ↓
Copywriter existente
    ↓
GeneratedCopy
    ↓
ReelGenerator / CarouselGenerator
```

Os generators não devem reimplementar regras comerciais de preço, desconto, disclosure ou estrutura de legenda.

### Story

Story pode ter copy visual própria, curta, derivada diretamente do `ProductData`.

Essa copy visual não substitui o `Copywriter` oficial.

## 7. Fluxo completo

```text
URL afiliada Shopee
        ↓
redirect público
        ↓
página pública Shopee
        ↓
ShopeePublicPageResolver
        ↓
ProductData
        ↓
┌──────────────────────────────────────┐
│ Copywriter existente                 │
│   ├→ ReelGenerator                   │
│   └→ CarouselGenerator               │
│                                      │
│ ProductData → StoryGenerator         │
└──────────────────────────────────────┘
        ↓
arquivos locais
```

Não existe `AffiliateLinkResolver`: o link afiliado já é a entrada.

## 8. Saída

```text
output/
  <item_id-ou-chave-da-url>/
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

## 9. Reels

Entrada:

- `ProductData`;
- copy oficial existente;
- vídeos públicos do produto quando disponíveis;
- imagens públicas como fallback.

Saída:

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

- `caption.txt` vem do `Copywriter` existente;
- priorizar vídeo público do produto quando disponível;
- sem vídeo, permitir composição usando imagens;
- texto visual pode resumir dados de `ProductData`.

## 10. Carrossel

Entrada:

- `ProductData`;
- copy oficial existente;
- imagens públicas extraídas da página.

Saída:

```text
01.jpg
02.jpg
...
caption.txt
```

Regras:

- `caption.txt` vem do `Copywriter` existente;
- cards usam apenas fatos extraídos da página;
- número de cards pode variar conforme conteúdo disponível.

## 11. Story

Entrada:

- `ProductData`;
- `affiliate_url` original;
- imagem pública do produto.

Saída:

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
- imagem;
- preço;
- preço anterior;
- desconto;
- CTA;
- área reservada para Link Sticker.

`story/link.txt` deve conter **exatamente a URL afiliada fornecida pelo usuário**.

O link clicável é adicionado manualmente pelo usuário através do Link Sticker da plataforma.

## 12. Metadata

`metadata.json` deve registrar apenas dados obtidos da URL/página e dados de geração.

Exemplo:

```json
{
  "marketplace": "shopee",
  "affiliate_url": "https://s.shopee.com.br/xxxx",
  "resolved_url": "https://shopee.com.br/...",
  "shop_id": 1252993709,
  "item_id": 21997761426,
  "title": "Casaco Teddy com Capuz",
  "description": "...",
  "price": 49.90,
  "old_price": 89.90,
  "discount_pct": 44,
  "rating": 4.8,
  "rating_count": 1234,
  "sales": 321,
  "images": ["https://..."],
  "videos": ["https://..."],
  "formats": ["reels", "carousel", "story"]
}
```

## 13. Preview

Com `--preview`, gerar `preview.html` local com:

- visualização de Reel, Carrossel e Story;
- copiar legenda;
- copiar URL afiliada;
- abrir imagem;
- abrir vídeo.

O preview não publica nem envia dados a serviços externos além dos recursos públicos já usados pelo pacote.

## 14. Recursos necessários

### Existentes

```text
src/ofertas_bot/agents/copywriter.py
docs/copy-guidelines.md
tests/test_copywriter.py
config/message_templates/shopee.txt
```

### Processamento de imagem

`Pillow` para resize, crop, composição, overlays, cards, Story e cover.

### Processamento de vídeo

`FFmpeg` pode ser usado como implementação local para gerar MP4/Reels.

Isso é ferramenta local de processamento e não cria dependência de banco ou serviço externo.

## 15. Separação de responsabilidades

```text
ShopeePublicPageResolver
    → resolve redirect e extrai fatos públicos

Copywriter existente
    → gera texto comercial oficial

ReelGenerator
    → gera mídia Reel

CarouselGenerator
    → gera cards

StoryGenerator
    → gera Story e prepara link.txt

PreviewGenerator
    → inspeção local
```

## 16. Regra fundamental

```text
ENTRADA ÚNICA = URL AFILIADA
EXTRAÇÃO = SOMENTE RECURSOS PÚBLICOS DESSA URL
SAÍDA = SOMENTE ARQUIVOS LOCAIS
GERAR ≠ PUBLICAR
```

Nenhum componente deste fluxo deve autenticar na Shopee ou consultar qualquer base do restante do projeto.

## 17. Critérios de aceite

### Isolamento

- nenhuma dependência de `Settings` para credenciais Shopee;
- nenhum `ShopeeProvider`;
- nenhum `generateShortLink`;
- nenhuma consulta autenticada a `productOfferV2`;
- nenhuma leitura/gravação em Supabase ou outra base;
- nenhuma consulta a catálogo, histórico ou fila;
- URL afiliada original preservada sem alteração.

### Extração

- seguir redirect público;
- extrair título e preço;
- extrair descrição, rating, contagem de avaliações, vendas, fotos e vídeos quando disponíveis;
- `shop_id` e `item_id` opcionais;
- não inventar dados ausentes.

### Copy

Reels e Carrossel devem reutilizar a fonte oficial de copy existente.

### Story

- gerar 9:16;
- gerar `link.txt` com exatamente a URL de entrada;
- reservar área para Link Sticker;
- não tentar incorporar link clicável diretamente no JPG/MP4.

### Segurança operacional

Nenhum comando desta funcionalidade deve publicar conteúdo ou autenticar em redes sociais.
