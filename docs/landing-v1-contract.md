# Contrato V1 — Landing + Link WhatsApp + UTM

**Status:** Decidido para V1  
**Versão do contrato:** 1.0  
**Data:** 2026-08-26  
**Branch:** `docs/feminino-calcados-discovery`

## 1. Objetivo

Definir o contrato funcional mínimo da primeira versão da landing page usada para captar usuários para o grupo de ofertas no WhatsApp.

A V1 deve resolver apenas três responsabilidades:

1. apresentar uma landing page pública e mobile-first;
2. direcionar o usuário para o grupo de WhatsApp por uma URL controlada pelo projeto;
3. receber e preservar parâmetros UTM para identificar a origem do tráfego.

GA4, Meta Pixel, banco de dados, Supabase, roteamento automático entre vários grupos e medição de entrada efetiva no grupo ficam fora deste contrato V1.

## 2. Escopo funcional da V1

Fluxo oficial:

```text
Anúncio / Instagram / outro canal
              |
              | URL da landing + UTM
              v
Landing page pública
              |
              | CTA "Entrar no grupo"
              v
Rota controlada /go/whatsapp
              |
              v
Link de convite do grupo WhatsApp ativo
```

## 3. Contrato da landing page

### 3.1 Entrada

A landing deve aceitar acesso por URL pública no domínio do projeto.

Exemplo conceitual:

```text
https://seudominio.com.br/ofertas
```

A URL poderá receber parâmetros UTM.

Exemplo:

```text
https://seudominio.com.br/ofertas?utm_source=instagram&utm_medium=paid&utm_campaign=grupo_ofertas_femininas&utm_content=reels_01
```

### 3.2 Saída principal

A única conversão obrigatória da V1 é o clique no CTA principal para entrada no grupo.

O CTA não deve apontar diretamente para o link permanente do grupo do WhatsApp.

O CTA deve apontar para uma rota controlada pelo projeto:

```text
/go/whatsapp
```

Exemplo conceitual:

```text
https://seudominio.com.br/go/whatsapp
```

### 3.3 Conteúdo mínimo

A V1 deve possuir, no mínimo:

- identificação clara do grupo;
- proposta de valor resumida;
- CTA principal para entrar no grupo;
- CTA adicional próximo ao fim da página;
- layout mobile-first;
- funcionamento adequado em desktop;
- carregamento por HTTPS.

Copy final, identidade visual definitiva, exemplos de ofertas e demais blocos de conteúdo serão detalhados separadamente.

## 4. Contrato do link WhatsApp

### 4.1 Regra principal

Nenhum anúncio, bio, QR code ou material externo deve depender diretamente do convite permanente de um grupo específico quando puder utilizar a landing ou a rota controlada.

A regra é:

```text
URL pública do projeto
        |
        v
/go/whatsapp
        |
        v
link real do WhatsApp
```

### 4.2 Destino da V1

Na V1 haverá apenas um destino ativo configurado por vez.

Não haverá balanceamento, escolha automática ou distribuição entre vários grupos nesta versão.

### 4.3 Troca do grupo

Deve ser possível alterar o link real do grupo de WhatsApp sem alterar:

- a URL divulgada da landing;
- URLs utilizadas em anúncios;
- links em bio;
- QR codes que apontem para a URL controlada;
- demais materiais externos que utilizem a rota do projeto.

### 4.4 Comportamento esperado

Ao acessar `/go/whatsapp`, o usuário deve ser redirecionado para o convite configurado do grupo ativo.

A implementação técnica exata do redirect será definida na implementação, preservando este comportamento funcional.

## 5. Contrato UTM

### 5.1 Objetivo

UTMs devem permitir identificar de qual origem, campanha e criativo veio o acesso à landing.

Na V1, UTM é mecanismo de identificação de origem. Não implica, por si só, uso de GA4, Meta Pixel ou armazenamento em banco.

### 5.2 Parâmetros suportados

A landing deve aceitar os parâmetros UTM padrão:

- `utm_source`;
- `utm_medium`;
- `utm_campaign`;
- `utm_content`;
- `utm_term`.

Os quatro primeiros são os principais para o uso planejado do projeto. `utm_term` deve ser aceito para compatibilidade, mesmo que não seja utilizado em todas as campanhas.

### 5.3 Sem UTM

A landing deve funcionar normalmente quando nenhum parâmetro UTM estiver presente.

UTM não é requisito para acesso à página nem para entrada no grupo.

### 5.4 Preservação

Quando a landing for acessada com parâmetros UTM, esses valores não devem ser descartados durante a navegação que leva ao CTA do WhatsApp.

A V1 deve preservar os parâmetros recebidos até a chamada da rota `/go/whatsapp`.

Exemplo:

```text
Entrada:
/ofertas?utm_source=instagram&utm_medium=paid&utm_campaign=grupo_feminino&utm_content=reels_01

CTA:
/go/whatsapp?utm_source=instagram&utm_medium=paid&utm_campaign=grupo_feminino&utm_content=reels_01
```

