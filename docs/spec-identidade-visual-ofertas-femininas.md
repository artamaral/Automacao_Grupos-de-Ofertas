# Spec — Identidade visual e padronização de criativos — Ofertas Femininas

## Status

Spec aprovada.

Esta spec define a identidade visual e a padronização dos criativos do perfil feminino, com prioridade para Instagram Reels, Carrossel e Stories. Ela deve ser usada como referência por qualquer implementação que gere imagens, vídeos, capas, telas de abertura, telas finais ou textos sobrepostos em mídia.

## 1. Objetivo

Criar uma identidade visual consistente para a operação `Ofertas Femininas`, usando como referência principal a ilustração fornecida pela proprietária da marca: quatro mulheres estilizadas, em composição elegante de moda e compras, com paleta em bege, rosé, pêssego, terracota, vinho e preto.

A marca deve transmitir:

- feminino;
- elegante;
- moda e estilo de vida;
- compras e achadinhos;
- curadoria;
- sofisticação acessível.

A identidade não deve competir visualmente com o produto anunciado. O produto continua sendo o elemento principal dos criativos comerciais.

## 2. Papel da ilustração da marca

A ilustração completa deve ser tratada como **imagem principal da identidade**, e não como um logotipo técnico para todos os tamanhos.

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

Evitar usar a ilustração completa em tamanho muito pequeno, pois os detalhes perdem legibilidade.

## 3. Marca reduzida

Para espaços pequenos deve existir uma versão reduzida derivada da identidade principal.

Uso da versão reduzida:

- foto de perfil;
- marca d'água;
- canto de criativos;
- selo de assinatura;
- capas de Destaques;
- miniaturas.

A versão reduzida pode usar:

- uma personagem representativa; ou
- uma composição simplificada das quatro personagens.

A implementação futura da versão reduzida deve manter a mesma linguagem visual da ilustração principal.

## 4. Paleta visual

A paleta deve ser derivada da própria ilustração da marca.

Famílias de cor prioritárias:

- bege claro;
- rosé;
- pêssego;
- terracota;
- vinho;
- preto.

Não é obrigatório usar todas as cores no mesmo criativo.

A regra principal é preservar contraste suficiente para leitura em celular e manter aparência limpa e elegante.

## 5. Princípios visuais

Todo criativo deve seguir estes princípios:

- produto como foco principal;
- pouco texto por cena;
- hierarquia clara;
- preço legível imediatamente;
- avaliação e desconto como informação secundária;
- identidade da marca presente, mas sem encobrir o produto;
- fundos limpos;
- evitar excesso de elementos decorativos;
- evitar texto longo sobre imagem ou vídeo;
- manter consistência entre Reels, Carrossel e Stories.

## 6. Estrutura visual padrão para Reels

O Reels deve utilizar uma estrutura em blocos reutilizáveis.

### Cena 1 — abertura

Objetivo: reconhecer a marca e gerar interesse.

Conteúdo possível:

```text
Achadinho do dia
```

ou uma chamada curta equivalente adequada ao subnicho.

A ilustração da marca pode aparecer integralmente ou como elemento parcial.

### Cena 2 — produto

O produto ocupa a maior área visual.

Campos permitidos sobre a mídia:

```text
{{product_name_short}}
{{marketplace}}
```

O nome deve ser reduzido para leitura rápida. O título comercial completo não deve ocupar a tela.

Para o marketplace, usar somente o nome da plataforma.

Exemplo correto:

```text
Shopee
```

Não usar construções em inglês como:

```text
on Shopee
```

### Cena 3 — oferta

Prioridade visual:

```text
R$ {{price}}
{{discount}}
⭐ {{rating}}
```

Exemplo:

```text
R$ 45.50
⭐ 5.0
```

O preço deve ser uma unidade visual única e nunca pode conter espaço interno entre reais e centavos.

Correto:

```text
45.50
R$ 45.50
```

Incorreto:

```text
45. 50
R$ 45. 50
```

A parte decimal pode ser visualmente menor que a parte inteira, desde que continue pertencendo ao mesmo preço e não seja separada por espaço.

Exemplo visual permitido:

```text
45.50
```

com `50` em corpo tipográfico menor.

### Cena 4 — chamada para ação

Texto curto.

Exemplos:

```text
Link na legenda
```

```text
Entre no grupo de ofertas
```

A URL longa do produto não deve ser sobreposta ao vídeo ou imagem.

### Cena 5 — assinatura

Pode incluir:

- versão reduzida da marca;
- `#ad` ou aviso equivalente;
- aviso curto de preço e disponibilidade;
- chamada para o grupo.

## 7. Estrutura padrão para Carrossel

A identidade visual deve se manter estável entre as páginas.

Estrutura sugerida:

