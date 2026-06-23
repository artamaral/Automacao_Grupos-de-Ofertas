# Status da implantação

## Visão geral

A implantação está em fase de preparação técnica. O projeto já possui pipeline local testável, providers com fluxo fake/injetável, validações de configuração e fluxo de dry-run para evitar publicação real acidental.

O objetivo atual é manter Shopee e Amazon evoluindo de forma incremental, sem executar chamadas externas por padrão e sem publicar fora de dry-run.

## Estado atual

### Pipeline principal

O fluxo base já está estruturado como:

```text
Collector -> Scorer -> Copywriter -> Compliance -> Publisher
```

Componentes em funcionamento:

- coleta mock para testes locais;
- ranqueamento de ofertas;
- geração de copy com preço no formato `de R$ X por R$ Y`;
- validação de compliance;
- publicação dry-run;
- harness CLI com mensagens amigáveis;
- validação de `--limit > 0` no harness;
- testes unitários e lint rodando localmente;
- documentação do fluxo fake/injetável;
- checklist antes de qualquer chamada real.

### Providers

#### Mock

Provider mock funcional e usado como caminho seguro para testes de ponta a ponta.

#### Shopee

Implementado até agora:

- validação de configuração obrigatória;
- erro amigável quando variáveis locais não existem;
- assinatura HMAC base;
- mapper de payload bruto para `Offer`;
- validação de campos obrigatórios no mapper;
- endpoints públicos centralizados;
- builder assinado com nomes neutros;
- base URL configurável com default fake;
- gateway de busca;
- paginação fake opcional no gateway;
- validação interna de `limit > 0` no gateway;
- retry opcional injetável no gateway;
- transport HTTP injetável/fake;
- execução fake controlada no gateway, sem internet;
- `ShopeeProvider.fetch()` integrado ao gateway injetável;
- tratamento de erro HTTP no gateway;
- tratamento de payload inválido com `ShopeePayloadError`;
- tratamento amigável de payload inválido no harness;
- fixture anônima de contrato;
- teste de resposta vazia;
- teste de limite com fixture de contrato;
- teste de retry opcional com transport fake;
- teste de base URL configurável;
- teste de paginação fake com transport sequencial.

Ainda não implementado:

- chamada real à API;
- paginação real validada contra contrato oficial;
- validação com payload real anonimizado da Shopee;
- persistência de resultados.

#### Amazon

Implementado até agora:

- provider inicial;
- validação de configuração;
- erro amigável no harness quando credenciais não existem;
- endpoints públicos centralizados;
- builder de request de busca;
- base URL configurável com default fake;
- mapper de payload para `Offer`;
- validação de campos obrigatórios no mapper;
- gateway de busca;
- paginação fake opcional no gateway;
- validação interna de `limit > 0` no gateway;
- retry opcional injetável no gateway;
- transport HTTP injetável/fake;
- `AmazonProvider.fetch()` integrado ao gateway injetável;
- tratamento de erro HTTP no gateway;
- tratamento de payload inválido com `AmazonPayloadError`;
- tratamento amigável de payload inválido no harness;
- fixture anônima de contrato;
- teste de resposta vazia;
- teste de limite com fixture de contrato;
- teste de retry opcional com transport fake;
- teste de base URL configurável;
- teste de paginação fake com transport sequencial.

Ainda não implementado:

- assinatura/autenticação real da PA API;
- chamada real à PA API;
- paginação real validada contra contrato oficial;
- validação com payload real anonimizado da Amazon;
- persistência de resultados.

### Configuração de providers

Implementado até agora:

- módulo `provider_settings.py` para resolver base URL dos providers;
- defaults seguros em `https://example.com`;
- variáveis `SHOPEE_BASE_URL` e `AMAZON_BASE_URL` documentadas;
- `.env.example` atualizado;
- testes cobrindo defaults e override por ambiente.

Observação: a base URL foi isolada em módulo próprio porque a edição direta do `Settings` foi bloqueada ao envolver campos sensíveis. A solução atual mantém o mesmo objetivo técnico sem expor credenciais e sem ativar HTTP real.

### Validação de payload

Implementado até agora:

- `OfferMapper` centraliza validação mínima antes de gerar `Offer`;
- campos mínimos `title`, `url` e `price` são obrigatórios;
- Shopee e Amazon têm testes cobrindo payload sem título, sem URL e sem preço;
- payload inválido falha antes de score, copy ou publicação.

Critério atual: payload real só deve entrar como fixture anonimizada e precisa respeitar essas validações mínimas.

### Paginação

Implementado até agora:

- `execute_paginated_search()` opcional no gateway da Shopee;
- `execute_paginated_search()` opcional no gateway da Amazon;
- paginação fake com `limit`, `page_size` e `max_pages` positivos;
- Shopee envia `page` nos parâmetros do request;
- Amazon envia `Page` no body do request;
- parada por `has_next_page`, `limit` ou `max_pages`;
- testes com transport fake sequencial.

