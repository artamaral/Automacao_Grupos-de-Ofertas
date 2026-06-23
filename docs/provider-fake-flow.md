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

## Erros esperados

### Configuração ausente

Shopee:

- `ShopeeConfigurationError`

Amazon:

- `AmazonConfigurationError`

O harness transforma esses erros em mensagem amigável com exit code `2`.

### HTTP inválido

Erro comum:

- `ProviderHttpError`

O harness transforma esse erro em mensagem amigável com exit code `3`.

### Payload inválido

Shopee:

- `ShopeePayloadError`

Amazon:

- `AmazonPayloadError`

O harness transforma esses erros em mensagem amigável com exit code `3`.

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

- Criar um transport HTTP real separado, com timeout e sem logs sensíveis.
- Adicionar configuração explícita para habilitar chamada real.
- Implementar assinatura real da Amazon PA API em módulo isolado.
- Evoluir mappers com payloads reais anonimizados.
- Criar testes de contrato usando fixtures sem dados sensíveis.
- Definir checklist antes de liberar qualquer publicação fora de dry-run.
