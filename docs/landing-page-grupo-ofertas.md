# Landing Page do Grupo de Ofertas

**Status:** Em definiÃ§Ã£o
**VersÃ£o do documento:** 0.1
**Data inicial:** 2026-08-26
**Escopo:** aquisiÃ§Ã£o de membros para grupos de ofertas no WhatsApp

## 1. Objetivo

Definir, de forma incremental e versionada, a estratÃ©gia, regras de negÃ³cio, arquitetura tÃ©cnica, mÃ©tricas, requisitos de escala e operaÃ§Ã£o da landing page usada para divulgar e captar membros para os grupos de ofertas.

Este documento Ã© deliberadamente evolutivo. DecisÃµes ainda nÃ£o tomadas devem permanecer explicitamente marcadas como abertas, em vez de serem assumidas durante a implementaÃ§Ã£o.

## 2. Contexto do projeto

A landing page faz parte do funil de aquisiÃ§Ã£o do ecossistema de grupos de ofertas da Shopee e Amazon.

Fluxo inicial proposto:

```text
Instagram / Facebook Ads
          |
          v
Landing page no domÃ­nio prÃ³prio
          |
          v
CTA "Entrar no grupo"
          |
          v
Rota controlada /go/whatsapp
          |
          v
Grupo de WhatsApp ativo
```

A landing page nÃ£o Ã©, nesta fase, uma loja virtual nem um catÃ¡logo completo de produtos. Sua funÃ§Ã£o principal Ã© converter visitantes em membros do grupo.

## 3. DecisÃ£o tÃ©cnica inicial

### 3.1 Hospedagem

Utilizar a infraestrutura jÃ¡ contratada na Hostinger e o domÃ­nio jÃ¡ disponÃ­vel.

### 3.2 ImplementaÃ§Ã£o inicial

A primeira versÃ£o deve ser uma aplicaÃ§Ã£o estÃ¡tica e simples:

- HTML;
- CSS;
- JavaScript apenas quando necessÃ¡rio;
- sem banco de dados obrigatÃ³rio na V1;
- sem backend obrigatÃ³rio na V1;
- sem WordPress como dependÃªncia inicial.

### 3.3 MotivaÃ§Ã£o

A landing possui inicialmente um Ãºnico objetivo de conversÃ£o e nÃ£o requer CMS, blog, autenticaÃ§Ã£o ou administraÃ§Ã£o complexa de conteÃºdo.

A arquitetura deve priorizar:

1. baixo custo;
2. velocidade de carregamento;
3. simplicidade operacional;
4. facilidade de versionamento no Git;
5. controle total sobre tracking e redirects;
6. possibilidade de evoluÃ§Ã£o sem reescrever todo o funil.

## 4. PrincÃ­pios do produto

A landing deve ser:

- **mobile-first**, pois a maior parte do trÃ¡fego deverÃ¡ chegar de Instagram, Facebook e WhatsApp;
- **orientada a uma aÃ§Ã£o principal**, evitando mÃºltiplas rotas de fuga;
- **rÃ¡pida**, com poucas dependÃªncias e mÃ­dia otimizada;
- **mensurÃ¡vel**, permitindo identificar origem do trÃ¡fego e cliques no CTA;
- **escalÃ¡vel**, permitindo futuramente trabalhar com mÃºltiplos grupos, nichos e campanhas;
- **desacoplada do link direto do WhatsApp**, para permitir troca do grupo de destino sem alterar anÃºncios e materiais jÃ¡ publicados.

## 5. Estrutura funcional inicial da pÃ¡gina

### 5.1 Hero

Deve comunicar imediatamente:

- o que Ã© o grupo;
- para quem ele Ã©;
- que tipo de benefÃ­cio o usuÃ¡rio recebe;
- que a participaÃ§Ã£o Ã© gratuita, quando aplicÃ¡vel;
- CTA principal para entrada no WhatsApp.

### 5.2 Prova do conteÃºdo

A pÃ¡gina deve mostrar exemplos representativos das ofertas enviadas no grupo.

Objetivo:

- reduzir incerteza;
- demonstrar o tipo de produto divulgado;
- tornar tangÃ­vel o valor do grupo antes do clique.

### 5.3 Categorias/subnichos

A pÃ¡gina poderÃ¡ apresentar as principais categorias atendidas pelo grupo.

A taxonomia exibida deve seguir a taxonomia oficial vigente no projeto e nÃ£o deve criar categorias independentes da operaÃ§Ã£o real.

### 5.4 Como funciona

ExplicaÃ§Ã£o curta do fluxo:

1. ofertas sÃ£o encontradas e selecionadas;
2. produtos relevantes sÃ£o publicados;
3. o usuÃ¡rio recebe as oportunidades no WhatsApp.

### 5.5 CTA recorrente

