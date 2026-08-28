# Contrato V1 â€” Landing + Link WhatsApp + UTM

**Status:** Decidido para V1
**VersÃ£o do contrato:** 1.6
**Data:** 2026-08-26
**Branch:** `docs/feminino-calcados-discovery`

## 1. Objetivo

Definir o contrato funcional mÃ­nimo da primeira versÃ£o da landing page usada para captar usuÃ¡rios para grupos de ofertas no WhatsApp.

A V1 deve resolver quatro responsabilidades:

1. apresentar uma landing page pÃºblica e mobile-first por nicho;
2. direcionar o usuÃ¡rio para o grupo de WhatsApp correspondente ao nicho por uma URL controlada pelo projeto;
3. receber e preservar parÃ¢metros UTM para identificar a origem do trÃ¡fego;
4. nascer com convenÃ§Ã£o de URL compatÃ­vel com mÃºltiplos nichos, sem exigir mÃºltiplos grupos simultÃ¢neos dentro do mesmo nicho na V1.

GA4, Meta Pixel, banco de dados, Supabase, roteamento automÃ¡tico entre vÃ¡rios grupos do mesmo nicho e mediÃ§Ã£o de entrada efetiva no grupo ficam fora deste contrato V1.

A primeira implementaÃ§Ã£o da V1 serÃ¡ exclusivamente para o nicho feminino.

## 2. Escopo funcional da V1

Fluxo oficial:

```text
AnÃºncio / Instagram / outro canal
              |
              | URL da landing do nicho + UTM
              v
Landing pÃºblica do nicho
              |
              | CTA principal
              v
Rota controlada /go/whatsapp/{nicho}
              |
              v
Link de convite do grupo WhatsApp ativo daquele nicho
```

Exemplo inicial:

```text
/feminino
    |
    v
/go/whatsapp/feminino
    |
    v
grupo feminino ativo
```

Exemplo futuro:

```text
/mae-bebe
    |
    v
/go/whatsapp/mae-bebe
    |
    v
grupo mae-bebe ativo
```

## 3. Contrato da landing page

### 3.1 Entrada

Cada nicho deve possuir uma URL pÃºblica prÃ³pria no domÃ­nio do projeto.

ConvenÃ§Ã£o:

```text
/{nicho}
```

Exemplos:

```text
https://seudominio.com.br/feminino
https://seudominio.com.br/mae-bebe
```

A URL poderÃ¡ receber parÃ¢metros UTM.

Exemplo:

```text
https://seudominio.com.br/feminino?utm_source=instagram&utm_medium=paid&utm_campaign=grupo_ofertas_femininas&utm_content=reels_01
```

### 3.2 SaÃ­da principal

A conversÃ£o obrigatÃ³ria da V1 Ã© o clique no CTA principal para entrada no grupo do nicho correspondente.

O CTA nÃ£o deve apontar diretamente para o convite permanente do WhatsApp. Deve apontar para:

```text
/go/whatsapp/{nicho}
```

Exemplo:

```text
https://seudominio.com.br/go/whatsapp/feminino
```

### 3.3 PÃºblico de referÃªncia da landing feminina

A primeira landing deve falar prioritariamente com mulheres de aproximadamente 30 a 55 anos.

Essa faixa Ã© referÃªncia para linguagem, visual e escolha de exemplos. NÃ£o Ã© uma restriÃ§Ã£o de acesso ao grupo.

### 3.4 Macrogrupos exibidos na landing feminina

A landing feminina nÃ£o deve expor toda a taxonomia tÃ©cnica interna de subnichos.

Para comunicaÃ§Ã£o com a usuÃ¡ria final, a cobertura do nicho feminino deve ser apresentada exatamente com estes seis macrogrupos:

- ðŸ’„ Beleza
- ðŸ‘— Moda
- ðŸ‘  CalÃ§ados
- ðŸ‘œ Bolsas e acessÃ³rios
- ðŸ’‡â€â™€ï¸ Cabelos
- ðŸ§´ Skincare

Esses macrogrupos sÃ£o uma camada de apresentaÃ§Ã£o da landing. Eles nÃ£o substituem nem redefinem a taxonomia tÃ©cnica usada por catÃ¡logo, discovery, scoring ou seleÃ§Ã£o de ofertas.

## 4. Copy consolidada da landing feminina

