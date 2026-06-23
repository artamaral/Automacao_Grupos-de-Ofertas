# Persistência local opcional em JSON

## Objetivo

A persistência local em JSON permite salvar ofertas já normalizadas em arquivo local para inspeção, depuração e testes futuros.

Ela é opcional e só acontece quando a opção `--save-json` é informada no CLI.

## Módulo

Implementação atual:

```text
src/ofertas_bot/storage/json_offer_store.py
```

Componentes:

- `JsonOfferStore`;
- `offer_to_json()`;
- `offer_from_json()`;
- `OfferStoreError`.

## Uso no CLI

Exemplo:

```text
python -m ofertas_bot.harness --marketplace mock --niche maquiagem --limit 2 --save-json ./tmp/ofertas.json
```

Comportamento:

- sem `--save-json`, nenhum arquivo é gravado;
- com `--save-json`, o arquivo recebe uma lista de ofertas normalizadas;
- o diretório de destino é criado se não existir;
- a mensagem de sucesso informa o caminho usado.

## O que é salvo

A serialização salva apenas campos normalizados de `Offer`:

- marketplace;
- título;
- URL pública da oferta;
- URL pública de imagem, quando existir;
- preço;
- preço antigo;
- comissão numérica;
- vendas;
- avaliação;
- nicho;
- frete/benefício booleano.

## O que não deve ser salvo

Não salvar:

- chaves;
- tokens;
- cookies;
- sessões;
- QR codes;
- headers de autenticação;
- assinaturas;
- payload bruto com dados sensíveis.

## Comportamento técnico

- `save()` cria o diretório de destino se necessário;
- `load()` retorna lista vazia se o arquivo não existir;
- JSON inválido gera `OfferStoreError`;
- formato inválido gera `OfferStoreError`;
- itens inválidos geram `OfferStoreError`.

## Cuidados antes de uso real

Antes de usar com payload real anonimizado, validar:

1. caminho local seguro;
2. nenhuma credencial no payload;
3. mensagem clara ao usuário;
4. teste de escrita e leitura;
5. documentação atualizada.
