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
- endpoints públicos centralizados;
- builder assinado com nomes neutros;
- gateway de busca;
- transport HTTP injetável/fake;
- execução fake controlada no gateway, sem internet;
- `ShopeeProvider.fetch()` integrado ao gateway injetável;
- tratamento de erro HTTP no gateway;
- tratamento de payload inválido com `ShopeePayloadError`;
- tratamento amigável de payload inválido no harness.

Ainda não implementado:

- chamada real à API;
- configuração real de base URL no `Settings`;
- paginação real;
- validação com payload real anonimizado da Shopee;
- retries e rate limit;
- persistência de resultados.

#### Amazon

Implementado até agora:

- provider inicial;
- validação de configuração;
- erro amigável no harness quando credenciais não existem;
- endpoints públicos centralizados;
- builder de request de busca;
- mapper de payload para `Offer`;
- gateway de busca;
- transport HTTP injetável/fake;
- `AmazonProvider.fetch()` integrado ao gateway injetável;
- tratamento de erro HTTP no gateway;
- tratamento de payload inválido com `AmazonPayloadError`;
- tratamento amigável de payload inválido no harness.

Ainda não implementado:

- assinatura/autenticação real da PA API;
- chamada real à PA API;
- configuração real de base URL no `Settings`;
- validação com payload real anonimizado da Amazon;
- retries e rate limit;
- persistência de resultados.

### Transporte HTTP

Implementado até agora:

- `StaticHttpTransport` para testes sem internet;
- `UrllibHttpTransport` como transport HTTP real isolado;
- timeout configurável no transport real;
- tratamento de JSON inválido;
- tratamento de erro de rede;
- normalização para `HttpResponse`;
- testes do transport real usando opener fake, sem internet.

Importante: o transport real não está conectado automaticamente aos providers e não é usado pelo harness.

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
- teste do transport real foi ajustado para deixar imports da biblioteca padrão antes de `pytest`.

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
- evitar hardcode de URL real;
- manter `.env` e credenciais fora do repositório;
- usar fixtures e exemplos sem dados sensíveis.

## Backlog técnico

### Shopee

- Criar configuração para base URL sem expor credenciais.
- Mapear payload real da Shopee quando houver exemplo anonimizado seguro.
- Adicionar validação de campos obrigatórios vindos da API.
- Adicionar tratamento para resposta vazia.
- Adicionar retry/rate limit antes de qualquer chamada real.
- Definir logs seguros, sem imprimir tokens, assinatura ou credenciais.

### Amazon

- Implementar assinatura/autenticação real da PA API em módulo isolado.
- Criar configuração para base URL sem expor credenciais.
- Mapear payload real da Amazon quando houver exemplo anonimizado seguro.
- Adicionar validação de campos obrigatórios vindos da API.
- Adicionar tratamento para resposta vazia.
- Adicionar retry/rate limit antes de qualquer chamada real.
- Definir logs seguros, sem imprimir tokens, assinatura ou credenciais.

### Configuração e operação

- Documentar variáveis de ambiente por provider.
- Adicionar exemplos de execução local por marketplace.
- Conectar `enable_real_http` aos providers somente depois do checklist.
- Criar fixtures de contrato com payloads anonimizados.
- Avaliar persistência de resultados.

### Qualidade

- Reduzir duplicação entre gateways de Shopee e Amazon.
- Revisar mensagens de exceção para manter padrão `ERRO | DETALHE | AÇÃO` no CLI.
- Criar testes para resposta vazia por provider.
- Criar testes para limites e paginação quando os contratos reais forem definidos.

## Próximo passo imediato

Documentar variáveis de ambiente por provider e exemplos de execução local seguros, mantendo `mock` e `dry-run` como caminhos padrão.