Os textos desta seÃ§Ã£o foram definidos durante o desenho da V1 e estÃ£o prÃ³ximos da copy de produÃ§Ã£o. Devem ser usados como base na implementaÃ§Ã£o. Ajustes posteriores de pontuaÃ§Ã£o, hierarquia visual ou pequenas variaÃ§Ãµes de redaÃ§Ã£o podem ser feitos sem alterar a promessa ou as regras de negÃ³cio.

### 4.1 Hero

**TÃ­tulo**

> Ofertas e cupons para mulheres, nÃ£o perca tempo procurando

**SubtÃ­tulo**

> Receba no WhatsApp Ã³timos produtos de beleza, moda, calÃ§ados, bolsas, cabelos e skincare.

**Gancho**

> Os preÃ§os mudam, os cupons acabam e as melhores ofertas podem durar pouco.

**CTA principal**

> Quero receber as ofertas no WhatsApp

### 4.2 Mensagem principal de confianÃ§a

Esta mensagem deve receber destaque visual e nÃ£o ser tratada apenas como observaÃ§Ã£o de rodapÃ©:

> ðŸ’Ž Ofertas e cupons apenas de produtos ORIGINAIS e de lojas CONFIÃVEIS

### 4.3 Como funciona â€” copy-base

A seÃ§Ã£o deve explicar de maneira simples o que a participante recebe e como o grupo funciona.

**ðŸ”Ž NÃ³s fazemos a curadoria**

> Selecionamos produtos femininos de beleza, moda, calÃ§ados, bolsas, cabelos e skincare, priorizando boas ofertas e cupons.

**ðŸ’Ž Produtos e lojas confiÃ¡veis**

> Ofertas e cupons apenas de produtos originais e de lojas confiÃ¡veis.

**ðŸ“² VocÃª recebe direto no WhatsApp**

> As ofertas sÃ£o enviadas ao longo do dia, para vocÃª nÃ£o precisar ficar procurando promoÃ§Ãµes.

**ðŸ·ï¸ Oferta + preÃ§o + cupom + link**

> Cada mensagem traz as informaÃ§Ãµes necessÃ¡rias para avaliar rapidamente a oportunidade e acessar a oferta.

**ðŸŒ™ Seu descanso Ã© respeitado**

> As mensagens param Ã  noite e sÃ³ voltam pela manhÃ£. O grupo fica em silÃªncio aproximadamente entre 21h10 e 8h.

**ðŸ”• SÃ³ administradores enviam mensagens**

> Somente administradores enviam mensagens no grupo, evitando conversas, correntes ou mensagens de participantes.

### 4.4 TensÃ£o de comunicaÃ§Ã£o

A tensÃ£o da landing deve partir de uma situaÃ§Ã£o real:

```text
A usuÃ¡ria nÃ£o quer perder tempo procurando promoÃ§Ãµes
        +
preÃ§os mudam, cupons acabam e estoque pode terminar
        â†“
o grupo faz a curadoria e avisa pelo WhatsApp
```

FormulaÃ§Ãµes jÃ¡ discutidas e aprovadas como referÃªncia:

> Quando aparece uma boa oferta, vocÃª precisa saber a tempo.

> Boas ofertas nÃ£o ficam disponÃ­veis para sempre. Entre no grupo e receba nossos achados e cupons enquanto ainda estÃ£o valendo.

> NÃ³s procuramos. VocÃª recebe quando aparece algo que vale a pena.

Essas formulaÃ§Ãµes sÃ£o referÃªncias de copy e podem ser usadas em seÃ§Ãµes secundÃ¡rias, desde que nÃ£o criem promessa de disponibilidade garantida.

### 4.5 UrgÃªncia permitida

A copy pode criar senso de urgÃªncia exclusivamente com base em condiÃ§Ãµes reais:

- preÃ§o promocional pode mudar;
- cupom pode expirar ou atingir limite de uso;
- estoque pode acabar;
- oferta pode deixar de estar disponÃ­vel.

NÃ£o usar:

- escassez artificial;
- contagem regressiva fictÃ­cia;
- prazo inventado;
- afirmaÃ§Ã£o de Ãºltimas unidades sem evidÃªncia;
- qualquer urgÃªncia que nÃ£o corresponda a uma condiÃ§Ã£o real verificÃ¡vel.

### 4.6 CTA final

A pÃ¡gina deve repetir o objetivo principal prÃ³ximo ao final.

Copy-base:

> Quer receber essas ofertas todos os dias?

CTA-base:

