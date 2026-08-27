# Contrato V1 — Landing + Link WhatsApp + UTM

**Status:** Decidido para V1  
**Versão do contrato:** 1.2  
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

## 2. Escopo funcional da V1

Fluxo oficial:

```text
Anúncio / Instagram / outro canal
              |
              | URL da landing do nicho + UTM
              v
Landing pública do nicho
              |
              | CTA "Entrar no grupo"
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

Exemplo futuro de outro nicho:

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

A única conversão obrigatória da V1 é o clique no CTA principal para entrada no grupo do nicho correspondente.

O CTA não deve apontar diretamente para o link permanente do grupo do WhatsApp.

O CTA deve apontar para uma rota controlada pelo projeto com o nicho explícito:

```text
/go/whatsapp/{nicho}
```

Exemplo:

```text
https://seudominio.com.br/go/whatsapp/feminino
```

### 3.3 Conteúdo mínimo

Cada landing da V1 deve possuir, no mínimo:

- identificação clara do nicho/grupo;
- proposta de valor resumida;
- CTA principal para entrar no grupo;
- CTA adicional próximo ao fim da página;
- layout mobile-first;
- funcionamento adequado em desktop;
- carregamento por HTTPS.

Copy final, identidade visual definitiva, exemplos de ofertas e demais blocos de conteúdo serão detalhados separadamente por nicho.

## 4. Contrato do link WhatsApp

### 4.1 Regra principal

Nenhum anúncio, bio, QR code ou material externo deve depender diretamente do convite permanente de um grupo específico quando puder utilizar a landing ou a rota controlada do nicho.

A regra é:

```text
URL pública do nicho
        |
        v
/go/whatsapp/{nicho}
        |
        v
link real do WhatsApp daquele nicho
```

### 4.2 Destino da V1

Na V1 haverá apenas um destino ativo por nicho.

Não haverá balanceamento, escolha automática ou distribuição entre vários grupos dentro do mesmo nicho nesta versão.

A arquitetura, porém, deve preservar a URL pública por nicho para que no futuro a mesma rota possa escolher entre múltiplos grupos sem quebrar anúncios ou landings existentes.

Exemplo futuro:

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

### 4.3 Troca do grupo

Deve ser possível alterar o link real do grupo de WhatsApp de um nicho sem alterar:

- a URL divulgada da landing daquele nicho;
- URLs utilizadas em anúncios;
- links em bio;
- QR codes que apontem para a URL controlada;
- demais materiais externos que utilizem a rota do projeto.

### 4.4 Comportamento esperado

Ao acessar `/go/whatsapp/{nicho}`, o usuário deve ser redirecionado para o convite configurado do grupo ativo daquele nicho.

O redirect da V1 deve utilizar resposta HTTP temporária `302`.

A escolha de `302` é deliberada: o destino pode ser alterado no futuro e não deve ser tratado pelos clientes como permanente.

Fluxo normativo:

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
URL do grupo ativo daquele nicho
```

### 4.5 Fonte única de configuração

Cada nicho deve possuir uma única configuração operacional para o grupo ativo.

Na V1, a convenção de variável pode ser:

```text
WHATSAPP_GROUP_URL_<NICHO>
```

Exemplo inicial:

```text
WHATSAPP_GROUP_URL_FEMININO
```

Exemplo futuro:

```text
WHATSAPP_GROUP_URL_MAE_BEBE
```

A implementação deve evitar duplicar o convite do grupo em HTML, JavaScript, anúncios ou múltiplos arquivos de configuração.

Objetivo operacional:

```text
alterar WHATSAPP_GROUP_URL_FEMININO
        |
        v
novo destino passa a valer em /go/whatsapp/feminino
        |
        v
landing, anúncios e URLs públicas permanecem inalterados
```

### 4.6 Validação mínima do destino

Antes do redirect, a implementação deve verificar que a configuração do nicho:

- existe;
- não está vazia;
- representa uma URL HTTPS;
- aponta para um domínio/forma de convite do WhatsApp aceita pela implementação.

A aplicação não deve redirecionar para um valor arbitrário ou claramente inválido.

### 4.7 Falha controlada

Se a configuração do nicho estiver ausente ou inválida:

- não realizar redirect para endereço desconhecido;
- não usar automaticamente um grupo antigo como fallback silencioso;
- não expor detalhes internos de configuração ao visitante;
- retornar uma resposta/página de erro controlada.

A copy visual da página de erro será definida separadamente.

### 4.8 UTMs no redirect

