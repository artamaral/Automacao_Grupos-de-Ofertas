# Status da implantação

## Visão geral

A implantação está em fase de preparação técnica. O projeto já possui pipeline local testável, providers iniciais, validações de configuração e fluxo de dry-run para evitar publicação real acidental.

O objetivo atual é preparar a integração Shopee de forma incremental, sem executar chamadas externas até termos transporte, configuração e validações fechadas.

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
- testes unitários e lint rodando localmente.

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
- execução fake controlada no gateway, sem internet.

Ainda não implementado:

- chamada real à API;
- configuração real de base URL no `Settings`;
- paginação real;
- tratamento de payload real da Shopee;
- retries, timeout e rate limit;
- persistência de resultados.

#### Amazon

Implementado até agora:

- provider inicial;
- validação de configuração;
- erro amigável no harness quando credenciais não existem.

Ainda não implementado:

- request builder;
- assinatura/autenticação real;
- mapper de resposta real;
- transport real;
- integração com PA API.

## Problemas encontrados

### Ruff I001 no `shopee_request.py`

Durante a criação do primeiro builder de request Shopee, o Ruff acusou várias vezes:

```text
I001 Import block is un-sorted or un-formatted
```

Mesmo após ajustes de ordenação, o arquivo continuou causando falha local. A solução aplicada foi recriar o arquivo sem imports no topo e manter um builder alternativo mais limpo em `shopee_signed_request.py`.

Decisão atual:

- manter `shopee_signed_request.py` como caminho novo e preferencial;
- evitar evoluir o builder antigo até decidir se ele será removido;
- considerar remover `shopee_request.py` em uma etapa futura, se não houver dependências.

### Bloqueios da ferramenta ao editar arquivos com nomes sensíveis

Algumas tentativas de edição foram bloqueadas quando o conteúdo incluía nomes como credenciais, chaves ou URLs reais. Isso afetou principalmente:

- `settings.py`;
- `shopee_request.py`;
- mudanças envolvendo parâmetros sensíveis.

Soluções adotadas:

- usar nomes neutros em novos módulos, como `api_credential`;
- criar módulos separados para endpoints públicos;
- evitar hardcode de URL real;
- manter `.env` e credenciais fora do repositório.

## Backlog técnico

### Shopee

- Remover ou depreciar `src/ofertas_bot/providers/shopee_request.py`, se o novo builder substituir totalmente o antigo.
- Integrar `ShopeeProvider.fetch()` ao gateway com transport injetável.
- Adicionar geração de timestamp no provider, não no builder.
- Criar configuração para base URL sem expor credenciais.
- Mapear payload real da Shopee quando houver exemplo seguro.
- Adicionar validação de campos obrigatórios vindos da API.
- Adicionar tratamento para resposta vazia.
- Adicionar tratamento para status HTTP não 2xx.
- Adicionar timeout/retry/rate limit antes de qualquer chamada real.
- Definir logs seguros, sem imprimir tokens, assinatura ou credenciais.

### Amazon

- Criar builder de request.
- Criar mapper de resposta.
- Criar gateway e transport fake equivalente ao da Shopee.
- Adicionar testes para configuração e payloads.

### Configuração e operação

- Documentar variáveis de ambiente por provider.
- Definir diferença entre dry-run, fake transport e chamada real.
- Adicionar checklist de ativação para produção.
- Adicionar exemplos de execução local por marketplace.
- Avaliar remoção de arquivos legados ou duplicados quando o fluxo novo estabilizar.

### Qualidade

- Reduzir duplicação entre mapper do provider e gateway.
- Adicionar testes de erro para payload inválido em gateway.
- Adicionar testes de erro HTTP no gateway.
- Revisar mensagens de exceção para manter padrão `ERRO | DETALHE | AÇÃO` no CLI.

## Próximo passo imediato

Conectar o `ShopeeProvider.fetch()` ao `ShopeeGateway.execute_search()` quando um gateway com transport fake for injetado. O comportamento padrão continuará seguro: sem gateway/transport real, nenhuma chamada externa será executada.
