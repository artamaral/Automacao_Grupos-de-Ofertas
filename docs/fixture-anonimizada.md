# Fluxo de fixture anonimizada

## Objetivo

Definir como transformar uma resposta real bruta em fixture segura para testes.

A regra principal é: payload bruto nunca deve ser commitado.

## Comando local

Use o comando abaixo para gerar uma versão anonimizada de um JSON bruto salvo localmente:

```text
python -m ofertas_bot.tools.anonymize_payload --input tmp/raw-shopee-response.json --output tests/fixtures/shopee-real-anonymized.json
```

## Ordem segura

1. Executar chamada real controlada com `--limit 1`.
2. Salvar o payload bruto apenas em pasta local ignorada pelo Git, como `tmp/`.
3. Rodar o comando de anonimização.
4. Revisar manualmente o JSON anonimizado.
5. Confirmar que não existe dado sensível.
6. Só então usar o JSON como fixture em testes.

## Campos tratados automaticamente

O anonimizador remove ou substitui campos que parecem conter:

- assinatura;
- credencial;
- chave secreta;
- token;
- sessão;
- cookie;
- e-mail;
- telefone;
- URL real;
- imagem real;
- identidade de loja/vendedor/usuário;
- nome/título de produto real.

## Limites do anonimizador

O anonimizador é uma camada auxiliar, não uma garantia absoluta.

Sempre revisar manualmente antes de commitar qualquer fixture.

## O que não fazer

- Não commitar payload bruto.
- Não commitar resposta completa sem revisão.
- Não commitar valores de autenticação.
- Não commitar URL real de produto, imagem, loja ou usuário.
- Não commitar prints de terminal com dados sensíveis.

## Depois de criar a fixture

Depois de criar uma fixture segura:

1. criar teste do mapper com o formato real anonimizado;
2. ajustar campos esperados;
3. rodar `ruff` e `pytest`;
4. manter a fixture pequena e focada no contrato necessário.
