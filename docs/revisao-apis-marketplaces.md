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

### Impacto no projeto

- Não devemos tratar a integração Amazon atual como contrato final.
- Antes de chamada real na Amazon, decidir se o projeto continua temporariamente com PA-API 5.0 ou se migra o desenho para Creators API.
- O builder atual da Amazon deve continuar protegido por guard e testes, sem chamada real automática.

### Decisão pendente

- [ ] Confirmar se a conta do projeto ainda terá acesso útil à PA-API 5.0.
- [ ] Avaliar se a Creators API atende melhor ao fluxo de ofertas afiliadas.
- [ ] Só depois decidir a próxima integração real da Amazon.

## Shopee

### Achado

O endpoint público atual da Shopee não foi confirmado de forma suficiente durante o desenvolvimento. O caminho usado no código foi mantido como provisório:

```text
/api/v2/product/search_item
```

### Impacto no projeto

- Não devemos executar chamada real na Shopee sem confirmar o endpoint oficial no painel/documentação da conta usada.
- O preview seguro deve ser usado para comparar método, host, path e parâmetros antes da primeira chamada.
- O caminho do endpoint deve ser configurável fora do Git, para não depender de valor hardcoded caso o contrato oficial seja diferente.

### Decisão pendente

- [ ] Confirmar host/base URL oficial da conta Shopee.
- [ ] Confirmar path oficial do endpoint de busca/listagem.
- [ ] Confirmar método HTTP.
- [ ] Confirmar parâmetros obrigatórios.
- [ ] Confirmar formato da assinatura.
- [ ] Confirmar formato da resposta.

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