> Quero receber as ofertas no WhatsApp

O CTA final pode usar variaÃ§Ã£o equivalente, como:

> Quero entrar no grupo

O destino permanece `/go/whatsapp/feminino` com preservaÃ§Ã£o das UTMs recebidas.

## 5. Prova de curadoria e Vitrine Shopee

### 5.1 FunÃ§Ã£o da Vitrine Shopee

A Vitrine do Afiliado Shopee, ou coleÃ§Ã£o curada equivalente, pode ser utilizada como prova concreta da curadoria realizada pelo projeto.

Ela deve permitir que a visitante veja o tipo de produto selecionado antes de entrar no grupo.

A Vitrine Shopee Ã© um elemento secundÃ¡rio. NÃ£o deve competir visualmente com o CTA principal de entrada no WhatsApp.

### 5.2 Copy-base para a prova de curadoria

FormulaÃ§Ãµes jÃ¡ discutidas:

> Quer ver o tipo de oferta que selecionamos?

CTA secundÃ¡rio:

> Ver nossa seleÃ§Ã£o na Shopee

TambÃ©m podem existir chamadas especÃ­ficas, por exemplo:

> CalÃ§ados que valem a pena

CTA:

> Ver seleÃ§Ã£o de calÃ§ados

E:

> Cupons e achados

CTA:

> Ver seleÃ§Ã£o na Shopee

### 5.3 Exemplos reais de ofertas

A landing pode apresentar aproximadamente 3 a 4 exemplos visuais de ofertas ou categorias curadas.

Modelo conceitual:

```text
Ofertas que vocÃª pode receber no grupo

[Produto de beleza]
De R$ XX,XX por R$ XX,XX
[Ver oferta]

[CalÃ§ado feminino]
Oferta em destaque
[Ver ofertas de calÃ§ados]

[Cupom Shopee]
Cupom disponÃ­vel
[Pegar cupom]
```

Os dados exibidos devem corresponder Ã  oferta real no momento em que forem publicados. A landing nÃ£o deve manter preÃ§o, desconto, estoque ou validade fictÃ­cios.

CTAs secundÃ¡rios permitidos:

- `Ver nossa seleÃ§Ã£o na Shopee`;
- `Ver oferta`;
- `Pegar cupom`;
- `Ver ofertas de calÃ§ados`;
- `Ver seleÃ§Ã£o de calÃ§ados`;
- `Ver seleÃ§Ã£o na Shopee`.

O CTA dominante da pÃ¡gina continua sendo a entrada no grupo de WhatsApp.

## 6. Regras pÃºblicas de operaÃ§Ã£o

### 6.1 NÃ£o prometer quantidade fixa de mensagens

A landing nÃ£o deve informar quantidade diÃ¡ria fixa de mensagens.

A cadÃªncia operacional pode evoluir sem exigir mudanÃ§a da promessa pÃºblica da landing.

### 6.2 NÃ£o publicar horÃ¡rios individuais de triggers

A landing nÃ£o deve informar horÃ¡rios detalhados de cada trigger ou disparo.

O comportamento pÃºblico deve ser descrito simplesmente como recebimento de ofertas ao longo do dia.

### 6.3 PerÃ­odo de silÃªncio

A operaÃ§Ã£o possui Ãºltimo trigger Ã s `21:00`, podendo haver envio residual por atÃ© aproximadamente 10 minutos.

Por isso, a landing nÃ£o deve afirmar silÃªncio a partir de 21h em ponto.

Contrato pÃºblico atual:

> O grupo fica em silÃªncio aproximadamente entre 21h10 e 8h.

Esse horÃ¡rio pode evoluir futuramente. Enquanto a polÃ­tica estiver vigente, a landing nÃ£o deve publicar promessa conflitante com ela.

### 6.4 Somente administradores enviam mensagens

A landing deve comunicar que somente administradores enviam mensagens no grupo.

Esse ponto funciona como elemento de confianÃ§a e deixa claro que o grupo nÃ£o funciona como chat aberto entre participantes.

## 7. Contrato do link WhatsApp

### 7.1 Regra principal

Nenhum anÃºncio, bio, QR code ou material externo deve depender diretamente do convite permanente de um grupo especÃ­fico quando puder utilizar a landing ou a rota controlada do nicho.

```text
URL pÃºblica do nicho
        |
        v
/go/whatsapp/{nicho}
        |
        v
link real do WhatsApp daquele nicho
```

