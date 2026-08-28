# Sistema Visual â€” Landing Ofertas Femininas

**Status:** Definido para V1
**Data:** 2026-08-27
**Branch:** `docs/feminino-calcados-discovery`

## 1. Objetivo

Definir a direÃ§Ã£o visual da landing `feminino` a partir da identidade jÃ¡ criada para o projeto **Ofertas Femininas**.

A V1 nÃ£o deve criar uma nova identidade grÃ¡fica. A landing deve reutilizar e adaptar a linguagem visual jÃ¡ presente nos materiais existentes do grupo, preservando reconhecimento de marca entre landing, grupo e peÃ§as de oferta.

## 2. Assets de referÃªncia

Dois assets jÃ¡ desenvolvidos sÃ£o as referÃªncias visuais oficiais desta etapa:

1. **Banner institucional Ofertas Femininas**
   - ilustraÃ§Ã£o de quatro mulheres com sacolas;
   - fundo creme/rosado claro;
   - linguagem feminina sofisticada;
   - composiÃ§Ã£o leve, com bastante espaÃ§o em branco;
   - referÃªncia principal para Hero e identidade institucional.

2. **PeÃ§a visual de oferta/produto**
   - composiÃ§Ã£o de produto em destaque;
   - tÃ­tulos serifados em vinho/vermelho escuro;
   - coral/terracota nos destaques e CTAs;
   - fundo creme/rosado;
   - Ã­cones lineares;
   - bloco de preÃ§o com borda suave;
   - referÃªncia principal para cards, destaques de preÃ§o, prova de curadoria e linguagem comercial.

Esses assets sÃ£o referÃªncias de estilo. A implementaÃ§Ã£o nÃ£o Ã© obrigada a copiÃ¡-los literalmente, mas deve manter coerÃªncia evidente com eles.

## 3. PrincÃ­pios visuais

A landing deve transmitir:

- feminino;
- sofisticado;
- acolhedor;
- confiÃ¡vel;
- comercial sem aparÃªncia de marketplace genÃ©rico;
- sensaÃ§Ã£o de curadoria;
- leitura simples e rÃ¡pida em dispositivos mÃ³veis.

A pÃ¡gina deve parecer uma propriedade da marca **Ofertas Femininas**, e nÃ£o uma pÃ¡gina da Shopee, Amazon ou de qualquer marketplace especÃ­fico.

## 4. Paleta visual

A identidade deve usar principalmente a paleta jÃ¡ perceptÃ­vel nos assets:

- **creme / rosado muito claro:** fundo principal;
- **coral / terracota:** CTAs, destaques e elementos de aÃ§Ã£o;
- **vinho / vermelho escuro:** tÃ­tulos e textos de maior peso visual;
- **rosa suave / pÃªssego:** fundos secundÃ¡rios, blocos e elementos decorativos;
- **cinza quente / marrom escuro:** textos corridos e informaÃ§Ãµes auxiliares.

Os cÃ³digos HEX definitivos nÃ£o precisam ser fixados nesta etapa. Na implementaÃ§Ã£o, devem ser extraÃ­dos ou aproximados a partir dos assets oficiais para manter fidelidade visual.

## 5. Tipografia

A landing deve trabalhar com no mÃ¡ximo duas famÃ­lias tipogrÃ¡ficas principais.

### 5.1 TÃ­tulos

Usar tipografia **serifada elegante**, inspirada nos tÃ­tulos existentes nas peÃ§as.

AplicaÃ§Ãµes:

- Hero;
- tÃ­tulos de seÃ§Ã£o;
- chamadas de destaque;
- preÃ§os ou nÃºmeros de forte hierarquia, quando adequado.

### 5.2 Textos de apoio

Usar tipografia **sans-serif limpa e altamente legÃ­vel**.

AplicaÃ§Ãµes:

- subtÃ­tulos;
- textos de apoio;
- cards;
- informaÃ§Ãµes de produto;
- botÃµes;
- textos operacionais.

A legibilidade mobile tem prioridade sobre reproduÃ§Ã£o literal da fonte de uma peÃ§a grÃ¡fica.

## 6. Hero

O banner institucional com as quatro mulheres deve ser a principal referÃªncia visual para o Hero.

Estrutura conceitual em desktop:

```text
texto + CTA                         ilustraÃ§Ã£o / asset institucional
```

O bloco de texto deve conter a copy-base jÃ¡ definida no contrato da landing:

**TÃ­tulo**

> Ofertas e cupons para mulheres, nÃ£o perca tempo procurando

**SubtÃ­tulo**

