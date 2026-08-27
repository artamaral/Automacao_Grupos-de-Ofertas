# Contrato V1 — Landing + Link WhatsApp + UTM

**Status:** Decidido para V1  
**Versão do contrato:** 1.3  
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

### RB-14 — Curadoria Shopee como prova secundária

A landing feminina poderá utilizar uma Vitrine do Afiliado Shopee ou coleção curada equivalente como prova de curadoria real.

Esse recurso deve funcionar como evidência do tipo de produto selecionado e como mecanismo opcional para a visitante explorar exemplos antes de entrar no grupo.

A Vitrine Shopee não substitui o objetivo principal da landing e não deve competir visualmente com o CTA de entrada no WhatsApp.

### RB-15 — CTAs secundários de curadoria

A landing poderá exibir CTAs secundários associados à curadoria, por exemplo:

- `Ver nossa seleção na Shopee`;
- `Ver oferta`;
- `Pegar cupom`;
- `Ver ofertas de calçados`.

Esses CTAs são auxiliares. O CTA dominante permanece a entrada no grupo de WhatsApp.

### RB-16 — Urgência baseada em condição real

A copy poderá trabalhar senso de urgência baseado exclusivamente em condições reais do mercado e das ofertas, tais como:

- preço promocional pode mudar;
- cupom pode expirar ou atingir limite de uso;
- estoque pode acabar;
- oferta pode deixar de estar disponível.

É proibido criar escassez artificial, contagem regressiva fictícia, prazo inventado ou qualquer afirmação de urgência que não corresponda a uma condição real verificável.

### RB-17 — Tensão principal da mensagem

A tensão de comunicação da landing feminina deve ser construída em torno de uma necessidade real da usuária:

```text
nao tenho tempo para procurar boas ofertas
        +
quando descubro, o preco ou cupom pode ja ter mudado
        |
        v
receber uma curadoria no WhatsApp resolve o problema de descobrir tarde
```

A mensagem deve vender conveniência, curadoria e timing, e não medo artificial de perda.

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

A V1 é considerada funcional quando todos os seguintes cenários forem atendidos:

1. abrir a landing sem UTM carrega a página normalmente;
2. abrir a landing com UTMs carrega a página normalmente;
3. clicar no CTA principal leva à rota `/go/whatsapp/{nicho}`;
4. os parâmetros UTM recebidos permanecem disponíveis na chamada da rota `/go/whatsapp/{nicho}`;
5. `/go/whatsapp/{nicho}` responde com HTTP `302` para o convite configurado do nicho;
6. alterar a configuração do grupo muda o destino sem alterar a URL pública da landing;
7. o fluxo funciona em navegador mobile;
8. o fluxo funciona em navegador desktop;
9. a página funciona sem banco de dados, GA4 ou Meta Pixel;
10. ausência de configuração válida do grupo produz falha controlada e não redirect incorreto;
11. o convite do grupo não está duplicado como dependência dentro da landing;
12. UTMs não precisam ser propagadas para `chat.whatsapp.com` para que a V1 seja considerada correta;
13. a landing feminina pode exibir uma prova de curadoria via Vitrine Shopee sem remover a prioridade visual do CTA de WhatsApp;
14. qualquer urgência usada na copy corresponde a condição real e não a escassez artificial.

## 11. Contratos de URL

### Landing

```text
GET /{nicho}
```

Exemplo inicial:

```text
GET /feminino
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
GET /go/whatsapp/{nicho}
```

Exemplo inicial:

```text
GET /go/whatsapp/feminino
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
```

## 12. Diretrizes de conteúdo da landing feminina

A primeira landing implementada será a do nicho feminino.

### Público de referência

Mulheres de aproximadamente 30 a 55 anos.

Essa faixa é uma referência inicial de linguagem e posicionamento, não uma restrição técnica de acesso.

### Promessa principal

A landing deve comunicar que a participante receberá no grupo uma curadoria de bons produtos em oferta e cupons voltados ao universo feminino.

Direção conceitual:

```text
bons produtos + ofertas + cupons + curadoria + timing
```

### Subnichos

A landing deve destacar os subnichos oficiais existentes na taxonomia feminina do projeto. Não deve criar categorias promocionais independentes da taxonomia operacional.

### Exemplos de curadoria

A landing poderá mostrar exemplos reais ou representativos do tipo de produto selecionado, podendo direcionar para:

- oferta específica;
- cupom válido;
- coleção temática;
- Vitrine Shopee curada.

Quando houver link de afiliado ou coleção de afiliado, o uso deve seguir as regras aplicáveis do programa de afiliados e as diretrizes de transparência adotadas pelo projeto.

### Hierarquia de CTA

CTA principal:

```text
Entrar no grupo de ofertas
```

ou equivalente com foco explícito em receber ofertas no WhatsApp.

CTAs secundários podem incluir:

```text
Ver nossa seleção na Shopee
Ver oferta
Pegar cupom
Ver ofertas de calçados
```

O CTA de WhatsApp deve permanecer dominante em posição, contraste e recorrência.

### Gancho de timing

A landing deve comunicar que uma boa oferta é útil quando chega a tempo.

A mensagem pode explorar conceitos como:

- `receba quando aparecer algo que vale a pena`;
- `ofertas e cupons podem mudar`;
- `não dependa de lembrar de procurar`.

A redação final será definida em etapa específica de copy.

## 13. Decisões registradas

| Status | Decisão |
|---|---|
| Decidido | V1 é composta por landing + rota controlada para WhatsApp + suporte/preservação de UTM. |
| Decidido | UTM faz parte da V1. |
| Decidido | GA4 e Meta Pixel não fazem parte do contrato V1. |
| Decidido | A arquitetura de URL nasce preparada para múltiplos nichos. |
| Decidido | A V1 possui apenas um grupo WhatsApp ativo por nicho. |
| Decidido | A URL pública deve permanecer estável mesmo quando o convite do grupo mudar. |
| Decidido | Banco de dados não é requisito da V1. |
| Decidido | `/go/whatsapp/{nicho}` utiliza HTTP 302. |
| Decidido | O link real do grupo é centralizado em configuração única por nicho. |
| Decidido | Trocar o grupo não exige editar a landing. |
| Decidido | A primeira landing implementada será `/feminino`. |
| Decidido | A landing feminina fala prioritariamente com mulheres de aproximadamente 30 a 55 anos. |
| Decidido | A promessa central é receber bons produtos em oferta e cupons, com curadoria voltada ao universo feminino. |
| Decidido | A Vitrine Shopee pode ser usada como prova secundária de curadoria. |
| Decidido | CTAs de oferta, cupom e coleção são secundários ao CTA de entrada no grupo. |
| Decidido | O gancho de urgência deve se basear apenas em preço, cupom, estoque ou disponibilidade reais. |
| Decidido | Escassez artificial e urgência fictícia não devem ser usadas. |
| Em aberto | Definir domínio definitivo de produção. |
| Em aberto | Definir mecanismo técnico de configuração do link do grupo na Hostinger. |
| Em aberto | Definir copy final e identidade visual. |
| Em aberto | Definir a URL exata da Vitrine Shopee/coleções quando estiverem prontas. |

## 14. Próximo detalhamento

Depois deste contrato, os próximos documentos/revisões devem detalhar separadamente:

1. copy final e estrutura de conteúdo da landing feminina;
2. identidade visual e assets;
3. mecanismo técnico do redirect na Hostinger;
4. URL e operação da Vitrine Shopee/coleções;
5. convenção operacional para criação das UTMs;
6. processo de deploy;
7. critérios de observabilidade e testes da V1.
