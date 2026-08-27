# Sistema Visual — Landing Ofertas Femininas

**Status:** Definido para V1  
**Data:** 2026-08-27  
**Branch:** `docs/feminino-calcados-discovery`

## 1. Objetivo

Definir a direção visual da landing `feminino` a partir da identidade já criada para o projeto **Ofertas Femininas**.

A V1 não deve criar uma nova identidade gráfica. A landing deve reutilizar e adaptar a linguagem visual já presente nos materiais existentes do grupo, preservando reconhecimento de marca entre landing, grupo e peças de oferta.

## 2. Assets de referência

Dois assets já desenvolvidos são as referências visuais oficiais desta etapa:

1. **Banner institucional Ofertas Femininas**
   - ilustração de quatro mulheres com sacolas;
   - fundo creme/rosado claro;
   - linguagem feminina sofisticada;
   - composição leve, com bastante espaço em branco;
   - referência principal para Hero e identidade institucional.

2. **Peça visual de oferta/produto**
   - composição de produto em destaque;
   - títulos serifados em vinho/vermelho escuro;
   - coral/terracota nos destaques e CTAs;
   - fundo creme/rosado;
   - ícones lineares;
   - bloco de preço com borda suave;
   - referência principal para cards, destaques de preço, prova de curadoria e linguagem comercial.

Esses assets são referências de estilo. A implementação não é obrigada a copiá-los literalmente, mas deve manter coerência evidente com eles.

## 3. Princípios visuais

A landing deve transmitir:

- feminino;
- sofisticado;
- acolhedor;
- confiável;
- comercial sem aparência de marketplace genérico;
- sensação de curadoria;
- leitura simples e rápida em dispositivos móveis.

A página deve parecer uma propriedade da marca **Ofertas Femininas**, e não uma página da Shopee, Amazon ou de qualquer marketplace específico.

## 4. Paleta visual

A identidade deve usar principalmente a paleta já perceptível nos assets:

- **creme / rosado muito claro:** fundo principal;
- **coral / terracota:** CTAs, destaques e elementos de ação;
- **vinho / vermelho escuro:** títulos e textos de maior peso visual;
- **rosa suave / pêssego:** fundos secundários, blocos e elementos decorativos;
- **cinza quente / marrom escuro:** textos corridos e informações auxiliares.

Os códigos HEX definitivos não precisam ser fixados nesta etapa. Na implementação, devem ser extraídos ou aproximados a partir dos assets oficiais para manter fidelidade visual.

## 5. Tipografia

A landing deve trabalhar com no máximo duas famílias tipográficas principais.

### 5.1 Títulos

Usar tipografia **serifada elegante**, inspirada nos títulos existentes nas peças.

Aplicações:

- Hero;
- títulos de seção;
- chamadas de destaque;
- preços ou números de forte hierarquia, quando adequado.

### 5.2 Textos de apoio

Usar tipografia **sans-serif limpa e altamente legível**.

Aplicações:

- subtítulos;
- textos de apoio;
- cards;
- informações de produto;
- botões;
- textos operacionais.

A legibilidade mobile tem prioridade sobre reprodução literal da fonte de uma peça gráfica.

## 6. Hero

O banner institucional com as quatro mulheres deve ser a principal referência visual para o Hero.

Estrutura conceitual em desktop:

```text
texto + CTA                         ilustração / asset institucional
```

O bloco de texto deve conter a copy-base já definida no contrato da landing:

**Título**

> Ofertas e cupons para mulheres, não perca tempo procurando

**Subtítulo**

> Receba no WhatsApp ótimos produtos de beleza, moda, calçados, bolsas, cabelos e skincare.

**Gancho**

> Os preços mudam, os cupons acabam e as melhores ofertas podem durar pouco.

**CTA principal**

> Quero receber as ofertas no WhatsApp

Em mobile, a disposição pode ser reorganizada para preservar leitura e conversão, desde que o CTA principal apareça cedo e sem exigir rolagem excessiva.

## 7. Botões e hierarquia de CTAs

### 7.1 CTA principal

O CTA de entrada no WhatsApp é a ação visual dominante da página.

Direção visual:

- preenchimento coral/terracota;
- texto claro;
- contraste forte;
- cantos arredondados;
- largura confortável no mobile;
- possibilidade de uso do ícone do WhatsApp;
- área de toque adequada para dispositivo móvel.

Texto-base:

> Quero receber as ofertas no WhatsApp

### 7.2 CTAs secundários

CTAs de Shopee, ofertas ou cupons devem possuir menor peso visual.

Podem utilizar:

- fundo claro;
- borda coral/terracota;
- texto coral, vinho ou equivalente;
- dimensões menores que o CTA principal.

Hierarquia obrigatória:

```text
WhatsApp > Vitrine Shopee > oferta/cupom individual
```

## 8. Cards de produto e prova de curadoria

A peça visual de oferta é a principal referência para os cards da landing.

Os cards devem adaptar essa linguagem para uma interface web mais leve.

Características desejadas:

- fundo claro;
- cantos arredondados;
- borda delicada;
- produto com área visual relevante;
- nome do produto;
- marketplace identificado quando necessário;
- preço/oferta em destaque quando real e atualizado;
- cupom quando aplicável;
- CTA secundário simples;
- observação discreta de que preço e disponibilidade podem mudar.