### 7.2 Destino da V1

Na V1 haverÃ¡ apenas um destino ativo por nicho.

NÃ£o haverÃ¡ balanceamento, escolha automÃ¡tica ou distribuiÃ§Ã£o entre vÃ¡rios grupos dentro do mesmo nicho.

A arquitetura deve permitir evoluÃ§Ã£o futura sem quebra de URL:

```text
/go/whatsapp/feminino
        |
        v
router feminino
        |
        +--> Grupo Feminino 01
        +--> Grupo Feminino 02
        +--> Grupo Feminino 03
```

### 7.3 Troca do grupo

Deve ser possÃ­vel alterar o link real do grupo sem alterar:

- a URL da landing;
- URLs utilizadas em anÃºncios;
- links em bio;
- QR codes;
- materiais externos que utilizem a rota controlada.

### 7.4 Redirect

Ao acessar `/go/whatsapp/{nicho}`, o usuÃ¡rio deve ser redirecionado para o convite configurado daquele nicho.

A V1 usa HTTP `302`.

```text
GET /go/whatsapp/{nicho}
        |
        v
resolver configuracao do nicho
        |
        v
validar configuracao
        |
        +-- invalida/ausente --> falha controlada
        |
        v
HTTP 302
        |
        v
URL do grupo ativo
```

### 7.5 ConfiguraÃ§Ã£o Ãºnica por nicho

ConvenÃ§Ã£o da V1:

```text
WHATSAPP_GROUP_URL_<NICHO>
```

Exemplo inicial:

```text
WHATSAPP_GROUP_URL_FEMININO
```

O convite nÃ£o deve ficar duplicado em HTML, JavaScript, anÃºncios ou mÃºltiplos arquivos de configuraÃ§Ã£o.

### 7.6 ValidaÃ§Ã£o e falha controlada

Antes do redirect, a implementaÃ§Ã£o deve verificar que a configuraÃ§Ã£o:

- existe;
- nÃ£o estÃ¡ vazia;
- Ã© HTTPS;
- possui forma/domÃ­nio de convite do WhatsApp aceito pela implementaÃ§Ã£o.

Se estiver ausente ou invÃ¡lida:

- nÃ£o redirecionar para endereÃ§o desconhecido;
- nÃ£o usar grupo antigo como fallback silencioso;
- nÃ£o usar grupo de outro nicho;
- nÃ£o expor detalhes internos;
- retornar resposta/pÃ¡gina de erro controlada.

### 7.7 Ambiente

A V1 deve possuir configuraÃ§Ã£o de produÃ§Ã£o para cada nicho implantado.

Staging separado nÃ£o Ã© requisito obrigatÃ³rio da V1.

## 8. Contrato UTM

### 8.1 ParÃ¢metros suportados

A landing deve aceitar:

- `utm_source`;
- `utm_medium`;
- `utm_campaign`;
- `utm_content`;
- `utm_term`.

UTM Ã© opcional e nunca pode impedir acesso Ã  landing ou ao WhatsApp.

### 8.2 PreservaÃ§Ã£o

Os parÃ¢metros recebidos devem ser preservados atÃ© a rota de saÃ­da.

```text
/feminino?utm_source=instagram&utm_medium=paid&utm_campaign=grupo_feminino&utm_content=reels_01
        |
        v
/go/whatsapp/feminino?utm_source=instagram&utm_medium=paid&utm_campaign=grupo_feminino&utm_content=reels_01
        |
        v
HTTP 302 -> URL do grupo feminino ativo
```

A V1 nÃ£o exige persistÃªncia das UTMs nem sua propagaÃ§Ã£o para `chat.whatsapp.com`.

### 8.3 ConvenÃ§Ã£o inicial

Para campanhas pagas da Meta:

```text
utm_source=instagram | facebook
utm_medium=paid
utm_campaign=<nome_da_campanha>
utm_content=<identificador_do_criativo>
```

Exemplo:

```text
utm_source=instagram
utm_medium=paid
utm_campaign=grupo_ofertas_femininas
utm_content=reels_01
```

Valores desconhecidos nÃ£o devem ser bloqueados e parÃ¢metros ausentes nÃ£o invalidam a URL.

## 9. Regras de negÃ³cio consolidadas

### RB-01 â€” Uma aÃ§Ã£o principal

A landing deve priorizar a entrada no grupo de WhatsApp.

