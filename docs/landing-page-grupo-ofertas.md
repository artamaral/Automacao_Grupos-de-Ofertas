# Landing Page do Grupo de Ofertas

**Status:** Em definição  
**Versão do documento:** 0.1  
**Data inicial:** 2026-08-26  
**Escopo:** aquisição de membros para grupos de ofertas no WhatsApp

## 1. Objetivo

Definir, de forma incremental e versionada, a estratégia, regras de negócio, arquitetura técnica, métricas, requisitos de escala e operação da landing page usada para divulgar e captar membros para os grupos de ofertas.

Este documento é deliberadamente evolutivo. Decisões ainda não tomadas devem permanecer explicitamente marcadas como abertas, em vez de serem assumidas durante a implementação.

## 2. Contexto do projeto

A landing page faz parte do funil de aquisição do ecossistema de grupos de ofertas da Shopee e Amazon.

Fluxo inicial proposto:

```text
Instagram / Facebook Ads
          |
          v
Landing page no domínio próprio
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

A landing page não é, nesta fase, uma loja virtual nem um catálogo completo de produtos. Sua função principal é converter visitantes em membros do grupo.

## 3. Decisão técnica inicial

### 3.1 Hospedagem

Utilizar a infraestrutura já contratada na Hostinger e o domínio já disponível.

### 3.2 Implementação inicial

A primeira versão deve ser uma aplicação estática e simples:

- HTML;
- CSS;
- JavaScript apenas quando necessário;
- sem banco de dados obrigatório na V1;
- sem backend obrigatório na V1;
- sem WordPress como dependência inicial.

### 3.3 Motivação

A landing possui inicialmente um único objetivo de conversão e não requer CMS, blog, autenticação ou administração complexa de conteúdo.

A arquitetura deve priorizar:

1. baixo custo;
2. velocidade de carregamento;
3. simplicidade operacional;
4. facilidade de versionamento no Git;
5. controle total sobre tracking e redirects;
6. possibilidade de evolução sem reescrever todo o funil.

## 4. Princípios do produto

A landing deve ser:

- **mobile-first**, pois a maior parte do tráfego deverá chegar de Instagram, Facebook e WhatsApp;
- **orientada a uma ação principal**, evitando múltiplas rotas de fuga;
- **rápida**, com poucas dependências e mídia otimizada;
- **mensurável**, permitindo identificar origem do tráfego e cliques no CTA;
- **escalável**, permitindo futuramente trabalhar com múltiplos grupos, nichos e campanhas;
- **desacoplada do link direto do WhatsApp**, para permitir troca do grupo de destino sem alterar anúncios e materiais já publicados.

## 5. Estrutura funcional inicial da página

### 5.1 Hero

Deve comunicar imediatamente:

- o que é o grupo;
- para quem ele é;
- que tipo de benefício o usuário recebe;
- que a participação é gratuita, quando aplicável;
- CTA principal para entrada no WhatsApp.

### 5.2 Prova do conteúdo

A página deve mostrar exemplos representativos das ofertas enviadas no grupo.

Objetivo:

- reduzir incerteza;
- demonstrar o tipo de produto divulgado;
- tornar tangível o valor do grupo antes do clique.

### 5.3 Categorias/subnichos

A página poderá apresentar as principais categorias atendidas pelo grupo.

A taxonomia exibida deve seguir a taxonomia oficial vigente no projeto e não deve criar categorias independentes da operação real.

### 5.4 Como funciona

Explicação curta do fluxo:

1. ofertas são encontradas e selecionadas;
2. produtos relevantes são publicados;
3. o usuário recebe as oportunidades no WhatsApp.

### 5.5 CTA recorrente

Além do CTA principal no hero, deve existir CTA próximo ao fim da página.

A versão mobile poderá utilizar CTA fixo, desde que não comprometa usabilidade ou leitura.

## 6. Regra de negócio: link controlado para WhatsApp

Os anúncios e canais externos não devem depender diretamente do convite permanente de um grupo específico.

Direção proposta:

```text
seudominio.com.br/go/whatsapp
                |
                v
        grupo atualmente ativo
```

Essa camada de indireção deve permitir futuramente:

- trocar o grupo de destino sem editar anúncios ativos;
- substituir links expirados;
- direcionar tráfego para um novo grupo quando o atual atingir capacidade;
- distribuir tráfego entre vários grupos;
- registrar qual grupo recebeu cada origem de tráfego.

A implementação concreta da rota será definida em versão posterior deste documento.

## 7. Tracking inicial

### 7.1 Identificação de origem

A landing deve preservar parâmetros UTM recebidos da campanha.

Exemplo conceitual:

```text
utm_source=instagram
utm_medium=paid
utm_campaign=grupo_ofertas_femininas
utm_content=reels_01
```

### 7.2 Eventos mínimos desejados

Na primeira versão instrumentada:

- `page_view`;
- `click_whatsapp`.

### 7.3 Eventos/dados futuros

A arquitetura deve permitir evoluir para registrar:

- campanha;
- criativo;
- origem;
- grupo de destino;
- timestamp;
- identificador de sessão anônimo, quando necessário e compatível com a política de privacidade adotada;
- conversões posteriores que puderem ser tecnicamente observadas.

## 8. Funil de negócio

O funil que deverá orientar a evolução da landing é:

```text
Investimento em anúncios
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
Conversões de afiliado
        |
        v
