# Status da persistência JSON local

## Concluído

A persistência local opcional em JSON foi implementada e documentada.

Itens cobertos:

- pacote `src/ofertas_bot/storage/`;
- `JsonOfferStore.save()`;
- `JsonOfferStore.load()`;
- serialização de ofertas normalizadas;
- restauração de ofertas normalizadas;
- retorno de lista vazia quando o arquivo não existe;
- erro controlado para JSON inválido;
- erro controlado para formato inválido;
- erro controlado para falha de escrita;
- opção explícita `--save-json` no harness;
- teste garantindo que o fluxo padrão não grava arquivo;
- teste garantindo que `--save-json` grava apenas quando solicitado;
- teste de erro amigável quando o caminho não pode ser escrito.

## Escopo atual

A gravação é local, opcional e não acontece por padrão.

O JSON deve conter apenas campos normalizados de oferta e não deve conter credenciais, tokens, cookies, sessões, QR codes, headers de autenticação ou payload bruto sensível.

## Próximo passo

Preparar critérios de limpeza e exclusão futura para arquivos de saída local, evitando que resultados temporários sejam versionados por engano.
