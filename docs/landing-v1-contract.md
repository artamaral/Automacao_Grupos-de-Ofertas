# Contrato V1 — Landing + Link WhatsApp + UTM

**Status:** Decidido para V1  
**Versão do contrato:** 1.6  
**Data:** 2026-08-26  
**Branch:** `docs/feminino-calcados-discovery`

## 1. Objetivo

Definir o contrato funcional mínimo da primeira versão da landing page usada para captar usuários para grupos de ofertas no WhatsApp.

A V1 deve resolver quatro responsabilidades:

1. apresentar uma landing page pública e mobile-first por nicho;
2. direcionar o usuário para o grupo de WhatsApp correspondente ao nicho por uma URL controlada pelo projeto;
3. receber e preservar parâmetros UTM para identificar a origem do tráfego;
4. nascer com convenção de URL compatível com múltiplos nichos, sem exigir múltiplos grupos simultâneos dentro do mesmo nicho na V1.

GA4, Meta Pixel, banco de dados, Supabase, roteamento automático entre vários grupos do mesmo nicho e medição de entrada efetiva no grupo ficam fora deste contrato V1.

A primeira implementação da V1 será exclusivamente para o nicho feminino.

## 2. Escopo funcional da V1

Fluxo oficial:

```text
Anúncio / Instagram / outro canal
              |
              | URL da landing do nicho + UTM
              v
Landing pública do nicho
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

Cada nicho deve possuir uma URL pública própria no domínio do projeto.

Convenção:

```text
/{nicho}
```

Exemplos:

```text
https://seudominio.com.br/feminino
https://seudominio.com.br/mae-bebe
```

A URL poderá receber parâmetros UTM.

Exemplo:

```text
https://seudominio.com.br/feminino?utm_source=instagram&utm_medium=paid&utm_campaign=grupo_ofertas_femininas&utm_content=reels_01
```

### 3.2 Saída principal

A conversão obrigatória da V1 é o clique no CTA principal para entrada no grupo do nicho correspondente.

O CTA não deve apontar diretamente para o convite permanente do WhatsApp. Deve apontar para:

```text
/go/whatsapp/{nicho}
```

Exemplo:

```text
https://seudominio.com.br/go/whatsapp/feminino
```

### 3.3 Público de referência da landing feminina

A primeira landing deve falar prioritariamente com mulheres de aproximadamente 30 a 55 anos.

Essa faixa é referência para linguagem, visual e escolha de exemplos. Não é uma restrição de acesso ao grupo.

### 3.4 Macrogrupos exibidos na landing feminina

A landing feminina não deve expor toda a taxonomia técnica interna de subnichos.

Para comunicação com a usuária final, a cobertura do nicho feminino deve ser apresentada exatamente com estes seis macrogrupos:

- 💄 Beleza
- 👗 Moda
- 👠 Calçados
- 👜 Bolsas e acessórios
- 💇‍♀️ Cabelos
- 🧴 Skincare

Esses macrogrupos são uma camada de apresentação da landing. Eles não substituem nem redefinem a taxonomia técnica usada por catálogo, discovery, scoring ou seleção de ofertas.

## 4. Copy consolidada da landing feminina

Os textos desta seção foram definidos durante o desenho da V1 e estão próximos da copy de produção. Devem ser usados como base na implementação. Ajustes posteriores de pontuação, hierarquia visual ou pequenas variações de redação podem ser feitos sem alterar a promessa ou as regras de negócio.

### 4.1 Hero

**Título**

> Ofertas e cupons para mulheres, não perca tempo procurando

**Subtítulo**

> Receba no WhatsApp ótimos produtos de beleza, moda, calçados, bolsas, cabelos e skincare.

**Gancho**

> Os preços mudam, os cupons acabam e as melhores ofertas podem durar pouco.

**CTA principal**

> Quero receber as ofertas no WhatsApp

### 4.2 Mensagem principal de confiança

Esta mensagem deve receber destaque visual e não ser tratada apenas como observação de rodapé:

> 💎 Ofertas e cupons apenas de produtos ORIGINAIS e de lojas CONFIÁVEIS

### 4.3 Como funciona — copy-base

A seção deve explicar de maneira simples o que a participante recebe e como o grupo funciona.

**🔎 Nós fazemos a curadoria**

> Selecionamos produtos femininos de beleza, moda, calçados, bolsas, cabelos e skincare, priorizando boas ofertas e cupons.

**💎 Produtos e lojas confiáveis**

> Ofertas e cupons apenas de produtos originais e de lojas confiáveis.

**📲 Você recebe direto no WhatsApp**

> As ofertas são enviadas ao longo do dia, para você não precisar ficar procurando promoções.

**🏷️ Oferta + preço + cupom + link**

> Cada mensagem traz as informações necessárias para avaliar rapidamente a oportunidade e acessar a oferta.

**🌙 Seu descanso é respeitado**

> As mensagens param à noite e só voltam pela manhã. O grupo fica em silêncio aproximadamente entre 21h10 e 8h.

**🔕 Só administradores enviam mensagens**

> Somente administradores enviam mensagens no grupo, evitando conversas, correntes ou mensagens de participantes.

### 4.4 Tensão de comunicação

A tensão da landing deve partir de uma situação real:

```text
A usuária não quer perder tempo procurando promoções
        +
