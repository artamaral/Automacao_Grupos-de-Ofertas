# Spec — Identidade visual e padronização de criativos — Ofertas Femininas

## Status

Spec aprovada e atualizada para **padrão visual operacional v1**.

Esta spec define a identidade visual e a padronização dos criativos do perfil `Ofertas Femininas`, com prioridade para Instagram Post, Reels, Carrossel e Stories. Ela deve ser usada como referência por qualquer implementação que gere imagens, vídeos, capas, telas de abertura, telas finais ou textos sobrepostos em mídia.

A execução prática no Canva deve seguir também:

```text
docs/manual-template-ofertas-femininas-canva.md
```

## 1. Objetivo

Criar uma identidade visual consistente para a operação `Ofertas Femininas`, usando como referência principal a ilustração fornecida pela proprietária da marca: quatro mulheres estilizadas, em composição elegante de moda e compras, com paleta em bege, rosé, pêssego, terracota, vinho e preto.

A marca deve transmitir:

- feminino;
- elegante;
- moda e estilo de vida;
- compras e achadinhos;
- curadoria;
- sofisticação acessível.

A identidade não deve competir visualmente com o produto anunciado. **O produto é sempre o elemento principal dos criativos comerciais.**

## 2. Papel da ilustração da marca

A ilustração completa é a imagem principal da identidade, e não um logotipo técnico para todos os tamanhos.

Uso recomendado da ilustração completa:

- abertura de Reels;
- encerramento de Reels;
- capas;
- banners;
- peças institucionais;
- capa de catálogo;
- apresentação do grupo;
- tela final de chamada para ação;
- material de campanha da marca.

Em posts comerciais de produto, a ilustração deve aparecer de forma reduzida ou parcial, ou ser substituída pela assinatura textual:

```text
Ofertas Femininas
```

Nunca usar textos genéricos como:

```text
minha marca
marca
logo aqui
```

## 3. Marca reduzida e assinatura

Para espaços pequenos deve existir uma versão reduzida derivada da identidade principal.

Uso da versão reduzida:

- foto de perfil;
- marca d'água;
- canto de criativos;
- selo de assinatura;
- capas de Destaques;
- miniaturas.

A assinatura textual padrão é:

```text
Ofertas Femininas
```

Em criativos comerciais, quando a ilustração reduzida prejudicar a leitura ou competir com o produto, preferir a assinatura textual.

## 4. Formatos base

### 4.1 Instagram Post

```text
1080 × 1350 px
proporção 4:5
```

Este é o formato mestre do template estático.

### 4.2 Story e Reels vertical

```text
1080 × 1920 px
proporção 9:16
```

A estrutura visual deve ser adaptada mantendo as mesmas zonas, hierarquia, cores e tipografia.

## 5. Grade do template mestre 4:5

O template padrão de 1080 × 1350 deve usar:

```text
margem externa: 64 px
espaço mínimo entre blocos: 20 px
espaço preferencial entre blocos principais: 28–40 px
```

A composição é dividida conceitualmente em duas colunas:

```text
coluna esquerda: aproximadamente 42%
coluna direita: aproximadamente 58%
```

Uso:

- coluna esquerda: identidade, nome do produto, informações comerciais, benefícios somente quando confirmados, preço e chamada para ação;
- coluna direita: produto principal e decoração secundária.

A grade é uma referência operacional. Ajustes pequenos são permitidos para acomodar produtos muito largos ou muito altos, sem alterar a hierarquia visual.

## 6. Zonas fixas do template 4:5

### Zona A — identidade

Local:

```text
superior esquerda
```

Conteúdo:

```text
Ofertas Femininas
```

Opcionalmente acompanhada da marca reduzida.

Regras:

- não ocupar mais de aproximadamente 18% da altura;
- não competir com o produto;
- manter espaço claro antes do nome do produto.

### Zona B — nome curto do produto

Local:

```text
coluna esquerda, área superior/média
```

Conteúdo:

```text
{{product_name_short}}
```

Regras:

- alinhamento preferencial à esquerda;
- 2 a 4 linhas;
- evitar título comercial completo;
- preservar espaçamento entre linhas;
- nunca encostar no bloco de preço.

### Zona C — informações complementares

Local:

```text
abaixo do nome do produto
```

Podem aparecer somente quando os dados forem reais e confirmados:

```text
benefícios objetivos
desconto
característica do produto
quantidade/tamanho
```

Regras:

- máximo de 4 linhas ou itens;
- sem parágrafos;
- não inventar benefícios, composição, peso, volume ou efeito do produto;
- bloco vazio deve ser removido. **Não deixar faixa, cartão ou bloco colorido sem conteúdo.**

### Zona D — produto principal

Local:

```text
lado direito central
```

Regras:

- foco visual principal;
- ocupar aproximadamente 40% a 52% da largura útil;
- deve ser maior e mais importante que elementos decorativos;
- não cobrir textos;
- não ser coberto pela marca ou por preços;
- usar imagem real do produto quando disponível.

### Zona E — cartão comercial

Local:

```text
inferior esquerdo
```

Ordem fixa:

```text
{{marketplace}}
R$ {{price}}
⭐ {{rating}}
```

Exemplo:

```text
Shopee
R$ 35.48
⭐ 4.9
```

O cartão deve manter dimensões e hierarquia visual consistentes entre ofertas.

### Zona F — chamada para ação

Local:

```text
abaixo do cartão comercial
```

Texto padrão:

```text
Link na legenda
```

Outras chamadas somente quando definidas pela operação.

Nunca exibir a URL longa como texto dominante na arte.

### Zona G — rodapé

Conteúdo permitido:

```text
Preço e disponibilidade podem mudar.
#ad
```

Regras:

- texto discreto;
- leitura possível em celular;
- não competir com preço ou produto.

## 7. Paleta oficial v1

A paleta operacional deriva da ilustração aprovada e deve ser usada como referência no Canva.

| Função | Cor | HEX v1 |
|---|---|---|
| Fundo principal | creme quente | `#F7EFE6` |
| Fundo secundário | bege rosado | `#F1DDD2` |
| Rosé | rosé suave | `#DFA39A` |
| Pêssego | pêssego | `#E8A07E` |
| Terracota | destaque | `#C96F55` |
| Vinho | texto/destaque forte | `#7A2F3A` |
| Marrom escuro | texto funcional | `#4B3835` |
| Preto suave | contraste máximo | `#262120` |

Regras:

- não é obrigatório usar todas as cores;
- fundo deve permanecer claro na maioria dos posts de oferta;
- vinho e terracota são cores de destaque, não fundos extensos sem função;
- qualquer bloco colorido precisa ter função visual ou conteúdo;
- preservar contraste suficiente para leitura em celular.

## 8. Tipografia oficial v1

O sistema usa duas famílias tipográficas.

### 8.1 Títulos e identidade

Fonte preferencial:

```text
Playfair Display
```

Fallback permitido no Canva quando necessário:

```text
Cormorant Garamond
Libre Baskerville
```

Uso:

- `Ofertas Femininas`;
- nome curto do produto;
- preço, quando o template aprovado usar serifada.

### 8.2 Texto funcional

Fonte preferencial:

```text
Montserrat
```

Fallback permitido:

```text
DM Sans
Inter
Lato
```

Uso:

- marketplace;
- avaliação;
- benefícios;
- chamada para ação;
- aviso legal;
- textos auxiliares.

Não misturar mais de duas famílias no mesmo criativo.

## 9. Escala tipográfica 1080 × 1350

Referência operacional:

| Elemento | Tamanho recomendado |
|---|---:|
| `Ofertas Femininas` | 54–68 px |
| Nome principal do produto | 72–96 px |
| Subnome/marca do produto | 52–64 px |
| Benefícios/informações | 24–30 px |
| Marketplace | 24–30 px |
| Preço | 70–90 px |
| Avaliação | 28–36 px |
| Chamada para ação | 28–34 px |
| Aviso de rodapé | 18–22 px |

