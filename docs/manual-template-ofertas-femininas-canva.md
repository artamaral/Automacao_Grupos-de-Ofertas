# Manual do Template — Ofertas Femininas — Canva

## Status

Manual operacional v1 aprovado para padronização visual no Canva.

Este documento transforma a spec visual em instruções práticas de construção, edição e reutilização do template.

Referência obrigatória:

```text
docs/spec-identidade-visual-ofertas-femininas.md
```

## 1. Objetivo

Criar um template mestre no Canva que permita gerar novos posts de oferta sem redesenhar a peça a cada produto.

O operador deve trocar somente dados e mídias variáveis, mantendo:

- posições;
- cores;
- tipografia;
- tamanhos;
- espaçamentos;
- hierarquia;
- cartão comercial;
- chamada para ação;
- rodapé;
- assinatura `Ofertas Femininas`.

## 2. Template mestre

Criar inicialmente:

```text
Ofertas Femininas — Post Oferta — Mestre 4x5
```

Dimensão:

```text
1080 × 1350 px
```

Depois derivar:

```text
Ofertas Femininas — Story Oferta — Mestre 9x16
Ofertas Femininas — Capa Reels — Mestre 9x16
Ofertas Femininas — Carrossel Oferta — Mestre 4x5
```

## 3. Grade do Post 4x5

### Margens

Usar como referência:

```text
64 px em todos os lados
```

Criar guias visuais ou usar réguas do Canva para manter essa margem.

### Colunas

Divisão conceitual:

```text
esquerda: 42%
direita: 58%
```

A coluna direita deve receber o produto principal.

## 4. Camadas recomendadas

Organizar os elementos na seguinte ordem:

```text
1. fundo
2. decoração de fundo
3. produto
4. identidade
5. nome do produto
6. informações complementares
7. cartão comercial
8. chamada para ação
9. rodapé
```

Quando possível, bloquear no Canva:

- fundo;
- decoração;
- cartão comercial;
- botão de chamada para ação;
- rodapé;
- divisores;
- assinatura fixa.

Manter desbloqueados:

- imagem do produto;
- nome curto;
- preço;
- avaliação;
- marketplace;
- desconto;
- informações confirmadas.

## 5. Zona A — Ofertas Femininas

Posição:

```text
superior esquerda
```

Texto obrigatório:

```text
Ofertas Femininas
```

Fonte:

```text
Playfair Display
```

Tamanho:

```text
54–68 px
```

Cor preferencial:

```text
#7A2F3A
```

Pode ser acompanhada por uma versão reduzida da ilustração da marca.

Não usar:

```text
minha marca
marca
logo aqui
```

## 6. Zona B — nome do produto

Campo:

```text
{{product_name_short}}
```

Fonte:

```text
Playfair Display
```

Tamanho-base:

```text
72–96 px
```

Cor preferencial:

```text
#C96F55
```

Regras:

- alinhado à esquerda;
- máximo recomendado de 4 linhas;
- line-height entre 0.95 e 1.10;
- reduzir tamanho somente quando necessário;
- não quebrar palavras de forma artificial;
- não usar o título comercial completo se ele ocupar espaço excessivo.

## 7. Zona C — informações complementares

Fonte:

```text
Montserrat
```

Tamanho:

```text
24–30 px
```

Cor:

```text
#4B3835
```

Podem entrar:

- benefício confirmado;
- tamanho/volume confirmado;
- desconto confirmado;
- característica objetiva confirmada.

Máximo:

```text
4 itens
```

Se não houver informação real suficiente:

```text
remover o bloco
```

Não deixar bloco vinho, rosé, terracota ou qualquer outro bloco colorido sem texto ou função.

## 8. Zona D — produto

A imagem real do produto deve ser inserida na área central/direita.

Regra de escala:

```text
aproximadamente 40–52% da largura útil
```

O produto deve ser o maior elemento visual da peça.

Regras:

- manter proporção original;
- evitar deformação;
- não cobrir informações comerciais;
- não colocar decoração sobre a embalagem;
- se houver fundo na imagem original que comprometa o layout, tratar somente quando for possível sem alterar o produto;
- não gerar embalagem fictícia para substituir imagem oficial disponível.

## 9. Zona E — cartão comercial

O cartão deve permanecer na região inferior esquerda.

Ordem fixa:

```text
Marketplace
Preço
Avaliação
```

### Marketplace

Fonte:

```text
Montserrat
```

Tamanho:

```text
24–30 px
```

Texto:

```text
Shopee
Amazon
```

Não usar:

```text
on Shopee
on Amazon
```

### Preço

Formato:

```text
R$ 35.48
```

Fonte preferencial:

```text
Playfair Display
```

Tamanho:

```text
70–90 px
```

Cor:

```text
#7A2F3A
```

Regra rígida:

- `R$`, parte inteira e centavos devem usar a mesma família;
- não separar `35.48`;
- não usar `35. 48`;
- preferir preço inteiro no mesmo tamanho para consistência;
- se houver redução de `R$` ou centavos, usar no máximo a proporção definida na spec.

### Avaliação

Fonte:

```text
Montserrat
```

Tamanho:

```text
28–36 px
```

Formato:

```text
⭐ 4.9
```

## 10. Zona F — chamada para ação

Texto padrão:

```text
Link na legenda
```

Fonte:

```text
Montserrat
```

Tamanho:

```text
28–34 px
```

Botão:

- cantos arredondados;
- fundo `#C96F55` ou `#E8A07E`;
- texto claro;
- ícone de link opcional;
- largura suficiente para não apertar o texto.

Não colocar URL longa dentro do botão.

## 11. Zona G — rodapé

Textos:

```text
Preço e disponibilidade podem mudar.
#ad
```

Fonte:

```text
Montserrat
```

Tamanho:

```text
18–22 px
```

Cor:

```text
#4B3835
```

Pode usar `#7A2F3A` em `#ad`.

## 12. Paleta no Canva

Cadastrar ou manter facilmente acessíveis:

```text
#F7EFE6 — creme quente
#F1DDD2 — bege rosado
#DFA39A — rosé suave
#E8A07E — pêssego
#C96F55 — terracota
#7A2F3A — vinho
#4B3835 — marrom escuro
#262120 — preto suave
```

Uso padrão:

```text
fundo → #F7EFE6
identidade → #7A2F3A
título do produto → #C96F55
texto funcional → #4B3835
botão → #C96F55
preço → #7A2F3A
```

## 13. Espaçamento

### Entre identidade e produto

```text
32 px ou mais
```

### Nome do produto → informações

```text
28 px ou mais
```

### Informações → cartão comercial

```text
28 px ou mais
```

### Cartão → chamada para ação

```text
20–28 px
```

### Chamada para ação → rodapé

```text
20 px ou mais
```

Nunca usar blocos de texto encostados apenas para preencher espaço.

## 14. Decoração

Elementos permitidos:

- círculo de fundo;
- pedestal;
- folhas lineares;
- pontos leves;
- vaso neutro;
- linha divisória fina.

Limite recomendado:

```text
2 a 3 elementos decorativos relevantes
```

Regras:

- sempre secundários;
- não cobrir produto;
- não competir com preço;
- não criar bloco colorido vazio;
- remover qualquer decoração que prejudique leitura.

## 15. Campos variáveis do template

Padronizar como campos conceituais:

```text
{{product_name_short}}
{{marketplace}}
{{price}}
{{rating}}
{{discount_percent}}
{{confirmed_feature_1}}
{{confirmed_feature_2}}
{{size_or_volume}}
{{product_image}}
```

Dados não disponíveis devem resultar na remoção do elemento correspondente, e não em texto inventado.

## 16. Procedimento para criar um novo post

1. Duplicar o template mestre.
2. Renomear com data + item ou produto.
3. Substituir a imagem do produto.
4. Atualizar `product_name_short`.
5. Atualizar marketplace.
6. Atualizar preço no padrão `R$ 00.00`.
7. Atualizar avaliação.
8. Atualizar desconto somente quando confirmado.
9. Atualizar informações complementares somente quando confirmadas.
10. Remover blocos sem dados.
11. Conferir espaçamento entre linhas e blocos.
12. Conferir que não existe bloco colorido vazio.
13. Conferir que o produto é o maior foco visual.
14. Conferir `Ofertas Femininas`.
15. Conferir rodapé e `#ad`.
16. Exportar somente após revisão.

## 17. Checklist antes de publicar

- [ ] dimensão correta;
- [ ] produto real e não deformado;
- [ ] `Ofertas Femininas` presente;
- [ ] nome curto legível;
- [ ] marketplace correto;
- [ ] preço correto e no padrão `R$ 35.48`;
- [ ] mesma família tipográfica em `R$` e números;
- [ ] avaliação correta;
- [ ] desconto confirmado, se exibido;
- [ ] nenhuma informação inventada;
- [ ] nenhum bloco colorido vazio;
- [ ] espaçamento vertical adequado;
- [ ] chamada `Link na legenda`;
- [ ] aviso de preço/disponibilidade;
- [ ] `#ad`;
- [ ] nenhuma URL longa na arte;
- [ ] produto é o foco principal.

## 18. Variação Story e Reels

Ao adaptar para 1080 × 1920:

- manter identidade na parte superior ou tela inicial;
- produto central com maior área;
- preço e avaliação na metade inferior;
- chamada para ação acima da área inferior de interface;
- manter margens seguras maiores no topo e no rodapé;
- não copiar mecanicamente o 4:5: redistribuir verticalmente os mesmos blocos.

## 19. Variação Carrossel

Usar o mesmo sistema visual.

Página 1:

```text
Ofertas Femininas + produto + nome curto
```

Páginas intermediárias:

```text
produto/detalhe ou informação confirmada
```

Página comercial:

```text
marketplace + preço + avaliação
```

Página final:

```text
Link na legenda + Ofertas Femininas + aviso
```

Não criar páginas extras sem conteúdo real.

## 20. Regra de governança

O template mestre é o padrão operacional.

Mudanças em:

- fonte;
- paleta;
- posição das zonas;
- formato do cartão;
- padrão de preço;
- chamada para ação;
- assinatura;

devem primeiro ser aprovadas e refletidas na spec e neste manual antes de se tornarem novo padrão.
