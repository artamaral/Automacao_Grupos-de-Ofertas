# Padrão de mensagens e logs CLI

Este projeto roda principalmente em linha de comando. Por isso, toda mensagem impressa no terminal deve ser clara, acionável e segura.

## Objetivos

- facilitar debug local;
- evitar tracebacks desnecessários para erros esperados;
- deixar claro o que aconteceu, o motivo e a próxima ação;
- não vazar credenciais, tokens, cookies, QR codes ou sessões;
- manter uma saída legível para uso humano e futura automação.

## Formato recomendado

Use prefixos simples em caixa alta:

```text
INFO | mensagem informativa
WARN | situação bloqueada ou atenção necessária
ERRO | falha esperada e tratada
AÇÃO | próximo passo sugerido
DETALHE | contexto técnico seguro
```

Exemplo:

```text
ERRO | Configuração da Shopee incompleta
DETALHE | Missing Shopee configuration: SHOPEE_PARTNER_ID, SHOPEE_SECRET_KEY.
AÇÃO | Configure o arquivo .env local ou rode com --marketplace mock.
```

## Regras para erros esperados

Erros esperados devem ser tratados sem traceback, por exemplo:

- credenciais ausentes;
- limit inválido;
- provider ainda não implementado;
- marketplace sem suporte;
- payload de provider em formato inesperado;
- falha HTTP de provider;
- falha de transporte HTTP;
- falha ao salvar JSON local;
- oferta bloqueada por compliance;
- publicação real desabilitada.

Traceback completo deve ficar reservado para bugs inesperados durante desenvolvimento.

## Exemplos de erros tratados

### Configuração ausente

```text
ERRO | Configuração da Amazon incompleta
DETALHE | Missing Amazon configuration: AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY.
AÇÃO | Configure o arquivo .env local ou rode com --marketplace mock.
```

### Limit inválido no CLI

```text
ERRO | Limite de ofertas inválido
DETALHE | --limit deve ser maior que zero. Valor recebido: 0
AÇÃO | Informe um valor positivo, por exemplo --limit 5.
```

### Limit inválido no provider

```text
ERRO | Limite interno de provider inválido
DETALHE | Provider limit must be greater than zero. Received: 0
AÇÃO | Revise a origem do limite antes de executar novamente.
```

### Payload inválido

```text
ERRO | Resposta da Shopee em formato inesperado
DETALHE | Shopee response field 'items' must be a list
AÇÃO | Valide o payload retornado pelo provider antes de publicar ofertas.
```

### HTTP inválido

```text
ERRO | Falha na resposta HTTP da Amazon
DETALHE | Amazon request failed with status=500
AÇÃO | Verifique status, rate limit e disponibilidade antes de nova tentativa.
```

### Falha de transporte

```text
ERRO | Falha de transporte HTTP da Amazon
DETALHE | HTTP transport request failed
AÇÃO | Verifique conexão, timeout e configuração antes de nova tentativa.
```

### Falha ao salvar JSON

```text
ERRO | Não foi possível salvar o JSON de ofertas
DETALHE | Could not write offers JSON to ./tmp
AÇÃO | Verifique se o caminho é um arquivo válido e se há permissão de escrita.
```

## Opção `--save-json`

A opção `--save-json` salva as ofertas normalizadas em um arquivo JSON local somente quando informada explicitamente.

Exemplo recomendado:

```text
python -m ofertas_bot.harness --marketplace mock --niche maquiagem --limit 2 --save-json ./.data/ofertas.json
```

Para testes rápidos também é possível usar:

```text
python -m ofertas_bot.harness --marketplace mock --niche maquiagem --limit 2 --save-json ./tmp/ofertas.json
```

Mensagem esperada:

```text
INFO | Ofertas normalizadas salvas em .data/ofertas.json
```

Aviso esperado quando o arquivo for salvo diretamente no diretório atual:

```text
WARN | O arquivo ofertas.json será salvo no diretório atual. Prefira .data/, tmp/ ou exports/ para evitar commit acidental.
```

Regras:

- o fluxo padrão não grava arquivo;
- o arquivo deve conter apenas campos normalizados de `Offer`;
- não salvar credenciais, tokens, cookies, sessões, headers, QR codes ou payload bruto;
- usar caminhos locais ignorados pelo Git, como `./.data/`, `./tmp/` ou `./exports/`;
- evitar salvar arquivos de saída diretamente na raiz do repositório;
- se um arquivo na raiz for solicitado, a CLI apenas avisa e continua;
- erro de escrita deve retornar mensagem amigável e exit code `3`.

## Regras para mensagens de sucesso

Mensagens de sucesso devem responder:

1. o que rodou;
2. quantos itens foram processados;
3. qual marketplace/nicho foi usado;
4. se houve publicação real ou dry-run.

Exemplo:

```text
INFO | Encontradas 2 ofertas para nicho=maquiagem marketplace=mock
INFO | Oferta #1 score=91.39 aprovado=True
INFO | dry_run=True sent=False target=grupo-vip-dry-run
```

## Regras de segurança

Nunca imprimir:

- tokens;
- secret keys;
- cookies;
- QR codes;
- conteúdo de sessão;
- headers de autenticação;
- links internos sensíveis.

Pode imprimir nomes de variáveis ausentes, como:

```text
SHOPEE_PARTNER_ID
SHOPEE_SECRET_KEY
```

Mas nunca os valores.

## Saída de mensagens de oferta

A mensagem da oferta pode ser impressa inteira em modo `dry-run`, porque é exatamente o conteúdo que seria revisado antes da publicação.

Ainda assim, deve sempre conter aviso de afiliado e alerta de preço/disponibilidade.

## Códigos de saída

Sempre que possível:

- `0`: execução concluída com sucesso;
- `1`: erro inesperado;
- `2`: erro esperado de configuração;
- `3`: erro esperado de validação, compliance, HTTP, transporte ou entrada inválida.

## Diretriz final

A CLI deve ajudar o operador a decidir o próximo passo sem precisar abrir o código.