> Receba no WhatsApp Ã³timos produtos de beleza, moda, calÃ§ados, bolsas, cabelos e skincare.

**Gancho**

> Os preÃ§os mudam, os cupons acabam e as melhores ofertas podem durar pouco.

**CTA principal**

> Quero receber as ofertas no WhatsApp

Em mobile, a disposiÃ§Ã£o pode ser reorganizada para preservar leitura e conversÃ£o, desde que o CTA principal apareÃ§a cedo e sem exigir rolagem excessiva.

## 7. BotÃµes e hierarquia de CTAs

### 7.1 CTA principal

O CTA de entrada no WhatsApp Ã© a aÃ§Ã£o visual dominante da pÃ¡gina.

DireÃ§Ã£o visual:

- preenchimento coral/terracota;
- texto claro;
- contraste forte;
- cantos arredondados;
- largura confortÃ¡vel no mobile;
- possibilidade de uso do Ã­cone do WhatsApp;
- Ã¡rea de toque adequada para dispositivo mÃ³vel.

Texto-base:

> Quero receber as ofertas no WhatsApp

### 7.2 CTAs secundÃ¡rios

CTAs de Shopee, ofertas ou cupons devem possuir menor peso visual.

Podem utilizar:

- fundo claro;
- borda coral/terracota;
- texto coral, vinho ou equivalente;
- dimensÃµes menores que o CTA principal.

Hierarquia obrigatÃ³ria:

```text
WhatsApp > Vitrine Shopee > oferta/cupom individual
```

## 8. Cards de produto e prova de curadoria

A peÃ§a visual de oferta Ã© a principal referÃªncia para os cards da landing.

Os cards devem adaptar essa linguagem para uma interface web mais leve.

CaracterÃ­sticas desejadas:

- fundo claro;
- cantos arredondados;
- borda delicada;
- produto com Ã¡rea visual relevante;
- nome do produto;
- marketplace identificado quando necessÃ¡rio;
- preÃ§o/oferta em destaque quando real e atualizado;
- cupom quando aplicÃ¡vel;
- CTA secundÃ¡rio simples;
- observaÃ§Ã£o discreta de que preÃ§o e disponibilidade podem mudar.

A landing nÃ£o precisa reproduzir toda a quantidade de informaÃ§Ã£o presente numa arte de Instagram. O card web deve ser mais simples, escaneÃ¡vel e responsivo.

## 9. Ãcones e elementos decorativos

A linguagem visual deve seguir os assets existentes:

- Ã­cones lineares;
- traÃ§os finos;
- formas circulares;
- pequenos coraÃ§Ãµes;
- folhas ou elementos femininos decorativos;
- formas orgÃ¢nicas em coral/rosa/pÃªssego;
- decoraÃ§Ã£o usada com moderaÃ§Ã£o.

Os seis macrogrupos podem manter os emojis jÃ¡ definidos:

- ðŸ’„ Beleza
- ðŸ‘— Moda
- ðŸ‘  CalÃ§ados
- ðŸ‘œ Bolsas e acessÃ³rios
- ðŸ’‡â€â™€ï¸ Cabelos
- ðŸ§´ Skincare

## 10. Fundos e ritmo visual

A pÃ¡gina deve alternar fundos suaves para separar blocos sem criar contraste agressivo.

DireÃ§Ã£o recomendada:

```text
creme claro
    â†“
rosa/pÃªssego muito leve
    â†“
creme claro
```

Evitar grandes blocos escuros.

Vinho/vermelho escuro deve funcionar principalmente como cor de tÃ­tulo, destaque ou detalhe, nÃ£o como fundo dominante de grandes Ã¡reas da landing.

## 11. SeÃ§Ã£o de confianÃ§a

Os elementos de confianÃ§a devem seguir a mesma linguagem grÃ¡fica da marca e podem ser apresentados como pequenas faixas/cards/Ã­cones.

Mensagens jÃ¡ definidas:

> ðŸ’Ž Ofertas e cupons apenas de produtos ORIGINAIS e de lojas CONFIÃVEIS

> ðŸŒ™ Seu descanso Ã© respeitado. As mensagens param Ã  noite e sÃ³ voltam pela manhÃ£. O grupo fica em silÃªncio aproximadamente entre 21h10 e 8h.

> ðŸ”• SÃ³ administradores enviam mensagens

Essas informaÃ§Ãµes devem parecer parte da proposta de valor e nÃ£o texto jurÃ­dico de rodapÃ©.

## 12. Prova de curadoria

A seÃ§Ã£o de exemplos reais deve parecer uma extensÃ£o visual natural das peÃ§as de oferta existentes.