A landing não precisa reproduzir toda a quantidade de informação presente numa arte de Instagram. O card web deve ser mais simples, escaneável e responsivo.

## 9. Ícones e elementos decorativos

A linguagem visual deve seguir os assets existentes:

- ícones lineares;
- traços finos;
- formas circulares;
- pequenos corações;
- folhas ou elementos femininos decorativos;
- formas orgânicas em coral/rosa/pêssego;
- decoração usada com moderação.

Os seis macrogrupos podem manter os emojis já definidos:

- 💄 Beleza
- 👗 Moda
- 👠 Calçados
- 👜 Bolsas e acessórios
- 💇‍♀️ Cabelos
- 🧴 Skincare

## 10. Fundos e ritmo visual

A página deve alternar fundos suaves para separar blocos sem criar contraste agressivo.

Direção recomendada:

```text
creme claro
    ↓
rosa/pêssego muito leve
    ↓
creme claro
```

Evitar grandes blocos escuros.

Vinho/vermelho escuro deve funcionar principalmente como cor de título, destaque ou detalhe, não como fundo dominante de grandes áreas da landing.

## 11. Seção de confiança

Os elementos de confiança devem seguir a mesma linguagem gráfica da marca e podem ser apresentados como pequenas faixas/cards/ícones.

Mensagens já definidas:

> 💎 Ofertas e cupons apenas de produtos ORIGINAIS e de lojas CONFIÁVEIS

> 🌙 Seu descanso é respeitado. As mensagens param à noite e só voltam pela manhã. O grupo fica em silêncio aproximadamente entre 21h10 e 8h.

> 🔕 Só administradores enviam mensagens

Essas informações devem parecer parte da proposta de valor e não texto jurídico de rodapé.

## 12. Prova de curadoria

A seção de exemplos reais deve parecer uma extensão visual natural das peças de oferta existentes.

Título-base possível:

> Veja o tipo de oferta que selecionamos

A V1 pode usar aproximadamente 3 a 4 cards reais.

Cada exemplo pode apresentar:

- imagem;
- nome;
- preço/oferta/cupom quando aplicável;
- marketplace;
- CTA secundário.

Depois dos exemplos pode existir:

> Ver nossa seleção na Shopee

Esse botão permanece secundário em relação ao CTA de WhatsApp.

## 13. Relação com marketplaces

Shopee e Amazon são fontes das oportunidades e destinos comerciais, não a identidade principal da landing.

A marca visual dominante deve continuar sendo **Ofertas Femininas**.

A landing não deve parecer:

- uma loja Shopee;
- uma loja Amazon;
- um agregador genérico de preços;
- uma reprodução do layout de qualquer marketplace.

## 14. Responsividade

A implementação deve ser mobile-first.

Regras gerais:

- CTA principal visível cedo;
- textos sem linhas excessivamente longas;
- cards empilháveis ou em carrossel/grid responsivo;
- imagens redimensionadas sem perda da composição principal;
- botões com área de toque confortável;
- títulos serifados não podem prejudicar leitura em telas pequenas;
- elementos decorativos não devem competir com copy ou CTA.

## 15. Regra de fidelidade visual

A implementação deve reutilizar a linguagem gráfica já criada em vez de criar uma identidade paralela.

A fidelidade deve ser percebida principalmente por:

- paleta;
- contraste;
- tipografia;
- fundos;
- estilo de ilustração;
- tratamento de cards;
- formas e ícones;
- hierarquia dos CTAs.

Reprodução pixel a pixel dos assets não é requisito.

## 16. Critérios de aceite visual

A direção visual será considerada respeitada quando:

1. a landing for reconhecivelmente pertencente à identidade Ofertas Femininas;
2. o Hero reutilizar ou se inspirar diretamente no banner institucional;
3. cards e prova de curadoria seguirem a linguagem da peça de oferta;
4. a paleta permaneça dentro da família creme, coral/terracota, vinho e rosa/pêssego;
5. títulos usem linguagem serifada elegante e textos uma sans-serif legível;
6. o CTA WhatsApp seja visualmente dominante;
7. Shopee/Amazon permaneçam visualmente subordinadas à marca Ofertas Femininas;
8. a página funcione adequadamente em mobile e desktop;
9. a decoração não reduza a legibilidade nem a conversão;
10. a landing não crie uma identidade gráfica nova desconectada dos materiais existentes.

## 17. Wireframe oficial

O wireframe desktop/mobile da V1 foi confirmado e está documentado em:

`docs/landing-feminino-wireframe.md`

Esse documento passa a ser a referência para ordem das seções, disposição dos blocos, repetição dos CTAs, comportamento mobile e apresentação da prova de curadoria.

A ordem principal confirmada é:

```text
Hero
  ↓
Faixa de confiança
  ↓
Macrogrupos
  ↓
Como funciona
  ↓
Prova de curadoria / exemplos reais
  ↓
Vitrine Shopee
  ↓
Urgência real
  ↓
CTA final
  ↓
Rodapé
```

O CTA fixo no mobile permanece como recurso opcional a ser validado durante a implementação, conforme critérios descritos no wireframe.

## 18. Próxima etapa

Com contrato funcional, copy, sistema visual e wireframe confirmados, a próxima etapa é validar o ambiente Hostinger e definir o mecanismo técnico da hospedagem e da rota `/go/whatsapp/{nicho}` antes de iniciar a implementação em HTML/CSS.