preços mudam, cupons acabam e estoque pode terminar
        ↓
o grupo faz a curadoria e avisa pelo WhatsApp
```

Formulações já discutidas e aprovadas como referência:

> Quando aparece uma boa oferta, você precisa saber a tempo.

> Boas ofertas não ficam disponíveis para sempre. Entre no grupo e receba nossos achados e cupons enquanto ainda estão valendo.

> Nós procuramos. Você recebe quando aparece algo que vale a pena.

Essas formulações são referências de copy e podem ser usadas em seções secundárias, desde que não criem promessa de disponibilidade garantida.

### 4.5 Urgência permitida

A copy pode criar senso de urgência exclusivamente com base em condições reais:

- preço promocional pode mudar;
- cupom pode expirar ou atingir limite de uso;
- estoque pode acabar;
- oferta pode deixar de estar disponível.

Não usar:

- escassez artificial;
- contagem regressiva fictícia;
- prazo inventado;
- afirmação de últimas unidades sem evidência;
- qualquer urgência que não corresponda a uma condição real verificável.

### 4.6 CTA final

A página deve repetir o objetivo principal próximo ao final.

Copy-base:

> Quer receber essas ofertas todos os dias?

CTA-base:

> Quero receber as ofertas no WhatsApp

O CTA final pode usar variação equivalente, como:

> Quero entrar no grupo

O destino permanece `/go/whatsapp/feminino` com preservação das UTMs recebidas.

## 5. Prova de curadoria e Vitrine Shopee

### 5.1 Função da Vitrine Shopee

A Vitrine do Afiliado Shopee, ou coleção curada equivalente, pode ser utilizada como prova concreta da curadoria realizada pelo projeto.

Ela deve permitir que a visitante veja o tipo de produto selecionado antes de entrar no grupo.

A Vitrine Shopee é um elemento secundário. Não deve competir visualmente com o CTA principal de entrada no WhatsApp.

### 5.2 Copy-base para a prova de curadoria

Formulações já discutidas:

> Quer ver o tipo de oferta que selecionamos?

CTA secundário:

> Ver nossa seleção na Shopee

Também podem existir chamadas específicas, por exemplo:

> Calçados que valem a pena

CTA:

> Ver seleção de calçados

E:

> Cupons e achados

CTA:

> Ver seleção na Shopee

### 5.3 Exemplos reais de ofertas

A landing pode apresentar aproximadamente 3 a 4 exemplos visuais de ofertas ou categorias curadas.

Modelo conceitual:

```text
Ofertas que você pode receber no grupo