### RB-02 â€” Desacoplamento do grupo

O convite real do WhatsApp nÃ£o deve ser a URL pÃºblica permanente utilizada em campanhas.

### RB-03 â€” Um grupo ativo por nicho

A V1 trabalha com um Ãºnico destino ativo por nicho.

### RB-04 â€” Arquitetura multi-nicho

Usar `/{nicho}` e `/go/whatsapp/{nicho}` desde a V1.

### RB-05 â€” EvoluÃ§Ã£o sem quebra de URL

MÃºltiplos grupos futuros do mesmo nicho poderÃ£o ser colocados atrÃ¡s da mesma rota pÃºblica.

### RB-06 â€” UTM opcional e preservada

A ausÃªncia de UTM nÃ£o impede o fluxo; quando presente, deve chegar atÃ© `/go/whatsapp/{nicho}`.

### RB-07 â€” Redirect temporÃ¡rio

Usar HTTP `302`.

### RB-08 â€” ConfiguraÃ§Ã£o Ãºnica

O grupo ativo Ã© configurado em uma Ãºnica fonte por nicho.

### RB-09 â€” Falha controlada

ConfiguraÃ§Ã£o ausente ou invÃ¡lida nÃ£o pode gerar redirect arbitrÃ¡rio ou fallback silencioso.

### RB-10 â€” Mobile-first

O fluxo deve funcionar primeiro em dispositivos mÃ³veis, sem impedir uso em desktop.

### RB-11 â€” Curadoria Shopee como prova secundÃ¡ria

A Vitrine Shopee pode comprovar o tipo de curadoria, mas nÃ£o substitui o CTA principal.

### RB-12 â€” UrgÃªncia real

SÃ³ usar urgÃªncia baseada em preÃ§o, cupom, estoque ou disponibilidade reais.

### RB-13 â€” PÃºblico feminino

A comunicaÃ§Ã£o da primeira landing Ã© orientada principalmente a mulheres de aproximadamente 30 a 55 anos.

### RB-14 â€” Macrogrupos pÃºblicos

Exibir exatamente:

- ðŸ’„ Beleza
- ðŸ‘— Moda
- ðŸ‘  CalÃ§ados
- ðŸ‘œ Bolsas e acessÃ³rios
- ðŸ’‡â€â™€ï¸ Cabelos
- ðŸ§´ Skincare

### RB-15 â€” Produtos originais e lojas confiÃ¡veis

Comunicar explicitamente a promessa de curadoria de produtos originais e lojas confiÃ¡veis.

### RB-16 â€” Sem promessa de volume diÃ¡rio

NÃ£o publicar quantidade fixa de mensagens por dia.

### RB-17 â€” Sem horÃ¡rios de triggers

NÃ£o publicar a grade de disparos.

### RB-18 â€” SilÃªncio noturno

Comunicar silÃªncio aproximadamente entre 21h10 e 8h enquanto essa for a polÃ­tica operacional vigente.

### RB-19 â€” Grupo fechado para participantes

Somente administradores enviam mensagens.

## 10. Requisitos nÃ£o funcionais mÃ­nimos

A V1 deve:

- utilizar HTTPS;
- carregar rapidamente em conexÃ£o mÃ³vel;
- evitar dependÃªncias desnecessÃ¡rias;
- nÃ£o exigir login;
- nÃ£o exigir banco de dados;
- nÃ£o exigir cookies para funcionar;
- permitir versionamento integral no Git;
- permitir alteraÃ§Ã£o do destino WhatsApp sem alterar a URL pÃºblica da campanha;
- centralizar o destino de cada nicho em uma Ãºnica configuraÃ§Ã£o;
- manter URLs estÃ¡veis por nicho.

## 11. Fora do escopo da V1

Explicitamente fora deste contrato:

- GA4;
- Meta Pixel;
- Meta Conversion API;
- armazenamento de UTMs em banco;
- Supabase;
- identificaÃ§Ã£o individual do visitante;
- cookies de marketing;
- mediÃ§Ã£o da entrada efetiva no grupo;
- mediÃ§Ã£o de vendas de afiliados;
- dashboard;
- teste A/B;
- mÃºltiplos grupos simultÃ¢neos dentro do mesmo nicho;
- balanceamento de trÃ¡fego entre grupos;
- regra automÃ¡tica por capacidade do grupo;
- painel administrativo;
- CMS;
- WordPress.

## 12. CritÃ©rios de aceite da V1