AlÃ©m do CTA principal no hero, deve existir CTA prÃ³ximo ao fim da pÃ¡gina.

A versÃ£o mobile poderÃ¡ utilizar CTA fixo, desde que nÃ£o comprometa usabilidade ou leitura.

## 6. Regra de negÃ³cio: link controlado para WhatsApp

Os anÃºncios e canais externos nÃ£o devem depender diretamente do convite permanente de um grupo especÃ­fico.

DireÃ§Ã£o proposta:

```text
seudominio.com.br/go/whatsapp
                |
                v
        grupo atualmente ativo
```

Essa camada de indireÃ§Ã£o deve permitir futuramente:

- trocar o grupo de destino sem editar anÃºncios ativos;
- substituir links expirados;
- direcionar trÃ¡fego para um novo grupo quando o atual atingir capacidade;
- distribuir trÃ¡fego entre vÃ¡rios grupos;
- registrar qual grupo recebeu cada origem de trÃ¡fego.

A implementaÃ§Ã£o concreta da rota serÃ¡ definida em versÃ£o posterior deste documento.

## 7. Tracking inicial

### 7.1 IdentificaÃ§Ã£o de origem

A landing deve preservar parÃ¢metros UTM recebidos da campanha.

Exemplo conceitual:

```text
utm_source=instagram
utm_medium=paid
utm_campaign=grupo_ofertas_femininas
utm_content=reels_01
```

### 7.2 Eventos mÃ­nimos desejados

Na primeira versÃ£o instrumentada:

- `page_view`;
- `click_whatsapp`.

### 7.3 Eventos/dados futuros

A arquitetura deve permitir evoluir para registrar:

- campanha;
- criativo;
- origem;
- grupo de destino;
- timestamp;
- identificador de sessÃ£o anÃ´nimo, quando necessÃ¡rio e compatÃ­vel com a polÃ­tica de privacidade adotada;
- conversÃµes posteriores que puderem ser tecnicamente observadas.

## 8. Funil de negÃ³cio

O funil que deverÃ¡ orientar a evoluÃ§Ã£o da landing Ã©:

```text
Investimento em anÃºncios
        |
        v
Visitas na landing
        |
        v
Cliques para WhatsApp
        |
        v
Entradas no grupo
        |
        v
Engajamento no grupo
        |
        v
Cliques em ofertas
        |
        v
ConversÃµes de afiliado
        |
        v
Receita
```

Nem todas as etapas sÃ£o atualmente observÃ¡veis de ponta a ponta. A instrumentaÃ§Ã£o serÃ¡ refinada conforme as integraÃ§Ãµes permitirem.

## 9. MÃ©tricas

### MÃ©tricas iniciais

- sessÃµes/visitas da landing;
- taxa de clique no CTA do WhatsApp;
- cliques absolutos no CTA;
- origem/campanha/criativo via UTM;
- custo por visita, quando proveniente de mÃ­dia paga;
- custo por clique para WhatsApp.

### MÃ©trica principal desejada de aquisiÃ§Ã£o

- **Custo por Entrada no Grupo (CPL)**.

A forma confiÃ¡vel de medir a entrada efetiva no grupo, distinguindo-a de um simples clique para o WhatsApp, ainda precisa ser detalhada e validada tecnicamente.

### MÃ©tricas futuras de negÃ³cio

- receita por grupo;
- receita por membro;
- receita por campanha;
- receita por criativo;
- payback do custo de aquisiÃ§Ã£o;
- ROI/ROAS do funil de aquisiÃ§Ã£o;
- retenÃ§Ã£o e crescimento lÃ­quido dos grupos.

## 10. Escala prevista

A arquitetura nÃ£o deve presumir a existÃªncia de apenas um grupo.

Deve ser preparada para uma evoluÃ§Ã£o como:

```text
Campanha / nicho
       |
       v
Landing
       |
       v
Router de grupos
       |
       +--> Grupo 01
       +--> Grupo 02
       +--> Grupo 03
       +--> ...
```

PossÃ­veis critÃ©rios futuros de roteamento:

- grupo com capacidade disponÃ­vel;
- nicho/subnicho;
- campanha;
- origem do trÃ¡fego;
- distribuiÃ§Ã£o balanceada;
- prioridade operacional;
- regras especÃ­ficas de teste A/B.

Nenhum desses critÃ©rios estÃ¡ aprovado ainda como regra definitiva.

## 11. EvoluÃ§Ã£o proposta

### V1 â€” Landing mÃ­nima

- pÃ¡gina estÃ¡tica;
- identidade visual inicial;
- CTA para WhatsApp;
- domÃ­nio e SSL;
- versÃ£o mobile-first;
- redirect controlado para o grupo.

### V2 â€” InstrumentaÃ§Ã£o

- UTMs;
- GA4;
- Meta Pixel;
- eventos de visualizaÃ§Ã£o e clique;
- polÃ­tica de privacidade/cookies conforme necessidade da instrumentaÃ§Ã£o adotada.