[Produto de beleza]
De R$ XX,XX por R$ XX,XX
[Ver oferta]

[Calçado feminino]
Oferta em destaque
[Ver ofertas de calçados]

[Cupom Shopee]
Cupom disponível
[Pegar cupom]
```

Os dados exibidos devem corresponder à oferta real no momento em que forem publicados. A landing não deve manter preço, desconto, estoque ou validade fictícios.

CTAs secundários permitidos:

- `Ver nossa seleção na Shopee`;
- `Ver oferta`;
- `Pegar cupom`;
- `Ver ofertas de calçados`;
- `Ver seleção de calçados`;
- `Ver seleção na Shopee`.

O CTA dominante da página continua sendo a entrada no grupo de WhatsApp.

## 6. Regras públicas de operação

### 6.1 Não prometer quantidade fixa de mensagens

A landing não deve informar quantidade diária fixa de mensagens.

A cadência operacional pode evoluir sem exigir mudança da promessa pública da landing.

### 6.2 Não publicar horários individuais de triggers

A landing não deve informar horários detalhados de cada trigger ou disparo.

O comportamento público deve ser descrito simplesmente como recebimento de ofertas ao longo do dia.

### 6.3 Período de silêncio

A operação possui último trigger às `21:00`, podendo haver envio residual por até aproximadamente 10 minutos.

Por isso, a landing não deve afirmar silêncio a partir de 21h em ponto.

Contrato público atual:

> O grupo fica em silêncio aproximadamente entre 21h10 e 8h.

Esse horário pode evoluir futuramente. Enquanto a política estiver vigente, a landing não deve publicar promessa conflitante com ela.

### 6.4 Somente administradores enviam mensagens

A landing deve comunicar que somente administradores enviam mensagens no grupo.

Esse ponto funciona como elemento de confiança e deixa claro que o grupo não funciona como chat aberto entre participantes.

## 7. Contrato do link WhatsApp

### 7.1 Regra principal

Nenhum anúncio, bio, QR code ou material externo deve depender diretamente do convite permanente de um grupo específico quando puder utilizar a landing ou a rota controlada do nicho.

```text
URL pública do nicho
        |
        v
/go/whatsapp/{nicho}
        |
        v
link real do WhatsApp daquele nicho
```

### 7.2 Destino da V1

Na V1 haverá apenas um destino ativo por nicho.

Não haverá balanceamento, escolha automática ou distribuição entre vários grupos dentro do mesmo nicho.

A arquitetura deve permitir evolução futura sem quebra de URL:

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

Deve ser possível alterar o link real do grupo sem alterar:

- a URL da landing;
- URLs utilizadas em anúncios;
- links em bio;
- QR codes;
- materiais externos que utilizem a rota controlada.

### 7.4 Redirect

Ao acessar `/go/whatsapp/{nicho}`, o usuário deve ser redirecionado para o convite configurado daquele nicho.

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

### 7.5 Configuração única por nicho

Convenção da V1:

```text
WHATSAPP_GROUP_URL_<NICHO>
```

Exemplo inicial:

```text
WHATSAPP_GROUP_URL_FEMININO
```

O convite não deve ficar duplicado em HTML, JavaScript, anúncios ou múltiplos arquivos de configuração.

### 7.6 Validação e falha controlada

Antes do redirect, a implementação deve verificar que a configuração:

- existe;
- não está vazia;
- é HTTPS;
- possui forma/domínio de convite do WhatsApp aceito pela implementação.

Se estiver ausente ou inválida:

- não redirecionar para endereço desconhecido;
- não usar grupo antigo como fallback silencioso;
- não usar grupo de outro nicho;
- não expor detalhes internos;
- retornar resposta/página de erro controlada.

### 7.7 Ambiente

A V1 deve possuir configuração de produção para cada nicho implantado.

Staging separado não é requisito obrigatório da V1.

## 8. Contrato UTM

### 8.1 Parâmetros suportados

A landing deve aceitar:

- `utm_source`;
- `utm_medium`;
- `utm_campaign`;
- `utm_content`;
- `utm_term`.

UTM é opcional e nunca pode impedir acesso à landing ou ao WhatsApp.

### 8.2 Preservação

Os parâmetros recebidos devem ser preservados até a rota de saída.

```text
/feminino?utm_source=instagram&utm_medium=paid&utm_campaign=grupo_feminino&utm_content=reels_01
        |
        v