```text
Página 1 — capa + produto + gancho
Página 2 — produto / detalhe
Página 3 — produto / benefício visual
Página 4 — preço + avaliação + desconto
Página final — chamada para ação + marca
```

Quando houver mais imagens do produto, elas podem ocupar páginas intermediárias.

Não repetir todo o texto comercial em todas as páginas.

## 8. Estrutura padrão para Stories

Stories devem privilegiar ação rápida.

Estrutura mínima:

```text
produto
preço
marketplace
chamada para ação
marca
```

Quando a plataforma permitir ligação clicável, o Story pode usar o link de oferta como destino do elemento interativo.

Não exibir URL extensa como texto principal se houver recurso clicável disponível.

## 9. Campos padronizados para automação

Todo gerador de criativo deve trabalhar, quando disponíveis, com os seguintes campos estruturados:

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
```

A posição visual dos campos deve permanecer estável entre produtos. O conteúdo muda; o sistema visual não deve ser redesenhado a cada oferta.

## 10. Regra de preço

Formato textual padrão nos criativos:

```text
R$ 45.50
```

Regras obrigatórias:

- duas casas decimais quando houver centavos;
- separador decimal `.`;
- nenhum espaço entre ponto e centavos;
- permitido usar corpo menor nos centavos;
- não alterar o valor numérico recebido da fonte sem regra comercial explícita.

Exemplo com preço anterior:

```text
De R$ 89.90
Por R$ 45.50
```

ou, quando o espaço for restrito:

```text
R$ 45.50
44% OFF
```

## 11. Regra de marketplace e idioma

A linguagem pública dos criativos deve ser em português.

Não utilizar expressões híbridas desnecessárias em inglês.

Exemplos:

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

Termos técnicos internos, nomes de campos, APIs ou identificadores de código podem permanecer em inglês quando forem parte da implementação.

## 12. Texto sobre a mídia versus legenda

A tela deve conter somente informação de leitura rápida.

### Sobre a mídia

Priorizar:

```text
gancho curto
nome curto do produto
preço
desconto
avaliação
marketplace
chamada para ação
```

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

A legenda não precisa repetir exatamente a diagramação da tela.

## 13. Uso da marca em vídeos

A marca pode aparecer em três níveis:

### Abertura

Ilustração principal por curto período para identificação da marca.

### Durante o conteúdo

Versão reduzida ou marca d'água discreta, sem cobrir produto, preço ou informações importantes.

### Encerramento

Ilustração principal ou versão reduzida com chamada para ação.

Não manter a ilustração completa grande durante todo o vídeo.

## 14. Uso da marca em imagens

Em posts estáticos e Carrossel:

- produto é o primeiro foco;
- marca reduzida pode ficar em canto fixo;
- ilustração completa pode ser usada na capa ou página final;
- evitar cobrir detalhes do produto;
- preservar margem segura para interfaces do Instagram.

## 15. Sistema de identidade

A identidade deve ser tratada em três níveis:

```text
1. marca reduzida
2. ilustração principal
3. templates reutilizáveis
```

### Marca reduzida

Uso em pequenas áreas e assinatura.

### Ilustração principal

Uso institucional, abertura, encerramento e capas.

### Templates reutilizáveis

Uso diário em Reels, Stories, Carrossel e ofertas.

## 16. Ativo canônico da marca

A imagem fornecida pela proprietária é a referência visual aprovada desta spec.

Antes de automatizar a geração de criativos em produção, armazenar uma cópia canônica no projeto, preferencialmente em caminho equivalente a:

```text
assets/brand/ofertas-femininas/marca-principal.png
```

Também deve ser criada posteriormente uma versão reduzida, por exemplo:

```text
assets/brand/ofertas-femininas/marca-reduzida.png
```

Não substituir a ilustração por imagem gerada ou por outra marca sem aprovação explícita.

## 17. Critérios de aceite

Um template visual atende esta spec quando:

- [ ] usa a identidade derivada da ilustração aprovada;
- [ ] mantém o produto como foco principal;
- [ ] exibe preço sem espaço interno, por exemplo `R$ 45.50`;
- [ ] pode usar centavos em corpo menor sem separá-los do preço;
- [ ] usa `Shopee`, e não `on Shopee`;
- [ ] mantém textos públicos prioritariamente em português;
- [ ] não coloca URL longa como texto dominante sobre mídia;
- [ ] permite reutilização com campos estruturados;
- [ ] mantém posição e hierarquia visual consistentes entre produtos;
- [ ] inclui assinatura visual da marca sem obstruir o produto;
- [ ] contempla abertura, conteúdo e encerramento de Reels;
- [ ] contempla capa, conteúdo e página final de Carrossel;
- [ ] permite Story com chamada para ação e link clicável quando disponível.

## 18. Fora de escopo

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