A V1 Ã© considerada funcional quando:

1. `/feminino` funciona com ou sem UTM;
2. o CTA principal leva a `/go/whatsapp/feminino`;
3. UTMs recebidas permanecem disponÃ­veis na chamada da rota de redirect;
4. `/go/whatsapp/feminino` responde com HTTP `302` para o convite configurado;
5. trocar a configuraÃ§Ã£o do grupo altera o destino sem alterar a landing;
6. o fluxo funciona em mobile e desktop;
7. a pÃ¡gina funciona sem banco de dados, GA4 ou Meta Pixel;
8. configuraÃ§Ã£o invÃ¡lida produz falha controlada;
9. o convite nÃ£o estÃ¡ duplicado dentro da landing;
10. a landing exibe os seis macrogrupos definidos;
11. a landing comunica produtos originais e lojas confiÃ¡veis;
12. a landing nÃ£o promete quantidade fixa de mensagens;
13. a landing nÃ£o expÃµe horÃ¡rios individuais de triggers;
14. a landing comunica o silÃªncio aproximado entre 21h10 e 8h;
15. a landing comunica que somente administradores enviam mensagens;
16. o Hero utiliza a copy-base definida neste contrato;
17. a Vitrine Shopee e exemplos de ofertas, quando usados, permanecem secundÃ¡rios em relaÃ§Ã£o ao CTA do WhatsApp.

## 13. Contratos de URL

### Landing

```text
GET /{nicho}
```

Inicialmente:

```text
GET /feminino
```

### Redirect WhatsApp

```text
GET /go/whatsapp/{nicho}
```

Inicialmente:

```text
GET /go/whatsapp/feminino
```

Resposta configurada:

```text
HTTP 302
Location: <URL_DO_GRUPO_ATIVO_DO_NICHO>
```

Resposta sem configuraÃ§Ã£o vÃ¡lida:

```text
falha controlada
sem redirect para destino arbitrario
```

## 14. DecisÃµes registradas

| Status | DecisÃ£o |
|---|---|
| Decidido | A primeira implementaÃ§Ã£o Ã© a landing feminina. |
| Decidido | V1 Ã© landing + rota controlada para WhatsApp + suporte/preservaÃ§Ã£o de UTM. |
| Decidido | A arquitetura nasce multi-nicho. |
| Decidido | V1 possui um grupo WhatsApp ativo por nicho. |
| Decidido | `/go/whatsapp/{nicho}` utiliza HTTP 302. |
| Decidido | O destino Ã© centralizado em configuraÃ§Ã£o por nicho. |
| Decidido | Trocar o grupo nÃ£o exige editar a landing. |
| Decidido | UTM faz parte da V1. |
| Decidido | GA4 e Meta Pixel nÃ£o fazem parte da V1. |
| Decidido | PÃºblico de referÃªncia da landing feminina: mulheres de aproximadamente 30 a 55 anos. |
| Decidido | Macrogrupos pÃºblicos: Beleza, Moda, CalÃ§ados, Bolsas e acessÃ³rios, Cabelos e Skincare. |
| Decidido | Hero, gancho e CTA principal estÃ£o definidos como copy-base. |
| Decidido | A landing destaca produtos originais e lojas confiÃ¡veis. |
| Decidido | A Vitrine Shopee pode funcionar como prova secundÃ¡ria de curadoria. |
| Decidido | Exemplos reais de ofertas podem ser usados como prova. |
| Decidido | O CTA dominante continua sendo entrar no WhatsApp. |
| Decidido | A urgÃªncia deve ser baseada apenas em condiÃ§Ãµes reais. |
| Decidido | A landing nÃ£o promete volume diÃ¡rio fixo nem publica horÃ¡rios individuais de triggers. |
| Decidido | O perÃ­odo de silÃªncio comunicado Ã© aproximadamente de 21h10 a 8h. |
| Decidido | Somente administradores enviam mensagens. |

## 15. PrÃ³ximos detalhamentos

1. fechar a estrutura visual e ordem final das seÃ§Ãµes;
2. escolher os exemplos reais de ofertas/Vitrine Shopee usados na primeira publicaÃ§Ã£o;
3. definir identidade visual e assets;
4. definir o mecanismo tÃ©cnico do redirect na Hostinger;
5. fechar a convenÃ§Ã£o operacional de UTMs;
6. definir processo de deploy;
7. definir observabilidade e testes da V1.