Receita
```

Nem todas as etapas são atualmente observáveis de ponta a ponta. A instrumentação será refinada conforme as integrações permitirem.

## 9. Métricas

### Métricas iniciais

- sessões/visitas da landing;
- taxa de clique no CTA do WhatsApp;
- cliques absolutos no CTA;
- origem/campanha/criativo via UTM;
- custo por visita, quando proveniente de mídia paga;
- custo por clique para WhatsApp.

### Métrica principal desejada de aquisição

- **Custo por Entrada no Grupo (CPL)**.

A forma confiável de medir a entrada efetiva no grupo, distinguindo-a de um simples clique para o WhatsApp, ainda precisa ser detalhada e validada tecnicamente.

### Métricas futuras de negócio

- receita por grupo;
- receita por membro;
- receita por campanha;
- receita por criativo;
- payback do custo de aquisição;
- ROI/ROAS do funil de aquisição;
- retenção e crescimento líquido dos grupos.

## 10. Escala prevista

A arquitetura não deve presumir a existência de apenas um grupo.

Deve ser preparada para uma evolução como:

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

Possíveis critérios futuros de roteamento:

- grupo com capacidade disponível;
- nicho/subnicho;
- campanha;
- origem do tráfego;
- distribuição balanceada;
- prioridade operacional;
- regras específicas de teste A/B.

Nenhum desses critérios está aprovado ainda como regra definitiva.

## 11. Evolução proposta

### V1 — Landing mínima

- página estática;
- identidade visual inicial;
- CTA para WhatsApp;
- domínio e SSL;
- versão mobile-first;
- redirect controlado para o grupo.

### V2 — Instrumentação

- UTMs;
- GA4;
- Meta Pixel;
- eventos de visualização e clique;
- política de privacidade/cookies conforme necessidade da instrumentação adotada.

### V3 — Otimização de conversão

- testes de headline;
- testes de criativos/provas de oferta;
- testes de CTA;
- análise de taxa de conversão por campanha.

### V4 — Múltiplos grupos

- roteador de destino;
- troca de grupos sem alterar URLs públicas;
- capacidade/configuração por grupo;
- registro do grupo selecionado.

### V5 — Persistência e automação

Possível integração com a infraestrutura de dados já utilizada pelo projeto, incluindo Supabase, se a necessidade for validada.

Possíveis funções:

- configuração dos grupos ativos;
- capacidade e status;
- histórico de redirects;
- origem de tráfego;
- controle operacional.

### V6 — Inteligência de aquisição

- consolidação de custos de mídia;
- conversão e receita por origem;
- dashboard de CPL, ROI e receita;
- apoio à decisão de alocação de verba.

## 12. Fora do escopo da versão 0.1

Ainda não estão definidos:

- design visual definitivo;
- copy final;
- domínio/subdomínio/path definitivo;
- mecanismo técnico exato do redirect;
- mecanismo confiável para contabilizar entrada efetiva no grupo;
- regras de capacidade de cada grupo;
- estratégia de cookies/consentimento;
- políticas legais finais;
- integração específica com Supabase;
- integração com Meta Conversion API;
- estratégia de testes A/B;
- distribuição automática entre grupos;
- painel administrativo.

Esses pontos serão detalhados passo a passo.

## 13. Processo de evolução deste documento

Cada discussão futura deve transformar decisões em uma das categorias abaixo:

- **Decidido** — regra aprovada e que deve orientar implementação;
- **Hipótese** — proposta que precisa de teste ou validação;
- **Em aberto** — questão ainda sem decisão;
- **Descartado** — alternativa analisada e rejeitada, mantendo o motivo registrado.

Mudanças relevantes devem atualizar:

1. número da versão do documento;
2. seção afetada;
3. histórico de decisões;
4. commit correspondente.

## 14. Histórico de decisões

| Versão | Data | Status | Decisão |
|---|---|---|---|
| 0.1 | 2026-08-26 | Decidido | Usar inicialmente a hospedagem e o domínio já disponíveis na Hostinger. |
| 0.1 | 2026-08-26 | Decidido | Priorizar landing estática customizada em vez de WordPress na primeira versão. |
| 0.1 | 2026-08-26 | Decidido | O objetivo primário da landing é aquisição de membros para o grupo de WhatsApp. |
| 0.1 | 2026-08-26 | Decidido | A URL pública deve ser desacoplada do convite direto do grupo por uma camada de redirect controlável. |
| 0.1 | 2026-08-26 | Hipótese | GA4 e Meta Pixel serão os mecanismos iniciais de instrumentação. |
| 0.1 | 2026-08-26 | Em aberto | Definir mecanismo para mensurar entrada real no grupo, e não apenas clique no CTA. |
| 0.1 | 2026-08-26 | Em aberto | Definir regras de roteamento e capacidade quando houver vários grupos. |

## 15. Próximas decisões a detalhar

Ordem sugerida para as próximas discussões:

1. objetivo de negócio e público da primeira landing;
2. arquitetura de grupos e estratégia de escala;
3. definição exata da conversão que será otimizada;
4. regras de negócio do redirect/roteador;
5. estrutura e copy da landing;
6. identidade visual e ativos;
7. tracking, consentimento e métricas;
8. integração com dados/Supabase;
9. deploy, ambientes e operação;
10. testes e critérios de aceite.
