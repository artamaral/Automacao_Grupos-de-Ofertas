# Fluxo fake e injetável dos providers

## Objetivo

Este documento descreve como os providers de marketplace funcionam na fase atual da implantação.

A regra principal continua sendo: nenhuma chamada externa real deve acontecer por padrão. O projeto só executa fluxo de marketplace realista quando um gateway com transport fake é injetado em teste.

## Modos de execução

### Mock provider

Uso recomendado para testes de ponta a ponta do pipeline completo.

Fluxo:

```text
Collector -> MockOfferProvider -> Scorer -> Copywriter -> Compliance -> DryRunPublisher
```

Características:

- não usa credenciais;
- não faz HTTP;
- gera ofertas previsíveis;
- é o caminho mais seguro para testar CLI, copy, score e compliance.

### Provider configurado sem gateway/transport

Uso atual quando `--marketplace shopee` ou `--marketplace amazon` é executado sem integração real.

Comportamento esperado:

- valida configuração local;
- se faltarem variáveis, retorna erro amigável no harness;
- se variáveis existirem, mas não houver gateway com transport, levanta `NotImplementedError`;
- não faz chamada externa.

Este comportamento evita que uma execução local dispare requests reais por acidente.

### Provider com gateway e transport fake injetado

Uso recomendado para testes unitários de integração interna.

Fluxo Shopee:

```text
ShopeeProvider.fetch()
-> ShopeeGateway.execute_search()
-> ShopeeSignedRequestBuilder
-> StaticHttpTransport
-> ProviderHttpClient
-> ShopeeOfferMapper
-> list[Offer]
```

Fluxo Amazon:

```text
AmazonProvider.fetch()
-> AmazonGateway.execute_search()
-> AmazonSearchRequestBuilder
-> StaticHttpTransport
-> ProviderHttpClient
-> AmazonOfferMapper
-> list[Offer]
```

Características:

- usa payload controlado dentro do teste;
- registra o request enviado;
- valida status HTTP;
- valida formato mínimo do payload;
- normaliza o resultado para `Offer`;
- não usa internet.

## Validação de payload e campos obrigatórios

A normalização de payload externo passa pelos mappers antes de gerar `Offer`.

Campos mínimos esperados:

- `title`;
- `url`;
- `price`.

Se algum desses campos estiver ausente, vazio ou inválido, o mapper deve rejeitar o payload com `OfferMappingError` antes de qualquer etapa de score, copy ou publicação.

Essa validação já é coberta por testes fake para Shopee e Amazon e deve ser mantida quando payloads reais anonimizados forem adicionados.

## Paginação fake

Os gateways possuem paginação opcional para testes e fluxos futuros:

- `ShopeeGateway.execute_paginated_search()`;
- `AmazonGateway.execute_paginated_search()`.

Esse fluxo não é usado pelo harness nem pelos providers por padrão. Ele existe para validar o desenho de paginação com payloads controlados antes de qualquer chamada real.

Regras atuais:

- `limit`, `page_size` e `max_pages` precisam ser positivos;
- cada página usa o mesmo transport fake injetado;
- Shopee envia `page` nos parâmetros do request;
- Amazon envia `Page` no body do request;
- a coleta para quando `has_next_page` não é `True`;
- a coleta para quando uma página retorna lista vazia;
- a coleta para quando chega em `limit`;
- a coleta para quando chega em `max_pages`.

Os testes cobrem coleta em múltiplas páginas, parada por `max_pages` e parada por página vazia para Shopee e Amazon.

Exemplo conceitual:

```python
offers = gateway.execute_paginated_search(
    keyword="maquiagem",
    niche="maquiagem",
    limit=10,
    page_size=5,
)
```

## Retry e rate limit

A estrutura de retry já existe, mas é opcional e desligada por padrão.

Componentes:

- `RetryPolicy`: define tentativas, códigos que permitem retry e backoff;
- `Sleeper`: interface injetável para espera entre tentativas;
- `NoOpSleeper`: espera fake usada quando não se quer dormir de verdade;
- `SystemSleeper`: espera real preparada para uso futuro controlado.

O helper `execute_provider_request` aceita `retry_policy` e `sleeper`. Quando `retry_policy=None`, não há retry e o comportamento continua igual ao fluxo anterior.

Exemplo conceitual em teste:

```python
retry_policy = RetryPolicy(max_attempts=2, base_delay_seconds=0.25)
gateway = ShopeeGateway(
    request_builder=builder,
    transport=fake_transport,
    retry_policy=retry_policy,
    sleeper=fake_sleeper,
)
```

Esse fluxo permite simular status como `429` sem fazer chamada real e sem esperar tempo real no teste.

## Transport fake

O transport fake atual é `StaticHttpTransport`.

Ele recebe uma `HttpResponse` controlada e devolve essa resposta sempre que `send()` é chamado. Também registra os requests enviados no atributo `requests`.

Exemplo conceitual:

```python
response = HttpResponse(status_code=200, data={...})
transport = StaticHttpTransport(response=response)
```

Com isso, os testes conseguem validar:

- método HTTP;
- URL;
- parâmetros;
- body;
- payload de resposta;
- tratamento de erro.

## Transport HTTP real

Existe um transport HTTP real isolado chamado `UrllibHttpTransport`.

Ele foi criado apenas como peça técnica preparada para o futuro. No estado atual:

- não é conectado automaticamente a nenhum provider;
- não é usado pelo harness;
- não é usado por padrão em Shopee ou Amazon;
- deve continuar desativado até existir checklist de produção.

A configuração `enable_real_http` existe no `Settings` e nasce como `False` por padrão. A presença dessa configuração não habilita chamada real sozinha; ela é apenas a trava explícita que será usada quando a integração real for implementada.

## Erros esperados

### Configuração ausente

Shopee:

- `ShopeeConfigurationError`

Amazon:

- `AmazonConfigurationError`

O harness transforma esses erros em mensagem amigável com exit code `2`.

### Limite inválido

Erro comum:

- `ProviderLimitError`

O harness transforma esse erro em mensagem amigável com exit code `3`. O próprio harness também bloqueia `--limit <= 0` antes de chamar os providers.

### HTTP inválido

Erro comum:

- `ProviderHttpError`

O harness transforma esse erro em mensagem amigável com exit code `3`.

### Transporte inválido

Erro comum:

- `HttpTransportError`

O harness transforma esse erro em mensagem amigável com exit code `3`.

### Payload inválido

Shopee:

- `ShopeePayloadError`

Amazon:

- `AmazonPayloadError`

Mapper base:

- `OfferMappingError`

O harness transforma os erros de payload de gateway em mensagem amigável com exit code `3`. Erros de mapper ainda devem ser tratados antes de fluxo real com payload externo.

## Segurança

Não versionar:

- tokens;
- cookies;
- QR codes;
- sessões;
- credenciais de marketplace;
- headers de autenticação;
- assinaturas reais.

Não imprimir em logs:

- chaves;
- segredos;
- cookies;
- tokens;
- payloads com dados sensíveis.

Durante a fase atual, qualquer chamada real deve continuar desabilitada por padrão.

## Próximos passos

- Conectar `enable_real_http` aos providers somente depois do checklist de produção.
- Implementar assinatura real da Amazon PA API em módulo isolado.
- Evoluir mappers com payloads reais anonimizados.
- Evoluir paginação com contratos reais quando houver fixtures seguras.
- Definir checklist antes de liberar qualquer publicação fora de dry-run.