/go/whatsapp/feminino?utm_source=instagram&utm_medium=paid&utm_campaign=grupo_feminino&utm_content=reels_01
        |
        v
HTTP 302 -> URL do grupo feminino ativo
```

A V1 não exige persistência das UTMs nem sua propagação para `chat.whatsapp.com`.

### 8.3 Convenção inicial

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

Valores desconhecidos não devem ser bloqueados e parâmetros ausentes não invalidam a URL.

## 9. Regras de negócio consolidadas

### RB-01 — Uma ação principal

A landing deve priorizar a entrada no grupo de WhatsApp.

### RB-02 — Desacoplamento do grupo

O convite real do WhatsApp não deve ser a URL pública permanente utilizada em campanhas.

### RB-03 — Um grupo ativo por nicho

A V1 trabalha com um único destino ativo por nicho.

### RB-04 — Arquitetura multi-nicho

Usar `/{nicho}` e `/go/whatsapp/{nicho}` desde a V1.

### RB-05 — Evolução sem quebra de URL

Múltiplos grupos futuros do mesmo nicho poderão ser colocados atrás da mesma rota pública.

### RB-06 — UTM opcional e preservada

A ausência de UTM não impede o fluxo; quando presente, deve chegar até `/go/whatsapp/{nicho}`.

### RB-07 — Redirect temporário

Usar HTTP `302`.

### RB-08 — Configuração única

O grupo ativo é configurado em uma única fonte por nicho.

### RB-09 — Falha controlada

Configuração ausente ou inválida não pode gerar redirect arbitrário ou fallback silencioso.

### RB-10 — Mobile-first

O fluxo deve funcionar primeiro em dispositivos móveis, sem impedir uso em desktop.

### RB-11 — Curadoria Shopee como prova secundária

A Vitrine Shopee pode comprovar o tipo de curadoria, mas não substitui o CTA principal.

### RB-12 — Urgência real

Só usar urgência baseada em preço, cupom, estoque ou disponibilidade reais.

### RB-13 — Público feminino

A comunicação da primeira landing é orientada principalmente a mulheres de aproximadamente 30 a 55 anos.

### RB-14 — Macrogrupos públicos

Exibir exatamente:

- 💄 Beleza
- 👗 Moda
- 👠 Calçados
- 👜 Bolsas e acessórios
- 💇‍♀️ Cabelos
- 🧴 Skincare

### RB-15 — Produtos originais e lojas confiáveis

Comunicar explicitamente a promessa de curadoria de produtos originais e lojas confiáveis.

### RB-16 — Sem promessa de volume diário

Não publicar quantidade fixa de mensagens por dia.

### RB-17 — Sem horários de triggers

Não publicar a grade de disparos.

### RB-18 — Silêncio noturno

Comunicar silêncio aproximadamente entre 21h10 e 8h enquanto essa for a política operacional vigente.

### RB-19 — Grupo fechado para participantes

Somente administradores enviam mensagens.

## 10. Requisitos não funcionais mínimos

A V1 deve:

- utilizar HTTPS;
- carregar rapidamente em conexão móvel;
- evitar dependências desnecessárias;
- não exigir login;
- não exigir banco de dados;
- não exigir cookies para funcionar;
- permitir versionamento integral no Git;
- permitir alteração do destino WhatsApp sem alterar a URL pública da campanha;
- centralizar o destino de cada nicho em uma única configuração;
- manter URLs estáveis por nicho.

## 11. Fora do escopo da V1

Explicitamente fora deste contrato:

- GA4;
- Meta Pixel;
- Meta Conversion API;
- armazenamento de UTMs em banco;
- Supabase;
- identificação individual do visitante;
- cookies de marketing;
- medição da entrada efetiva no grupo;
- medição de vendas de afiliados;
- dashboard;
- teste A/B;
- múltiplos grupos simultâneos dentro do mesmo nicho;
- balanceamento de tráfego entre grupos;
- regra automática por capacidade do grupo;
- painel administrativo;
- CMS;
- WordPress.

## 12. Critérios de aceite da V1

A V1 é considerada funcional quando:

1. `/feminino` funciona com ou sem UTM;
2. o CTA principal leva a `/go/whatsapp/feminino`;
3. UTMs recebidas permanecem disponíveis na chamada da rota de redirect;
4. `/go/whatsapp/feminino` responde com HTTP `302` para o convite configurado;
5. trocar a configuração do grupo altera o destino sem alterar a landing;
6. o fluxo funciona em mobile e desktop;
7. a página funciona sem banco de dados, GA4 ou Meta Pixel;
8. configuração inválida produz falha controlada;
9. o convite não está duplicado dentro da landing;
10. a landing exibe os seis macrogrupos definidos;
11. a landing comunica produtos originais e lojas confiáveis;
12. a landing não promete quantidade fixa de mensagens;
13. a landing não expõe horários individuais de triggers;
14. a landing comunica o silêncio aproximado entre 21h10 e 8h;
15. a landing comunica que somente administradores enviam mensagens;
16. o Hero utiliza a copy-base definida neste contrato;
17. a Vitrine Shopee e exemplos de ofertas, quando usados, permanecem secundários em relação ao CTA do WhatsApp.

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

Resposta sem configuração válida:

```text
falha controlada
sem redirect para destino arbitrario
```

## 14. Decisões registradas

| Status | Decisão |
|---|---|
| Decidido | A primeira implementação é a landing feminina. |
| Decidido | V1 é landing + rota controlada para WhatsApp + suporte/preservação de UTM. |
| Decidido | A arquitetura nasce multi-nicho. |
| Decidido | V1 possui um grupo WhatsApp ativo por nicho. |
| Decidido | `/go/whatsapp/{nicho}` utiliza HTTP 302. |
| Decidido | O destino é centralizado em configuração por nicho. |
| Decidido | Trocar o grupo não exige editar a landing. |
| Decidido | UTM faz parte da V1. |
| Decidido | GA4 e Meta Pixel não fazem parte da V1. |
| Decidido | Público de referência da landing feminina: mulheres de aproximadamente 30 a 55 anos. |
| Decidido | Macrogrupos públicos: Beleza, Moda, Calçados, Bolsas e acessórios, Cabelos e Skincare. |
| Decidido | Hero, gancho e CTA principal estão definidos como copy-base. |
| Decidido | A landing destaca produtos originais e lojas confiáveis. |
| Decidido | A Vitrine Shopee pode funcionar como prova secundária de curadoria. |
| Decidido | Exemplos reais de ofertas podem ser usados como prova. |
| Decidido | O CTA dominante continua sendo entrar no WhatsApp. |
| Decidido | A urgência deve ser baseada apenas em condições reais. |
| Decidido | A landing não promete volume diário fixo nem publica horários individuais de triggers. |
| Decidido | O período de silêncio comunicado é aproximadamente de 21h10 a 8h. |
| Decidido | Somente administradores enviam mensagens. |

## 15. Próximos detalhamentos

1. fechar a estrutura visual e ordem final das seções;
2. escolher os exemplos reais de ofertas/Vitrine Shopee usados na primeira publicação;
3. definir identidade visual e assets;
4. definir o mecanismo técnico do redirect na Hostinger;
5. fechar a convenção operacional de UTMs;
6. definir processo de deploy;
7. definir observabilidade e testes da V1.
