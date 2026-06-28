# Cloud Runner n8n

Este documento descreve a trilha paralela para operacao autonoma em nuvem,
mantendo a solucao local/self-hosted atual intacta.

## Objetivo

Permitir que o `n8n` hospedado orquestre o fluxo real por HTTP, sem depender de:

- `Execute Command`
- PowerShell no host do `n8n`
- acesso direto ao filesystem `C:\...` pelo `n8n`

## Estrategia

O runtime continua reaproveitando o pipeline atual do projeto, mas passa a ser
exposto por um servidor HTTP proprio:

- `GET /health`
- `POST /prepare-window`
- `POST /finalize-window`
- `POST /dispatch-window`
- `POST /run-window`
- `POST /confirm-delivery`
- `POST /confirm-window-deliveries`

Esse runner fica em paralelo ao caminho atual:

- solucao atual: local/self-hosted
- nova solucao: runner HTTP cloud-ready

## Entry point

Script disponivel no projeto:

```text
ofertas-cloud-runner
```

Implementacao:

- [`src/ofertas_bot/cloud_runner.py`](../src/ofertas_bot/cloud_runner.py)
- [`src/ofertas_bot/cloud_runner_server.py`](../src/ofertas_bot/cloud_runner_server.py)

## Endpoints

### Health

```http
GET /health
```

Resposta:

```json
{
  "status": "ok",
  "result": {
    "status": "ok",
    "service": "ofertas-cloud-runner",
    "allowed_profiles": ["feminino", "mae-e-bebe", "auto-e-moto"]
  }
}
```

### Prepare window

```http
POST /prepare-window
Content-Type: application/json
```

Payload minimo:

```json
{
  "profiles_csv": "feminino,mae-e-bebe,auto-e-moto",
  "run_id": "2026-06-28-janela-01",
  "root_dir": "C:\\Automacao_Grupos-de-Ofertas\\n8n\\root",
  "app_dir": "C:\\Automacao_Grupos-de-Ofertas"
}
```

### Finalize window

```http
POST /finalize-window
Content-Type: application/json
```

Payload minimo:

```json
{
  "profiles_csv": "feminino,mae-e-bebe,auto-e-moto",
  "run_id": "2026-06-28-janela-01",
  "root_dir": "C:\\Automacao_Grupos-de-Ofertas\\n8n\\root",
  "app_dir": "C:\\Automacao_Grupos-de-Ofertas"
}
```

### Dispatch window

```http
POST /dispatch-window
Content-Type: application/json
```

Payload minimo:

```json
{
  "profiles_csv": "feminino,mae-e-bebe,auto-e-moto",
  "run_id": "2026-06-28-janela-01",
  "root_dir": "C:\\Automacao_Grupos-de-Ofertas\\n8n\\root",
  "app_dir": "C:\\Automacao_Grupos-de-Ofertas",
  "allowed_targets_csv": "grupo-teste-controlado"
}
```

Objetivo:

- carregar os `dispatch_artifact.json` da janela;
- filtrar os destinos permitidos para o teste controlado;
- devolver as mensagens prontas para o `n8n` enviar no canal real.

### Run window

```http
POST /run-window
Content-Type: application/json
```

Payload minimo:

```json
{
  "profiles_csv": "feminino,mae-e-bebe,auto-e-moto",
  "run_id": "2026-06-28-janela-01",
  "root_dir": "C:\\Automacao_Grupos-de-Ofertas\\n8n\\root",
  "app_dir": "C:\\Automacao_Grupos-de-Ofertas",
  "allowed_targets_csv": "grupo-teste-controlado"
}
```

Objetivo:

- executar `prepare` e `finalize` numa chamada unica;
- devolver no mesmo retorno a lista `deliveries[]` pronta para envio real;
- manter `last_sent_at` adiado ate a confirmacao externa de entrega.

### Confirm delivery

```http
POST /confirm-delivery
Content-Type: application/json
```

Payload minimo:

```json
{
  "profile": "feminino",
  "target": "grupo-teste-controlado",
  "manifest_item_number": 1,
  "root_dir": "C:\\Automacao_Grupos-de-Ofertas\\n8n\\root",
  "app_dir": "C:\\Automacao_Grupos-de-Ofertas"
}
```

Objetivo:

- confirmar no projeto apenas a mensagem que realmente saiu no canal;
- atualizar `last_sent_at` no `selection_state.json` somente apos sucesso real.

### Confirm window deliveries

```http
POST /confirm-window-deliveries
Content-Type: application/json
```

Payload minimo:

```json
{
  "root_dir": "C:\\Automacao_Grupos-de-Ofertas\\n8n\\root",
  "app_dir": "C:\\Automacao_Grupos-de-Ofertas",
  "deliveries": [
    {
      "profile": "feminino",
      "target": "grupo-teste-controlado",
      "manifest_item_number": 1
    }
  ]
}
```

## Observacao importante

Nesta primeira implementacao paralela, o runner HTTP ainda reutiliza:

- `catalogs/`
- `data/`
- `local_flow_cli`

No modo `real controlado`, o envio continua fora do Python:

- o Python monta e valida a rodada;
- o `n8n` faz o envio real pelo provedor de `WhatsApp` configurado;
- o `n8n` confirma de volta ao runner quais mensagens realmente sairam.

Ou seja:

- o caminho cloud foi preparado em paralelo
- o contrato HTTP ja existe
- storage realmente cloud-native ainda pode ser evolucao posterior

## Quando usar cada caminho

### Caminho atual

Usar quando houver:

- ambiente local
- ambiente self-hosted
- shell e filesystem disponiveis

### Caminho cloud runner

Usar quando houver:

- `n8n` hospedado
- necessidade de orquestracao autonoma por HTTP
- possibilidade de expor ou publicar um runner do projeto em ambiente proprio

## Decisao pragmatica desta fase

Para evitar custo, acoplamento prematuro ou decisao antecipada de dominio:

- `Quick Tunnel` continua aceito para validacao e prova do fluxo;
- dominio proprio e hostname estavel nao sao obrigatorios nesta etapa;
- `named tunnel` com URL estavel deve entrar apenas quando a operacao pedir
  repetibilidade suficiente para justificar essa decisao;
- enquanto isso, a referencia oficial continua sendo o contrato HTTP do runner,
  e nao uma tecnologia especifica de exposicao.