A escala pode ser reduzida proporcionalmente para nomes maiores, sem quebrar a hierarquia.

## 10. Espaçamento tipográfico e entre blocos

### 10.1 Entre linhas

O texto nunca deve parecer comprimido.

Referência:

```text
títulos: line-height 0.95–1.10
texto funcional: line-height 1.15–1.35
```

### 10.2 Entre blocos

Referência para post 4:5:

```text
identidade → nome do produto: 32 px ou mais
nome do produto → informações complementares: 28 px ou mais
informações → cartão comercial: 28 px ou mais
cartão comercial → chamada para ação: 20–28 px
chamada para ação → rodapé: 20 px ou mais
```

Não empilhar textos sem respiro apenas para preencher espaço.

## 11. Regra rígida do preço

Formato textual padrão:

```text
R$ 45.50
```

Regras obrigatórias:

- duas casas decimais quando houver centavos;
- separador decimal `.`;
- nenhum espaço entre ponto e centavos;
- preço em uma única linha sempre que possível;
- `R$`, parte inteira e centavos devem usar **a mesma família tipográfica**;
- não criar diferença de fonte entre `R$` e o valor;
- se houver diferença de tamanho, ela deve ser intencional e limitada.

Padrão recomendado quando houver hierarquia:

```text
R$: 80% do tamanho do número
parte inteira: 100%
centavos: 80–85%
```

Todos com o mesmo peso visual e a mesma família.

Para máxima consistência do template mestre, é permitido usar tudo no mesmo tamanho:

```text
R$ 35.48
```

Correto:

```text
R$ 35.48
```

Incorreto:

```text
R$ 35. 48
R$35.48   [quando o template exigir espaço após R$]
```

## 12. Regra de marketplace e idioma

A linguagem pública dos criativos deve ser em português.

Correto:

```text
Shopee
Amazon
Oferta na Shopee
Disponível na Amazon
```

Evitar:

```text
on Shopee
on Amazon
Shop now
Best deal
```

No cartão comercial, usar preferencialmente apenas:

```text
Shopee
Amazon
```

## 13. Elementos decorativos

Permitidos:

- círculo suave atrás do produto;
- folhas lineares;
- pontos decorativos leves;
- pedestal;
- vaso ou objeto neutro de apoio quando não competir com o item;
- divisores finos.

Regras:

- decoração é sempre secundária;
- máximo recomendado de 2 a 3 elementos decorativos relevantes;
- não usar elemento apenas para preencher espaço;
- não criar bloco vinho, rosé ou terracota vazio;
- não alterar ou inventar a embalagem real do produto quando houver imagem oficial disponível.

## 14. Conteúdo real versus conteúdo ilustrativo

Criativos de oferta devem usar dados reais da fonte operacional.

Podem ser exibidos:

```text
product_name_short
marketplace
price
rating
discount_percent
características confirmadas
peso/volume confirmados
```

Não inventar:

- benefícios;
- ingredientes;
- peso;
- volume;
- porcentagem;
- desconto;
- selo;
- avaliação;
- claims de saúde ou beleza;
- texto de embalagem que não exista na mídia real.

Se uma informação não estiver disponível, remover o bloco correspondente.

## 15. Texto sobre a mídia versus legenda

### Na arte

Priorizar:

```text
Ofertas Femininas
nome curto do produto
marketplace
preço
avaliação
desconto confirmado
chamada para ação
```

Benefícios somente quando confirmados.

### Na legenda

Manter:

- nome comercial completo;
- URL da oferta;
- preço;
- avaliação;
- chamada para o grupo;
- aviso de afiliado;
- aviso de preço e disponibilidade;
- hashtags aplicáveis.

## 16. Estrutura padrão para Reels

O Reels deve preservar a mesma identidade em formato 9:16.

Estrutura:

```text
Cena 1 — identidade / abertura curta
Cena 2 — produto
Cena 3 — preço + avaliação + marketplace
Cena 4 — chamada para ação
Cena 5 — assinatura / aviso
```