### V3 â€” OtimizaÃ§Ã£o de conversÃ£o

- testes de headline;
- testes de criativos/provas de oferta;
- testes de CTA;
- anÃ¡lise de taxa de conversÃ£o por campanha.

### V4 â€” MÃºltiplos grupos

- roteador de destino;
- troca de grupos sem alterar URLs pÃºblicas;
- capacidade/configuraÃ§Ã£o por grupo;
- registro do grupo selecionado.

### V5 â€” PersistÃªncia e automaÃ§Ã£o

PossÃ­vel integraÃ§Ã£o com a infraestrutura de dados jÃ¡ utilizada pelo projeto, incluindo Supabase, se a necessidade for validada.

PossÃ­veis funÃ§Ãµes:

- configuraÃ§Ã£o dos grupos ativos;
- capacidade e status;
- histÃ³rico de redirects;
- origem de trÃ¡fego;
- controle operacional.

### V6 â€” InteligÃªncia de aquisiÃ§Ã£o

- consolidaÃ§Ã£o de custos de mÃ­dia;
- conversÃ£o e receita por origem;
- dashboard de CPL, ROI e receita;
- apoio Ã  decisÃ£o de alocaÃ§Ã£o de verba.

## 12. Fora do escopo da versÃ£o 0.1

Ainda nÃ£o estÃ£o definidos:

- design visual definitivo;
- copy final;
- domÃ­nio/subdomÃ­nio/path definitivo;
- mecanismo tÃ©cnico exato do redirect;
- mecanismo confiÃ¡vel para contabilizar entrada efetiva no grupo;
- regras de capacidade de cada grupo;
- estratÃ©gia de cookies/consentimento;
- polÃ­ticas legais finais;
- integraÃ§Ã£o especÃ­fica com Supabase;
- integraÃ§Ã£o com Meta Conversion API;
- estratÃ©gia de testes A/B;
- distribuiÃ§Ã£o automÃ¡tica entre grupos;
- painel administrativo.

Esses pontos serÃ£o detalhados passo a passo.

## 13. Processo de evoluÃ§Ã£o deste documento

Cada discussÃ£o futura deve transformar decisÃµes em uma das categorias abaixo:

- **Decidido** â€” regra aprovada e que deve orientar implementaÃ§Ã£o;
- **HipÃ³tese** â€” proposta que precisa de teste ou validaÃ§Ã£o;
- **Em aberto** â€” questÃ£o ainda sem decisÃ£o;
- **Descartado** â€” alternativa analisada e rejeitada, mantendo o motivo registrado.

MudanÃ§as relevantes devem atualizar:

1. nÃºmero da versÃ£o do documento;
2. seÃ§Ã£o afetada;
3. histÃ³rico de decisÃµes;
4. commit correspondente.

## 14. HistÃ³rico de decisÃµes

| VersÃ£o | Data | Status | DecisÃ£o |
|---|---|---|---|
| 0.1 | 2026-08-26 | Decidido | Usar inicialmente a hospedagem e o domÃ­nio jÃ¡ disponÃ­veis na Hostinger. |
| 0.1 | 2026-08-26 | Decidido | Priorizar landing estÃ¡tica customizada em vez de WordPress na primeira versÃ£o. |
| 0.1 | 2026-08-26 | Decidido | O objetivo primÃ¡rio da landing Ã© aquisiÃ§Ã£o de membros para o grupo de WhatsApp. |
| 0.1 | 2026-08-26 | Decidido | A URL pÃºblica deve ser desacoplada do convite direto do grupo por uma camada de redirect controlÃ¡vel. |
| 0.1 | 2026-08-26 | HipÃ³tese | GA4 e Meta Pixel serÃ£o os mecanismos iniciais de instrumentaÃ§Ã£o. |
| 0.1 | 2026-08-26 | Em aberto | Definir mecanismo para mensurar entrada real no grupo, e nÃ£o apenas clique no CTA. |
| 0.1 | 2026-08-26 | Em aberto | Definir regras de roteamento e capacidade quando houver vÃ¡rios grupos. |

## 15. PrÃ³ximas decisÃµes a detalhar

Ordem sugerida para as prÃ³ximas discussÃµes:

1. objetivo de negÃ³cio e pÃºblico da primeira landing;
2. arquitetura de grupos e estratÃ©gia de escala;
3. definiÃ§Ã£o exata da conversÃ£o que serÃ¡ otimizada;
4. regras de negÃ³cio do redirect/roteador;
5. estrutura e copy da landing;
6. identidade visual e ativos;
7. tracking, consentimento e mÃ©tricas;
8. integraÃ§Ã£o com dados/Supabase;
9. deploy, ambientes e operaÃ§Ã£o;
10. testes e critÃ©rios de aceite.
