# Status da integração Shopee

Este arquivo registra o ponto exato em que a integração real com a Shopee foi pausada, para retomada futura sem perda de contexto.

## Status atual

**Status:** pausado, aguardando aprovação/liberação da conta Shopee.

A conta Shopee ainda está em análise. Por isso, a validação final de credenciais, permissões do app e contrato real do endpoint não pode ser concluída neste momento.

## O que já foi validado

- O fluxo mock do projeto segue funcionando.
- O `.env` local está ignorado pelo Git e não deve ser versionado.
- A trava `ENABLE_REAL_HTTP` existe e bloqueia chamadas reais por padrão.
- A trava `ENABLE_REAL_PUBLISH` deve permanecer desligada.
- O `safe_status` valida pré-requisitos antes de qualquer chamada real.
- O preview seguro do request mascara `partner_id` e `sign`.
- A base URL real usada nos testes manuais foi `https://partner.shopeemobile.com`.
- O path em análise foi `/api/v2/product/search_item`.
- O endpoint respondeu quando chamado sem query, indicando ausência de `partner_id`.
- O código passou a validar que `SHOPEE_PARTNER_ID` precisa ser numérico.
- O código passou a rejeitar payloads de erro da Shopee em vez de normalizar `0` ofertas silenciosamente.
- Foi criada ferramenta para capturar resposta real já anonimizada em `tmp/`.

## Evidências observadas

### Endpoint sem query

Resposta observada ao acessar o endpoint sem parâmetros:

```json
{
  "error": "error_param",
  "message": "There is no partner_id in query."
}
```

Interpretação: o host/path responde, mas exige parâmetros assinados.

### Partner id inválido

Resposta observada com valor de `SHOPEE_PARTNER_ID` não numérico ou fora do formato aceito:

```json
{
  "error": "error_param",
  "message": "Partner_id is invalid, should be an integer between 0 and 4294967295."
}
```

Interpretação: `SHOPEE_PARTNER_ID` deve ser somente numérico.

### Timestamp expirado

Resposta observada antes de sincronizar o relógio local:

```text
Shopee response returned error=error_param: Timestamp is expired.
```

Interpretação: o relógio local precisava de sincronização. Após ajuste do Windows Time Service, o erro evoluiu para HTTP 403, indicando que o timestamp deixou de ser o bloqueio principal.

### HTTP 403

Resposta observada após corrigir relógio e validar `partner_id` numérico:

```text
Shopee request failed with status=403
```

Interpretação atual: bloqueio provável de autorização, permissão, assinatura, app ainda em análise, endpoint não liberado para a conta ou credenciais incompatíveis com o app/endpoint.

## Configuração local esperada para retomada

Nunca versionar valores reais. Manter no `.env` local:

```text
ENABLE_REAL_HTTP=true
ENABLE_REAL_PUBLISH=false
SHOPEE_PARTNER_ID=<id_numerico_real>
SHOPEE_SECRET_KEY=<secret_key_real>
SHOPEE_TRACKING_ID=<tracking_id_se_aplicavel>
```

E, na sessão do PowerShell usada para os comandos reais:

```powershell
$env:SHOPEE_BASE_URL="https://partner.shopeemobile.com"
$env:SHOPEE_SEARCH_PATH="/api/v2/product/search_item"
$env:SHOPEE_SEARCH_PATH_CONFIRMED="true"
```

## Comandos para retomar quando a conta for aprovada

1. Atualizar repositório e rodar qualidade:

```powershell
cd C:\Automacao_Grupos-de-Ofertas
git pull
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

2. Validar variáveis sem expor segredo:

```powershell
.\.venv\Scripts\python.exe -c "from ofertas_bot.settings import get_settings; s=get_settings(); v=s.shopee_partner_id or ''; k=s.shopee_secret_key or ''; t=s.shopee_tracking_id or ''; print('partner_numeric=', v.isdecimal(), 'partner_len=', len(v)); print('secret_len=', len(k)); print('tracking_len=', len(t))"
```

3. Reconfigurar variáveis de sessão:

```powershell
$env:SHOPEE_BASE_URL="https://partner.shopeemobile.com"
$env:SHOPEE_SEARCH_PATH="/api/v2/product/search_item"
$env:SHOPEE_SEARCH_PATH_CONFIRMED="true"
```

4. Rodar status seguro:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.tools.safe_status --marketplace shopee
```

Resultado esperado antes de qualquer chamada real:

```text
INFO | Ambiente pronto para chamada real controlada
INFO | Publicação real continua fora do escopo deste status.
```

5. Rodar preview seguro:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 1 --print-provider-request
```

6. Conferir no painel/documentação oficial da conta aprovada se a assinatura esperada para o endpoint usa exatamente:

```text
partner_id + path + timestamp
```

Se o contrato exigir `access_token`, `shop_id`, `merchant_id`, outro path, outro host ou outro método HTTP, ajustar o `ShopeeSignedRequestBuilder` antes de nova chamada real.

7. Fazer uma única chamada real controlada:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 1 --execute-real-http-once
```

## O que não fazer enquanto a conta estiver em análise

- Não repetir chamadas reais em loop.
- Não ativar publicação real.
- Não salvar payload bruto.
- Não commitar `.env`.
- Não colar `SHOPEE_SECRET_KEY`, assinatura, tokens ou URL assinada em chat, issue ou commit.
- Não marcar a integração como concluída enquanto o HTTP 403 não for explicado.

## Critério para considerar esta etapa concluída

A integração Shopee só deve sair de `pausado` quando:

1. a conta/app Shopee estiver aprovada;
2. o endpoint real estiver confirmado no painel/documentação oficial;
3. a assinatura estiver compatível com o contrato oficial;
4. uma chamada real controlada com `--limit 1` retornar pelo menos uma resposta válida ou um payload vazio documentado como válido;
5. a resposta real for anonimizada antes de virar fixture;
6. `ruff` e `pytest` passarem sem erros;
7. `ENABLE_REAL_PUBLISH` continuar `false`.