Não é obrigatório exibir texto no topo em todas as cenas. Se o produto e o título já forem suficientes, priorizar espaço e respiro visual.

A ilustração principal não deve permanecer grande durante todo o vídeo.

## 17. Estrutura padrão para Carrossel

```text
Página 1 — capa + produto + identidade
Página 2 — produto/detalhe
Página 3 — informação confirmada ou detalhe visual
Página 4 — preço + avaliação + marketplace
Página final — chamada para ação + Ofertas Femininas
```

Quando não houver informação suficiente para uma página intermediária, reduzir a quantidade de páginas. Não criar conteúdo artificial para completar páginas.

## 18. Estrutura padrão para Stories

Estrutura mínima:

```text
produto
preço
marketplace
chamada para ação
Ofertas Femininas
```

Quando houver ligação clicável, usar a URL da oferta como destino do elemento interativo, sem exibir a URL longa como texto dominante.

## 19. Campos padronizados para automação

Todo gerador de criativo deve trabalhar, quando disponíveis, com:

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
confirmed_features
size_or_volume
```

A posição visual dos campos permanece estável entre produtos. O conteúdo muda; o sistema visual não deve ser redesenhado a cada oferta.

## 20. Elementos fixos versus variáveis

### Fixos

```text
formato
grade
margens
posição dos blocos
paleta
tipografia
estilo do cartão comercial
estilo da chamada para ação
posição do rodapé
assinatura Ofertas Femininas
```

### Variáveis

```text
imagem do produto
nome do produto
marketplace
preço
avaliação
desconto
informações confirmadas
```

## 21. Ativo canônico da marca

A imagem fornecida pela proprietária é a referência visual aprovada.

Armazenamento recomendado:

```text
assets/brand/ofertas-femininas/marca-principal.png
assets/brand/ofertas-femininas/marca-reduzida.png
```

Não substituir a ilustração por imagem gerada ou outra marca sem aprovação explícita.

## 22. Template mestre no Canva

Deve existir um template mestre de Instagram Post 4:5 no Canva, construído a partir desta spec.

O template deve conter:

- fundo e paleta definidos;
- Zona A a Zona G posicionadas;
- caixas de texto pré-formatadas;
- cartão comercial fixo;
- chamada para ação fixa;
- rodapé fixo;
- área principal reservada ao produto;
- assinatura `Ofertas Femininas`;
- elementos decorativos secundários bloqueados quando possível.

Campos variáveis devem ser claramente identificados no template.

O manual operacional é:

```text
docs/manual-template-ofertas-femininas-canva.md
```

## 23. Critérios de aceite

Um template visual atende esta spec quando:

- [ ] usa a identidade derivada da ilustração aprovada;
- [ ] usa formato 1080 × 1350 para o template mestre de post;
- [ ] mantém margem externa de referência de 64 px;
- [ ] mantém o produto como foco principal;
- [ ] usa `Ofertas Femininas` como assinatura;
- [ ] não utiliza `minha marca` ou equivalentes;
- [ ] não mantém bloco colorido vazio;
- [ ] não inventa benefícios, peso, volume ou características;
- [ ] exibe preço no padrão `R$ 45.50`;
- [ ] usa a mesma família tipográfica em `R$` e no valor;
- [ ] respeita espaçamento entre linhas e blocos;
- [ ] usa `Shopee`, e não `on Shopee`;
- [ ] mantém textos públicos em português;
- [ ] não coloca URL longa como texto dominante;
- [ ] permite reutilização com campos estruturados;
- [ ] mantém posição e hierarquia visual consistentes;
- [ ] usa decoração apenas como elemento secundário;
- [ ] contempla Reels, Carrossel e Story com a mesma identidade.

## 24. Fora de escopo

Esta spec não define:

- algoritmo de seleção comercial do produto;
- horários de publicação;
- quantidade diária de posts;
- credenciais do Instagram;
- integração com Graph API;
- regras de ranking;
- taxonomia;
- política de cooldown;
- geração automática de uma nova ilustração da marca.

Essas regras permanecem nas specs operacionais correspondentes.
