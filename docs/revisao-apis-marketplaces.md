# Revisão de APIs dos marketplaces

## Objetivo

Registrar o achado sobre a necessidade de validar os contratos atuais das APIs antes de executar chamadas reais.

Até aqui, o projeto priorizou segurança, harness, dry-run, guards, preview e testes. A partir da primeira chamada real, a versão atual da API passa a ser bloqueante.

## Amazon

### Achado

A documentação pública da Product Advertising API 5.0 ainda documenta a operação `SearchItems`, mas a própria página informa que a PA-API será descontinuada em 15 de maio de 2026 e recomenda migração para a Creators API.

Referência oficial consultada:

```text
https://webservices.amazon.com/paapi5/documentation/search-items.html
```

A página também informa que o site de documentação da PA-API não é mais mantido e pode conter informação desatualizada.

Além disso, a operação real da Amazon deve considerar a restrição de
elegibilidade da Creators API. A regra operacional conhecida é que, além de uma
conta de criador aprovada, pode ser necessário ter pelo menos 10 vendas
qualificadas nos últimos 30 dias para acessar a PA API por meio da Creators API.
Essa condição deve ser confirmada no painel/conta antes de qualquer chamada real.

### Impacto no projeto

- Não devemos tratar a integração Amazon atual como contrato final.
- Antes de chamada real na Amazon, decidir se o projeto continua temporariamente com PA-API 5.0 ou se migra o desenho para Creators API.
- O builder atual da Amazon deve continuar protegido por guard e testes, sem chamada real automática.
- Enquanto não houver elegibilidade, Amazon deve operar como provider restrito:
  mock/fake, entrada manual/curada ou avaliação experimental de scraping sob
  risco controlado.
- O projeto não deve depender da Amazon API para o MVP operacional.

### Estratégia temporária sem API oficial

Enquanto a conta não tiver acesso oficial suficiente:

1. manter testes e contrato interno do `AmazonProvider` com transport fake;
2. permitir entrada manual/curada de ofertas e cupons Amazon quando houver link
   válido e permitido;
3. usar o mesmo ranking, copy, compliance e revisão dos demais providers;
4. avaliar scraping apenas se não houver alternativa, com baixa frequência,
   isolamento técnico e aprovação explícita;
5. migrar para Creators API quando a elegibilidade existir.

Scraping para Amazon, se avaliado, deve respeitar:

- nada de captcha bypass;
- nada de contornar bloqueios, autenticação, detecção ou rate limits;
- nada de cookies, sessões, tokens ou credenciais versionados;
- nada de scraping agressivo;
- logs seguros e fonte/data registradas;
- fallback manual ou outro provider.

### Decisão pendente

- [ ] Confirmar se a conta do projeto ainda terá acesso útil à PA-API 5.0.
- [ ] Avaliar se a Creators API atende melhor ao fluxo de ofertas afiliadas.
- [ ] Confirmar no painel a regra de elegibilidade de 10 vendas qualificadas nos
      últimos 30 dias.
- [ ] Definir formato de entrada manual/curada para ofertas e cupons Amazon.
- [ ] Decidir se scraping será permitido como experimento de alto risco.
- [ ] Só depois decidir a próxima integração real da Amazon.

## Shopee

### Achado

O endpoint público REST usado no código durante o desenvolvimento não representa
o contrato correto da Open API de afiliados informada para o projeto. O caminho
atual deve ser tratado como legado/provisório:

```text
/api/v2/product/search_item
```

A documentação informada para a Open API de afiliados usa GraphQL. A query para
listar ofertas é:

```text
shopeeOfferV2
```

Tipo de retorno:

```text
ShopeeOfferConnectionV2!
```

Endpoint informado:

```text
POST https://open-api.affiliate.shopee.com.br/graphql
```

Headers conhecidos:

```text
Authorization: SHA256 Credential=<credential>, Signature=<signature>, Timestamp=<timestamp>
Content-Type: application/json
```

O header acima não deve ser logado com valores reais. `Credential`,
`Signature` e `Timestamp` devem ser tratados como dados sensíveis ou
operacionais.

Assinatura:

```text
Signature = SHA256(Credential + Timestamp + Payload + Secret)
```

Onde:

- `Credential` é o AppId da Open API;
- `Timestamp` é o Unix timestamp atual, com diferença máxima de 10 minutos em
  relação ao servidor;
- `Payload` é o body JSON exato enviado na requisição;
- `Secret` é a senha/chave da Open API e nunca deve ser exposta.

Formato do body:

```json
{
  "query": "...",
  "operationName": "...",
  "variables": {
    "myVariable": "someValue"
  }
}
```

`operationName` e `variables` são opcionais no protocolo GraphQL, mas
`operationName` é obrigatório quando houver mais de uma operação no mesmo
documento. No projeto, os builders devem sempre preencher `operationName` para
facilitar rastreio, logs seguros e testes.

Envelope de resposta:

```json
{
  "data": {},
  "errors": []
}
```

Quando não houver erro, `errors` pode não ser retornado.

### Contrato GraphQL conhecido

Famílias de operações informadas:

- ofertas por busca/lista;
- ofertas por marca;
- produtos;
- feed de produtos;
- feed de marcas;
- geração de short URL.

Essas famílias devem ser modeladas como operações do provider Shopee GraphQL,
não como CLIs separados.

Query parameters:

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `keyword` | `String` | Busca por nome da oferta. |
| `sortType` | `Int` | `1` para mais recentes, `2` para maior comissão. |
| `page` | `Int` | Número da página. |
| `limit` | `Int` | Quantidade de itens por página. |

Valores conhecidos de `sortType`:

| Valor | Nome | Descrição |
| --- | --- | --- |
| `1` | `LATEST_DESC` | Ordena por atualização mais recente. |
| `2` | `HIGHEST_COMMISSION_DESC` | Ordena por maior comissão. |

Response:

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `nodes` | `[ShopeeOfferV2]!` | Lista de ofertas. |
| `pageInfo` | `PageInfo!` | Dados de paginação. |

Estrutura `ShopeeOfferV2`:

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `commissionRate` | `String` | Taxa de comissão. Ex: `0.0123` para 1,23%. |
| `imageUrl` | `String` | URL da imagem. |
| `offerLink` | `String` | Link afiliado da oferta. |
| `originalLink` | `String` | Link original. |
| `offerName` | `String` | Nome da oferta. |
| `offerType` | `Int` | Tipo da oferta. |
| `categoryId` | `Int64` | Retorna quando `offerType = 2`. |
| `collectionId` | `Int64` | Retorna quando `offerType = 1`. |
| `periodStartTime` | `Int` | Início da oferta. |
| `periodEndTime` | `Int` | Fim da oferta. |

Valores conhecidos de `offerType`:

| Valor | Nome | Descrição |
| --- | --- | --- |
| `1` | `CAMPAIGN_TYPE_COLLECTION` | Oferta de coleção. |
| `2` | `CAMPAIGN_TYPE_CATEGORY` | Oferta de categoria. |

Estrutura `PageInfo`:

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `page` | `Int` | Página atual. |
| `limit` | `Int` | Quantidade por página. |
| `hasNextPage` | `Bool` | Indica se há próxima página. |

### Estrutura de erro GraphQL

Campos conhecidos em `errors`:

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `message` | `String` | Resumo do erro. |
| `path` | `String` | Localização da requisição com erro. |
| `extensions` | `object` | Detalhes do erro. |
| `extensions.code` | `Int` | Código do erro. |
| `extensions.message` | `String` | Descrição do erro. |

Códigos conhecidos:

| Código | Significado | Descrição |
| --- | --- | --- |
| `10000` | System error | Erro de sistema. |
| `10010` | Request parsing error | Sintaxe incorreta, tipo incorreto ou API inexistente. |
| `10020` | Identity authentication error | Assinatura incorreta ou expirada. |
| `10030` | Trigger traffic limiting | Número de requests excedeu o limite. |
| `11000` | Business processing error | Erro de processamento de negócio. |

### Mutação de short URL

A Open API também possui uma mutação para gerar short links. Esse recurso é
importante para o projeto porque permite transformar uma URL original ou de
oferta em um link curto rastreável antes do envio para WhatsApp/Telegram.