Essa preservação existe para permitir instrumentação posterior sem precisar alterar as URLs das campanhas já publicadas.

### 5.5 Valores desconhecidos

A aplicação não deve bloquear UTMs por possuir valores ainda não cadastrados.

Exemplo válido:

```text
utm_source=tiktok
```

Mesmo que TikTok ainda não faça parte das campanhas ativas, o valor deve ser tratado como texto válido.

### 5.6 Parâmetros ausentes

Os parâmetros UTM são independentes.

Uma URL com apenas parte dos parâmetros deve continuar funcionando.

Exemplo válido:

```text
/ofertas?utm_source=instagram&utm_campaign=grupo_feminino
```

## 6. Convenção inicial de UTMs

Para campanhas pagas da Meta, a convenção inicial recomendada é:

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

Os nomes definitivos de campanhas e criativos pertencem à estratégia de mídia e poderão evoluir sem alteração deste contrato.

## 7. Regras de negócio da V1

### RB-01 — Uma ação principal

A landing deve priorizar a entrada no grupo de WhatsApp como ação principal.

### RB-02 — Desacoplamento do grupo

O convite real do WhatsApp não deve ser a URL pública permanente usada nas campanhas quando a rota controlada puder ser utilizada.

### RB-03 — Um grupo ativo

A V1 trabalha com um único destino de WhatsApp por vez.

### RB-04 — UTM opcional

A ausência de UTM nunca pode impedir carregamento da landing ou entrada no WhatsApp.

### RB-05 — Preservação de UTM

UTMs recebidas na landing devem ser preservadas até a rota de saída para WhatsApp.

### RB-06 — Falha no destino

Se não houver link de WhatsApp configurado, a aplicação não deve redirecionar silenciosamente para destino desconhecido ou incorreto.

O comportamento visual de erro será definido na implementação, mas a falha deve ser explícita e controlada.

### RB-07 — Mobile-first

O fluxo principal deve funcionar primeiro em dispositivos móveis, sem impedir uso em desktop.

## 8. Requisitos não funcionais mínimos

A V1 deve:

- utilizar HTTPS;
- carregar rapidamente em conexão móvel;
- evitar dependências desnecessárias;
- não exigir login;
- não exigir banco de dados;
- não exigir cookies para funcionar;
- permitir versionamento integral do código no Git;
- permitir alteração do destino WhatsApp sem alterar a URL pública da campanha.

## 9. Fora do escopo da V1

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
- múltiplos grupos simultâneos;
- balanceamento de tráfego entre grupos;
- regra automática por capacidade do grupo;
- painel administrativo;
- CMS;
- WordPress.

Esses itens poderão ser adicionados em versões posteriores sem alterar o objetivo funcional da V1.

## 10. Critérios de aceite da V1

A V1 é considerada funcional quando todos os seguintes cenários forem atendidos:

1. abrir a landing sem UTM carrega a página normalmente;
2. abrir a landing com UTMs carrega a página normalmente;
3. clicar no CTA leva à rota `/go/whatsapp`;
4. os parâmetros UTM recebidos permanecem disponíveis na chamada da rota `/go/whatsapp`;
5. `/go/whatsapp` redireciona para o convite configurado do grupo ativo;
6. alterar o convite configurado muda o destino sem alterar a URL pública da landing;
7. o fluxo funciona em navegador mobile;
8. o fluxo funciona em navegador desktop;
9. a página funciona sem banco de dados, GA4 ou Meta Pixel;
10. ausência de configuração válida do grupo produz falha controlada e não redirect incorreto.

## 11. Contratos de URL

### Landing

```text
GET /ofertas
```

Aceita opcionalmente:

```text
utm_source
utm_medium
utm_campaign
utm_content
utm_term
```

### Redirect WhatsApp

```text
GET /go/whatsapp
```

Aceita opcionalmente os mesmos parâmetros UTM preservados da landing.

Resposta esperada quando configurado corretamente:

```text
redirect -> convite do grupo WhatsApp ativo
```

## 12. Decisões registradas

| Status | Decisão |
|---|---|
| Decidido | V1 é composta por landing + rota controlada para WhatsApp + suporte/preservação de UTM. |
| Decidido | UTM faz parte da V1. |
| Decidido | GA4 e Meta Pixel não fazem parte do contrato V1. |
| Decidido | V1 possui apenas um grupo WhatsApp ativo por vez. |
| Decidido | A URL pública deve permanecer estável mesmo quando o convite do grupo mudar. |
| Decidido | Banco de dados não é requisito da V1. |
| Em aberto | Definir domínio/path definitivo de produção. |
| Em aberto | Definir mecanismo técnico de configuração do link do grupo na Hostinger. |
| Em aberto | Definir copy e identidade visual finais. |

## 13. Próximo detalhamento

Depois deste contrato, os próximos documentos/revisões devem detalhar separadamente:

1. conteúdo e copy da landing;
2. identidade visual e assets;
3. mecanismo técnico do redirect na Hostinger;
4. convenção operacional para criação das UTMs;
5. processo de deploy;
6. critérios de observabilidade e testes da V1.