Os parâmetros UTM recebidos em `/go/whatsapp/{nicho}` pertencem ao contexto de aquisição do projeto e não precisam ser acrescentados ao link final `chat.whatsapp.com` na V1.

Contrato:

```text
/feminino?utm_source=instagram&...
        |
        v
/go/whatsapp/feminino?utm_source=instagram&...
        |
        v
HTTP 302 -> URL do grupo feminino ativo
```

As UTMs devem permanecer disponíveis até a chamada da rota de redirect, permitindo futura instrumentação. A V1 não exige persistência nem propagação das UTMs para o domínio do WhatsApp.

### 4.9 Operação de troca do grupo

Trocar o grupo ativo de um nicho deve exigir somente a alteração da configuração daquele nicho e a aplicação/deploy conforme o mecanismo suportado pelo ambiente Hostinger escolhido.

A operação não deve exigir edição da landing page.

Após a troca, deve ser feito um teste simples acessando `/go/whatsapp/{nicho}` e confirmando que o novo convite é o destino retornado.

### 4.10 Ambiente

A V1 deve possuir configuração de produção para cada nicho implantado.

Ambiente separado de staging não é requisito obrigatório da V1. Caso exista ambiente de teste, ele não deve utilizar por engano convites de produção durante validações destrutivas ou experimentais.

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

A V1 deve preservar os parâmetros recebidos até a chamada da rota `/go/whatsapp/{nicho}`.

Exemplo:

```text
Entrada:
/feminino?utm_source=instagram&utm_medium=paid&utm_campaign=grupo_feminino&utm_content=reels_01

CTA:
/go/whatsapp/feminino?utm_source=instagram&utm_medium=paid&utm_campaign=grupo_feminino&utm_content=reels_01
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
/feminino?utm_source=instagram&utm_campaign=grupo_feminino
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

Cada landing deve priorizar a entrada no grupo de WhatsApp do respectivo nicho como ação principal.

### RB-02 — Desacoplamento do grupo

O convite real do WhatsApp não deve ser a URL pública permanente usada nas campanhas quando a rota controlada puder ser utilizada.

### RB-03 — Um grupo ativo por nicho

A V1 trabalha com um único destino de WhatsApp ativo por nicho.

### RB-04 — Arquitetura multi-nicho

As URLs devem usar a convenção `/{nicho}` para landing e `/go/whatsapp/{nicho}` para redirect, mesmo que inicialmente apenas um nicho esteja implantado.

### RB-05 — UTM opcional

A ausência de UTM nunca pode impedir carregamento da landing ou entrada no WhatsApp.

### RB-06 — Preservação de UTM

UTMs recebidas na landing devem ser preservadas até a rota de saída para WhatsApp.

### RB-07 — Falha no destino

Se não houver link de WhatsApp configurado para o nicho solicitado, a aplicação não deve redirecionar silenciosamente para destino desconhecido ou incorreto.

A falha deve ser explícita e controlada.

### RB-08 — Mobile-first

O fluxo principal deve funcionar primeiro em dispositivos móveis, sem impedir uso em desktop.

### RB-09 — Redirect temporário

`/go/whatsapp/{nicho}` deve usar HTTP `302` na V1.

### RB-10 — Configuração única por nicho

O destino de cada nicho deve ser obtido de uma única configuração operacional.

### RB-11 — Troca sem alteração da landing

A troca do grupo ativo de um nicho não deve exigir alteração do HTML, CSS ou JavaScript da landing.

### RB-12 — Sem fallback silencioso

Configuração inválida não deve redirecionar automaticamente para convite antigo ou para grupo de outro nicho.

### RB-13 — Evolução sem quebra de URL

No futuro, múltiplos grupos dentro do mesmo nicho poderão ser adicionados atrás de `/go/whatsapp/{nicho}` sem exigir mudança na URL pública da landing ou das campanhas.

## 8. Requisitos não funcionais mínimos

A V1 deve:

- utilizar HTTPS;
- carregar rapidamente em conexão móvel;
- evitar dependências desnecessárias;
- não exigir login;
- não exigir banco de dados;
- não exigir cookies para funcionar;
- permitir versionamento integral do código no Git;
- permitir alteração do destino WhatsApp sem alterar a URL pública da campanha;
- centralizar o destino de cada nicho em uma única configuração operacional;
- manter URLs estáveis por nicho para permitir evolução futura sem quebra de campanhas.

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
- múltiplos grupos simultâneos dentro do mesmo nicho;
- balanceamento de tráfego entre grupos;
- regra automática por capacidade do grupo;
- painel administrativo;
- CMS;
- WordPress.

Ter múltiplos nichos com uma landing e um grupo ativo por nicho é compatível com o contrato V1. O que permanece fora do escopo é a distribuição automática entre vários grupos dentro de um mesmo nicho.

## 10. Critérios de aceite da V1

A V1 é considerada funcional quando todos os seguintes cenários forem atendidos para cada nicho implantado:

1. abrir `/{nicho}` sem UTM carrega a landing correta;
2. abrir `/{nicho}` com UTMs carrega a landing correta;
3. clicar no CTA leva à rota `/go/whatsapp/{nicho}`;
4. os parâmetros UTM recebidos permanecem disponíveis na chamada da rota `/go/whatsapp/{nicho}`;
5. `/go/whatsapp/{nicho}` responde com HTTP `302` para o convite configurado daquele nicho;
6. alterar a configuração do grupo daquele nicho muda o destino sem alterar a URL pública da landing;
7. o fluxo funciona em navegador mobile;
8. o fluxo funciona em navegador desktop;
9. a página funciona sem banco de dados, GA4 ou Meta Pixel;
10. ausência de configuração válida do nicho produz falha controlada e não redirect incorreto;
11. o convite do grupo não está duplicado como dependência dentro da landing;
12. UTMs não precisam ser propagadas para `chat.whatsapp.com` para que a V1 seja considerada correta;
13. adicionar um novo nicho não exige alterar a convenção de URL dos nichos existentes.

## 11. Contratos de URL

### Landing por nicho

```text
GET /{nicho}
```

Exemplos:

```text
GET /feminino
GET /mae-bebe
```

Aceita opcionalmente:

```text
utm_source
utm_medium
utm_campaign
utm_content
utm_term
```

### Redirect WhatsApp por nicho

```text
GET /go/whatsapp/{nicho}
```

Exemplos:

```text
GET /go/whatsapp/feminino
GET /go/whatsapp/mae-bebe
```

Aceita opcionalmente os mesmos parâmetros UTM preservados da landing.

Resposta esperada quando configurado corretamente:

```text
HTTP 302
Location: <URL_DO_GRUPO_ATIVO_DO_NICHO>
```

Resposta esperada quando não configurado corretamente:

```text
falha controlada
sem redirect para destino arbitrario
sem fallback para outro nicho
```

## 12. Decisões registradas

| Status | Decisão |
|---|---|
| Decidido | V1 é composta por landing por nicho + rota controlada para WhatsApp por nicho + suporte/preservação de UTM. |
| Decidido | UTM faz parte da V1. |
| Decidido | GA4 e Meta Pixel não fazem parte do contrato V1. |
| Decidido | V1 possui apenas um grupo WhatsApp ativo por nicho. |
| Decidido | A arquitetura nasce multi-nicho, usando `/{nicho}` e `/go/whatsapp/{nicho}`. |
| Decidido | Exemplos planejados incluem `/feminino` e `/mae-bebe`. |
| Decidido | A URL pública de um nicho deve permanecer estável mesmo quando o convite do grupo daquele nicho mudar. |
| Decidido | Banco de dados não é requisito da V1. |
| Decidido | `/go/whatsapp/{nicho}` utiliza HTTP 302. |
| Decidido | O link real do grupo é centralizado em uma única configuração por nicho. |
| Decidido | Trocar o grupo de um nicho não exige editar a landing. |
| Decidido | Configuração ausente ou inválida gera falha controlada, sem fallback silencioso. |
| Decidido | UTMs são preservadas até a rota de redirect, mas não precisam seguir para o domínio do WhatsApp na V1. |
| Decidido | No futuro, múltiplos grupos do mesmo nicho poderão ficar atrás da mesma rota sem mudar URLs públicas. |
| Em aberto | Definir domínio definitivo de produção. |
| Em aberto | Definir mecanismo técnico de armazenamento das configurações na Hostinger. |
| Em aberto | Definir copy e identidade visual finais por nicho. |

## 13. Próximo detalhamento

Depois deste contrato, os próximos documentos/revisões devem detalhar separadamente:

1. conteúdo e copy da primeira landing (`/feminino`);
2. identidade visual e assets;
3. mecanismo técnico do redirect e configuração por nicho na Hostinger;
4. convenção operacional para criação das UTMs;
5. processo de deploy;
6. critérios de observabilidade e testes da V1;
7. contrato futuro de roteamento quando um nicho possuir múltiplos grupos.