Mutação informada:

```graphql
mutation {
  generateShortLink(
    input: {
      originUrl: "https://shopee.com.br/Apple-Iphone-11-128GB-Local-Set-i.52377417.6309028319"
      subIds: ["s1", "s2", "s3", "s4", "s5"]
    }
  ) {
    shortLink
  }
}
```

Parâmetros conhecidos:

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `originUrl` | `String` | URL original que será convertida em short link. |
| `subIds` | `[String]` | Identificadores de rastreio/campanha. |

Resposta conhecida:

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `shortLink` | `String` | Link curto gerado pela Shopee. |

Uso esperado no projeto:

1. coletar oferta/produto/cupom;
2. definir contexto de rastreio (`subIds`) por grupo, campanha, provider e
   execução;
3. gerar short link pela mutação `generateShortLink`;
4. salvar short link e vínculo com a oferta;
5. usar o short link nas mensagens revisadas e aprovadas.

### Impacto no projeto

- A implementação principal da Shopee foi migrada do REST/GET legado para um
  provider GraphQL da Open API de afiliados.
- O provider GraphQL monta `POST` para
  `https://open-api.affiliate.shopee.com.br/graphql`.
- A autenticação gera o header `Authorization` no formato SHA256 informado
  pela documentação, sem expor credenciais ou assinatura em logs.
- O mapper da Shopee normaliza `data.shopeeOfferV2.nodes` para `Offer`.
- Como `shopeeOfferV2` nao retorna preco de produto, o projeto trata preco `0`
  como preco desconhecido e orienta a mensagem para consultar o valor no link.
- O mock usa payload fake no formato `ShopeeOfferConnectionV2`, mantendo paridade
  com o caminho real de desenvolvimento.
- A paginação usa `pageInfo.hasNextPage`, `pageInfo.page` e
  `pageInfo.limit`.
- A busca suporta `keyword`, `sortType`, `page` e `limit`.
- O ranking interno do projeto deve continuar independente do `sortType`; a
  ordenação da Shopee é apenas ordenação da fonte.
- Cupons/ofertas de campanha devem considerar `periodStartTime` e
  `periodEndTime` para validade.
- A geração de mensagem deve preferir `shortLink` quando ele existir e estiver
  vinculado à oferta aprovada.
- `subIds` devem ser padronizados para rastrear origem, grupo, campanha e
  execução sem expor dados pessoais.

### Decisão pendente

- [ ] Confirmar endpoint GraphQL oficial da conta Shopee.
- [ ] Confirmar método HTTP, headers e autenticação da Open API GraphQL.
- [ ] Confirmar o algoritmo exato da assinatura SHA256.
- [ ] Confirmar envelope real de resposta: `data`, `errors`, códigos e mensagens.
- [ ] Confirmar se `offerLink` já vem com tracking/afiliado aplicado.
- [ ] Confirmar se há query específica para cupons diários.
- [ ] Confirmar schema das queries de marca, produto, product feed e brand feed.
- [ ] Confirmar limites e formato aceito de `subIds`.
- [ ] Definir padrão interno de `subIds`.
- [x] Criar payload fake com `shopeeOfferV2` para o provider mock.
- [ ] Criar fixture fake/anonimizada com `generateShortLink`.
- [x] Implementar builder, gateway e mapper GraphQL para `shopeeOfferV2`.
- [ ] Validar builder, gateway e mapper GraphQL contra uma resposta real
      anonimizada da conta aprovada.

## Regra antes de chamada real

A ordem mínima passa a ser:

1. validar contratos oficiais;
2. ajustar configuração fora do Git;
3. rodar diagnóstico;
4. gerar preview seguro;
5. revisar manualmente o preview;
6. executar chamada real controlada com `--limit 1`;
7. anonimizar resposta antes de criar fixtures ou testes com payload real.

## O que continua proibido

- Chamada real sem validação de contrato.
- Publicação real.
- Salvar payload bruto no Git.
- Comitar credenciais, assinaturas, tokens, headers completos ou prints sensíveis.
- Aumentar volume antes de validar rate limit e resposta normalizada.
