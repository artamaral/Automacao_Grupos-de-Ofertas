# Persistência local opcional em JSON

## Objetivo

A persistência local em JSON permite salvar ofertas já normalizadas em arquivo local para inspeção, depuração e testes futuros.

Ela é opcional e não é chamada automaticamente pelo harness.

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

## Comportamento atual

- `save()` cria o diretório de destino se necessário;
- `load()` retorna lista vazia se o arquivo não existir;
- JSON inválido gera `OfferStoreError`;
- formato inválido gera `OfferStoreError`;
- itens inválidos geram `OfferStoreError`.

## Uso futuro

Este módulo pode ser conectado futuramente a uma opção explícita do CLI, por exemplo `--save-json`, mas não deve gravar nada automaticamente.

Antes de conectar ao harness, validar:

1. caminho local seguro;
2. nenhuma credencial no payload;
3. mensagem clara ao usuário;
4. teste de escrita e leitura;
5. documentação atualizada.