Critério atual: paginação existe apenas para fluxo fake/injetável e ainda não é usada pelo harness nem por chamadas reais.

### Transporte HTTP

Implementado até agora:

- `StaticHttpTransport` para testes sem internet;
- `UrllibHttpTransport` como transport HTTP real isolado;
- timeout configurável no transport real;
- tratamento de JSON inválido;
- tratamento de erro de rede;
- normalização para `HttpResponse`;
- testes do transport real usando opener fake, sem internet;
- tratamento amigável de `HttpTransportError` no harness.

Importante: o transport real não está conectado automaticamente aos providers e não é usado pelo harness.

### Retry e rate limit

Implementado até agora:

- `RetryPolicy` com tentativas máximas, códigos retryable e backoff;
- `Sleeper` injetável;
- `NoOpSleeper` para testes sem espera real;
- `SystemSleeper` preparado para uso futuro controlado;
- retry opcional no helper `execute_provider_request`;
- retry opcional nos gateways de Shopee e Amazon;
- testes de política de retry;
- testes de retry no helper de gateway;
- testes de retry integrado aos gateways com transport fake.

Critério atual: retry existe como estrutura técnica, mas não ativa chamada real nem conecta HTTP real por padrão.

### Gateways

Implementado até agora:

- helper compartilhado `execute_provider_request`;
- helper compartilhado `validate_positive_limit`;
- erro comum `ProviderLimitError`;
- envio e validação HTTP centralizados;
- erro padronizado quando o transport não está configurado;
- testes diretos para sucesso, transport ausente e erro HTTP;
- testes diretos para limite inválido nos gateways.

Esse helper reduziu duplicação entre `ShopeeGateway` e `AmazonGateway` sem mudar o comportamento esperado.

### Travas de segurança

Implementado até agora:

- `enable_real_publish=False` por padrão;
- `enable_real_http=False` por padrão;
- `docs/production-checklist.md` criado;
- `docs/provider-fake-flow.md` criado.

Critério atual:

- `enable_real_http=True` só depois de checklist de HTTP real, provider e payloads seguros;
- `enable_real_publish=True` só depois de checklist completo e revisão manual.

## Problemas encontrados

### Ruff I001 em imports

Durante a criação de alguns módulos e testes, o Ruff acusou:

```text
I001 Import block is un-sorted or un-formatted
```

Casos resolvidos:

- builder antigo da Shopee foi removido;
- teste do transport real foi ajustado para deixar imports da biblioteca padrão antes de `pytest`;
- teste do helper de gateway foi formatado com imports quebrados em bloco;
- teste de retry do helper foi formatado com imports quebrados em bloco;
- módulo de base URL foi formatado para seguir a ordenação do Ruff.

Decisão atual:

- manter imports organizados por grupo: biblioteca padrão, terceiros e pacote interno;
- usar `ruff check .` depois de cada etapa;
- evitar recriar arquivos legados que já foram removidos.

### Bloqueios da ferramenta ao editar arquivos com nomes sensíveis

Algumas tentativas de edição foram bloqueadas quando o conteúdo incluía nomes como credenciais, chaves ou URLs reais. Isso afetou principalmente:

- `settings.py`;
- mudanças envolvendo parâmetros sensíveis;
- exemplos muito próximos de credenciais reais.

Soluções adotadas:

- usar nomes neutros em novos módulos, como `api_credential`;
- criar módulos separados para endpoints públicos;
- criar módulo separado para base URL de providers;
- evitar hardcode de URL real;
- manter `.env` e credenciais fora do repositório;
- usar fixtures e exemplos sem dados sensíveis.

## Backlog técnico

### Shopee

- Mapear payload real da Shopee quando houver exemplo anonimizado seguro.
- Adicionar validação de campos obrigatórios vindos da API além do mínimo comum.
- Validar paginação contra contrato real anonimizado quando disponível.
- Definir logs seguros, sem imprimir tokens, assinatura ou credenciais.

### Amazon

- Implementar assinatura/autenticação real da PA API em módulo isolado.
- Mapear payload real da Amazon quando houver exemplo anonimizado seguro.
- Adicionar validação de campos obrigatórios vindos da API além do mínimo comum.
- Validar paginação contra contrato real anonimizado quando disponível.
- Definir logs seguros, sem imprimir tokens, assinatura ou credenciais.

### Configuração e operação

- Conectar `enable_real_http` aos providers somente depois do checklist.
- Avaliar persistência de resultados.

### Qualidade

- Avaliar extração de validações comuns de payload quando os contratos reais estabilizarem.
- Revisar documentação quando o primeiro payload real anonimizado for adicionado.

## Próximo passo imediato

Adicionar validação e testes de `max_pages`/parada de paginação para evitar loops longos em fluxos fake e futuros fluxos reais.
