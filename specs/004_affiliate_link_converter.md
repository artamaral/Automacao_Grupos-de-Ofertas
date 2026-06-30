# SPEC 004 — Conversão e Validação de Links Afiliados

Status: Rascunho

## Objetivo

Definir como o projeto deve receber, converter, validar e preservar links de afiliado de forma segura e auditável.

## Contexto

Links podem vir prontos da entrada ou serem retornados por APIs de afiliados. O pipeline não deve publicar link sem validação mínima nem esconder a natureza afiliada da mensagem.

## Entrada

Possíveis entradas:

- link original do produto;
- link afiliado já convertido;
- identificador de produto;
- marketplace;
- parâmetros necessários para API de afiliados;
- credenciais locais via `.env`, nunca versionadas.

## Saída

Oferta com link final de destino, preferencialmente em campo explícito:

```text
affiliate_url
```

Quando não houver link afiliado, manter o link original apenas se a regra de negócio permitir e a mensagem não fingir que é afiliada.

## Regras obrigatórias

- Não versionar credenciais.
- Não inventar link afiliado.
- Não publicar link vazio.
- Não sobrescrever link original sem rastreabilidade.
- Registrar marketplace de origem.
- Manter disclosure quando o link final for afiliado.
- HTTP real só pode ocorrer com `ENABLE_REAL_HTTP=true`.

## Shopee

Quando a Shopee for usada em modo real, parâmetros de API devem seguir exatamente o que foi solicitado na tarefa ou configurado explicitamente.

Não inferir automaticamente:

```text
keyword
listType
matchId
sortType
shopId
itemId
productCatId
isAMSOffer
isKeySeller
```

## Amazon

Quando Amazon PA API for usada em modo real, a integração deve respeitar credenciais locais, partner tag e travas de HTTP real.

## Fora de escopo

- Publicação em canal.
- Geração de copy final.
- Crawler sem API autorizada.
- Bypass de política ou limite de marketplace.

## Critérios de aceite

- Dado link afiliado válido, ele é preservado.
- Dado link original e conversor fake, a saída recebe link convertido fake em teste.
- Dado link ausente, a oferta é bloqueada ou sinalizada.
- Dado `ENABLE_REAL_HTTP=false`, nenhuma chamada real ocorre.
- Mensagem final com link afiliado inclui disclosure.

## Testes esperados

- Teste com conversor fake.
- Teste com link ausente.
- Teste de preservação de link afiliado existente.
- Teste de bloqueio de HTTP real por padrão.
- Teste de integração com compliance de disclosure.

## Harness / validação local

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage prepare --niche maquiagem --marketplace mock --target grupo-maquiagem
```