TÃ­tulo-base possÃ­vel:

> Veja o tipo de oferta que selecionamos

A V1 pode usar aproximadamente 3 a 4 cards reais.

Cada exemplo pode apresentar:

- imagem;
- nome;
- preÃ§o/oferta/cupom quando aplicÃ¡vel;
- marketplace;
- CTA secundÃ¡rio.

Depois dos exemplos pode existir:

> Ver nossa seleÃ§Ã£o na Shopee

Esse botÃ£o permanece secundÃ¡rio em relaÃ§Ã£o ao CTA de WhatsApp.

## 13. RelaÃ§Ã£o com marketplaces

Shopee e Amazon sÃ£o fontes das oportunidades e destinos comerciais, nÃ£o a identidade principal da landing.

A marca visual dominante deve continuar sendo **Ofertas Femininas**.

A landing nÃ£o deve parecer:

- uma loja Shopee;
- uma loja Amazon;
- um agregador genÃ©rico de preÃ§os;
- uma reproduÃ§Ã£o do layout de qualquer marketplace.

## 14. Responsividade

A implementaÃ§Ã£o deve ser mobile-first.

Regras gerais:

- CTA principal visÃ­vel cedo;
- textos sem linhas excessivamente longas;
- cards empilhÃ¡veis ou em carrossel/grid responsivo;
- imagens redimensionadas sem perda da composiÃ§Ã£o principal;
- botÃµes com Ã¡rea de toque confortÃ¡vel;
- tÃ­tulos serifados nÃ£o podem prejudicar leitura em telas pequenas;
- elementos decorativos nÃ£o devem competir com copy ou CTA.

## 15. Regra de fidelidade visual

A implementaÃ§Ã£o deve reutilizar a linguagem grÃ¡fica jÃ¡ criada em vez de criar uma identidade paralela.

A fidelidade deve ser percebida principalmente por:

- paleta;
- contraste;
- tipografia;
- fundos;
- estilo de ilustraÃ§Ã£o;
- tratamento de cards;
- formas e Ã­cones;
- hierarquia dos CTAs.

ReproduÃ§Ã£o pixel a pixel dos assets nÃ£o Ã© requisito.

## 16. CritÃ©rios de aceite visual

A direÃ§Ã£o visual serÃ¡ considerada respeitada quando:

1. a landing for reconhecivelmente pertencente Ã  identidade Ofertas Femininas;
2. o Hero reutilizar ou se inspirar diretamente no banner institucional;
3. cards e prova de curadoria seguirem a linguagem da peÃ§a de oferta;
4. a paleta permaneÃ§a dentro da famÃ­lia creme, coral/terracota, vinho e rosa/pÃªssego;
5. tÃ­tulos usem linguagem serifada elegante e textos uma sans-serif legÃ­vel;
6. o CTA WhatsApp seja visualmente dominante;
7. Shopee/Amazon permaneÃ§am visualmente subordinadas Ã  marca Ofertas Femininas;
8. a pÃ¡gina funcione adequadamente em mobile e desktop;
9. a decoraÃ§Ã£o nÃ£o reduza a legibilidade nem a conversÃ£o;
10. a landing nÃ£o crie uma identidade grÃ¡fica nova desconectada dos materiais existentes.

## 17. Wireframe oficial

O wireframe desktop/mobile da V1 foi confirmado e estÃ¡ documentado em:

`docs/landing-feminino-wireframe.md`

Esse documento passa a ser a referÃªncia para ordem das seÃ§Ãµes, disposiÃ§Ã£o dos blocos, repetiÃ§Ã£o dos CTAs, comportamento mobile e apresentaÃ§Ã£o da prova de curadoria.

A ordem principal confirmada Ã©:

```text
Hero
  â†“
Faixa de confianÃ§a
  â†“
Macrogrupos
  â†“
Como funciona
  â†“
Prova de curadoria / exemplos reais
  â†“
Vitrine Shopee
  â†“
UrgÃªncia real
  â†“
CTA final
  â†“
RodapÃ©
```

O CTA fixo no mobile permanece como recurso opcional a ser validado durante a implementaÃ§Ã£o, conforme critÃ©rios descritos no wireframe.

## 18. PrÃ³xima etapa

Com contrato funcional, copy, sistema visual e wireframe confirmados, a prÃ³xima etapa Ã© validar o ambiente Hostinger e definir o mecanismo tÃ©cnico da hospedagem e da rota `/go/whatsapp/{nicho}` antes de iniciar a implementaÃ§Ã£o em HTML/CSS.
