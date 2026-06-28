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

## Observacao importante

Nesta primeira implementacao paralela, o runner HTTP ainda reutiliza:

- `catalogs/`
- `data/`
- `local_flow_cli`

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
