# Atualização da Spec — Instagram Reels + Carrossel — Identidade visual e copy

## Status

Esta atualização complementa e modifica `docs/spec-instagram-reels-carousel.md`.

Quando houver conflito entre este documento e a spec anterior, **este documento prevalece somente nos pontos de identidade visual, apresentação da copy e formatação pública**.

As regras de seleção, alternância, quantidade diária, mídia, dry-run, containers, polling e publicação continuam sendo definidas pela spec anterior.

Referência visual obrigatória:

```text
docs/spec-identidade-visual-ofertas-femininas.md
```

## 1. Alteração de escopo da spec anterior

Na spec anterior, `alterar copy` estava explicitamente fora de escopo.

A partir desta atualização, a apresentação pública da copy do Instagram passa a seguir `docs/spec-identidade-visual-ofertas-femininas.md`.

Isso **não autoriza** alterar:

- ranking;
- seleção comercial;
- distribuição horária;
- meta diária;
- alternância Reels/Carrossel;
- elegibilidade de mídia;
- Graph API;
- credenciais;
- regras de claim/status.

## 2. Nova etapa conceitual do workflow

A parte comum do workflow passa a considerar dois produtos distintos:

```text
1. legenda da publicação
2. dados estruturados para composição visual
```

Estrutura conceitual:

```text
Trigger
↓
Contexto Instagram
↓
Validação
↓
Determinar próximo formato
↓
Selecionar candidato do plano de hoje
↓
Montar dados estruturados do criativo
↓
Montar legenda Instagram
↓
Dry Run
↓
Roteador Formato
↓
Reels ou Carrossel
```

Não é obrigatório que a composição visual seja executada dentro do n8n nesta etapa. O requisito é que os dados necessários sejam padronizados e que qualquer gerador de criativo siga a spec visual.

## 3. Campos obrigatórios para composição visual

Quando disponíveis na fonte, preservar:

```text
headline
product_name
product_name_short
price
old_price
discount_percent
rating
marketplace
offer_url
whatsapp_url
primary_subniche
affiliate_disclosure
product_image_urls
product_video_url
brand_asset
instagram_format
```

O gerador não deve precisar interpretar novamente o texto completo da legenda para descobrir preço, avaliação ou marketplace.

## 4. Nome do marketplace

Texto público deve usar somente o nome da plataforma ou português natural.

Correto:

```text
Shopee
Amazon
Oferta na Shopee
Disponível na Amazon
```

Não usar:

```text
on Shopee
on Amazon
```

Não introduzir expressões em inglês quando houver forma simples em português.

## 5. Formatação de preço

O preço público deve usar ponto decimal e não pode conter espaço entre reais e centavos.

Exemplo obrigatório:

```text
R$ 45.50
```

Incorreto:

```text
R$ 45. 50
```

Os centavos podem aparecer em corpo tipográfico menor no criativo, mas continuam pertencendo ao mesmo valor.

Se houver preço anterior:

```text
De R$ 89.90
Por R$ 45.50
```

ou, quando houver pouco espaço:

```text
R$ 45.50
44% OFF
```

## 6. Reels — apresentação visual

Reels deve utilizar o sistema visual definido na spec de identidade.

Sequência de referência:

```text
Cena 1 — abertura de marca / gancho
Cena 2 — produto
Cena 3 — preço, desconto e avaliação
Cena 4 — chamada para ação
Cena 5 — assinatura da marca
```

A ilustração completa da marca deve ser priorizada na abertura e/ou encerramento, não como elemento grande permanente sobre o produto.

Durante a demonstração do produto, utilizar marca reduzida ou marca d'água discreta quando necessário.

## 7. Carrossel — apresentação visual

Carrossel continua obedecendo à exigência operacional de 4 a 10 imagens da spec anterior.

A apresentação deve seguir:

```text
Página 1 — capa + produto + gancho
Páginas intermediárias — produto / detalhes visuais
Página de oferta — preço + avaliação + desconto
Página final — chamada para ação + identidade da marca
```

Não é obrigatório que cada imagem do produto receba texto.

## 8. URL do produto

A URL da oferta deve permanecer disponível na legenda e no payload estruturado.

Não usar URL longa como elemento visual dominante sobre imagens ou vídeo.

No criativo, preferir chamadas como:

```text
Link na legenda
```

Quando houver recurso clicável próprio da plataforma, usar o destino clicável em vez de exibir URL extensa.

## 9. Legenda Instagram

A legenda pode conter:

- nome completo do produto;
- URL da oferta;
- preço;
- avaliação;
- chamada para o grupo;
- aviso de afiliado;
- aviso de preço e disponibilidade;
- hashtags.

A legenda deve respeitar as regras de idioma e preço desta atualização.

Exemplo de trecho correto:

```text
🔥 Medicube PDRN Pink Peptide Serum

Shopee
💸 R$ 45.50
⭐ 5.0/5
```

Evitar:

```text
on Shopee
R$ 45. 50
```

## 10. Identidade visual

A imagem de marca aprovada deve ser tratada como ilustração principal da identidade.

A implementação de produção deve prever:

```text
assets/brand/ofertas-femininas/marca-principal.png
assets/brand/ofertas-femininas/marca-reduzida.png
```

A primeira corresponde à ilustração completa aprovada.

A segunda deve ser uma redução apropriada para assinatura, foto de perfil, marca d'água e pequenos espaços.

## 11. Critérios de aceite adicionais

Além dos critérios da spec anterior:

- [ ] criativos seguem `docs/spec-identidade-visual-ofertas-femininas.md`;
- [ ] o produto continua sendo o foco visual principal;
- [ ] preço aparece como `R$ 45.50`, sem espaço interno;
- [ ] centavos podem ser menores tipograficamente, mas não separados do valor;
- [ ] texto público usa `Shopee`, não `on Shopee`;
- [ ] texto público evita inglês desnecessário;
- [ ] URL completa permanece disponível na legenda/payload, mas não domina a arte;
- [ ] Reels possui estrutura visual reutilizável;
- [ ] Carrossel possui capa, páginas de produto, oferta e encerramento coerentes;
- [ ] dados de criativo permanecem estruturados, sem depender de extração posterior da legenda;
- [ ] marca principal e marca reduzida têm papéis distintos.

## 12. Prompt complementar para implementação

Ao implementar `docs/spec-instagram-reels-carousel.md`, leia também:

```text
docs/spec-instagram-reels-carousel-v2-identidade-visual.md
docs/spec-identidade-visual-ofertas-femininas.md
docs/copy-guidelines.md
```

Não reescreva regras operacionais já aprovadas na spec anterior.

Implemente somente os ajustes de dados estruturados, formatação pública e integração com templates visuais necessários para satisfazer esta atualização.

Não invente nova identidade, nova paleta ou nova marca. A ilustração aprovada é a referência canônica.
