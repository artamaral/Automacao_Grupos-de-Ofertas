# Arquitetura n8n multi-nicho

Este documento define a arquitetura recomendada para operar multiplos nichos e
multiplos grupos dentro de uma unica execucao do `n8n`.

Objetivo principal:

- processar `feminino`, `mae-e-bebe` e `auto-e-moto` dentro do mesmo run;
- manter o custo de `n8n` no modelo mais economico possivel;
- escalar o numero de grupos sem reescrever o workflow;
- deixar a ativacao de grupos e destinos controlada por config.

## Decisao arquitetural

A arquitetura recomendada e:

```text
1 workflow
  -> 1 execucao
  -> N profiles
  -> N grupos
  -> N destinos
```

Regra operacional:

- o workflow do `n8n` deve rodar uma unica vez por janela operacional;
- dentro desse run, ele processa uma lista de `profiles`;
- cada `profile` gera sua propria rodada;
- cada rodada usa o mesmo contrato de artefatos;
- os grupos e destinos ativos sao resolvidos por config.

## Porque essa arquitetura importa

Se cada nicho virar um workflow separado, ou se cada mensagem virar uma
subexecucao separada, o consumo de execucoes do `n8n` sobe sem necessidade.

Com a arquitetura recomendada:

- `3` nichos no mesmo run continuam sendo `1` execucao;
- o volume cresce dentro do workflow, nao no contador de runs;
- a escalabilidade fica concentrada no config e nos artefatos, nao em novos
  workflows.

## Fluxo recomendado

```text
Trigger unico
  -> carregar lista de profiles ativos
  -> para cada profile:
       validar catalogo ativo
       rodar prepare
       aguardar revisao
       rodar finalize
       coletar dispatch_artifact do profile
  -> consolidar resumo final da janela
```

## Unidade de orquestracao

A unidade de orquestracao deve ser:

- `janela operacional`

Exemplo:

- uma janela da manha roda os tres nichos
- uma janela da tarde roda os tres nichos
- uma janela da noite roda os tres nichos

Cada janela dessas deve preferencialmente ser:

- `1 execucao do n8n`

## Unidade de selecao

A unidade de selecao continua sendo por `profile`:

- `feminino` seleciona seus `20` itens
- `mae-e-bebe` seleciona seus `20` itens
- `auto-e-moto` seleciona seus `20` itens

No mesmo run, isso pode representar:

- `60` mensagens base
- multiplicadas pelos destinos ativos do config

## Unidade de dispatch

A unidade de dispatch continua sendo por destino logico.

Exemplo:

- `grupo-beleza`
- `canal-beleza`
- `grupo-mae-e-bebe`
- `canal-mae-e-bebe`
- `grupo-auto-e-moto`
- `canal-auto-e-moto`

Mas esses destinos nao devem virar workflows separados.

Eles devem continuar como registros dentro do mesmo artifact:

- `dispatch_artifact.json`

## Fonte de verdade para ativacao de grupos

A ativacao de grupos e destinos deve ficar em:

- [`config/group_profiles.toml`](../config/group_profiles.toml)

## Regra de ativacao

Existem dois niveis de liga/desliga:

### 1. Nivel do profile

Campo:

- `active`

Efeito:

- liga ou desliga o grupo logico inteiro

Exemplo:

```toml
[[profiles]]
slug = "beleza-ofertas"
active = false
```

Resultado:

- nenhum destino desse profile entra na fila

### 2. Nivel do destino

Campo:

- `[[profiles.destinations]].active`

Efeito:

- liga ou desliga apenas aquele destino especifico

Exemplo:

```toml
[[profiles.destinations]]
destination_ref = "grupo-beleza"
channel_adapter = "whatsapp"
active = true

[[profiles.destinations]]
destination_ref = "canal-beleza"
channel_adapter = "telegram"
active = false
```

Resultado:

- `grupo-beleza` recebe mensagens
- `canal-beleza` nao entra na fila

## Escalabilidade para N grupos

O desenho atual ja suporta `N` destinos por profile porque `destinations` e uma
lista.

Exemplo:

```toml
[[profiles]]
slug = "beleza-ofertas"
name = "Beleza Ofertas"
allowed_niches = ["beleza", "feminino"]
allowed_marketplaces = ["mock", "shopee"]
active = true

[[profiles.destinations]]
destination_kind = "group"
destination_ref = "grupo-beleza-vip"
channel_adapter = "whatsapp"
active = true

[[profiles.destinations]]
destination_kind = "group"
destination_ref = "grupo-beleza-2"
channel_adapter = "whatsapp"
active = true

[[profiles.destinations]]
destination_kind = "channel"
destination_ref = "canal-beleza"
channel_adapter = "telegram"
active = true
```

Nao e necessario mudar o workflow para crescer de `2` para `10` destinos.

O crescimento deve acontecer por config.

## Regra de implementacao no n8n

O workflow nao deve hardcodar:

- nome de grupo
- nome de canal
- quantidade fixa de destinos

O workflow deve:

1. rodar por `profile`
2. deixar o projeto montar a `review_queue`
3. deixar o projeto montar o `publication_manifest`
4. deixar o projeto montar o `dispatch_artifact`
5. consumir o artifact pronto

## Config minima recomendada

Cada destino deve declarar no minimo:

- `destination_kind`
- `destination_ref`
- `channel_adapter`
- `active`
- `max_messages_per_run`
- `max_messages_per_hour`
- `min_interval_seconds`
- `quiet_periods`

## Regra de crescimento

Quando um novo grupo surgir, a ordem correta e:

1. adicionar novo `destination` no `config/group_profiles.toml`
2. definir `active = false`
3. validar o comportamento no fluxo
4. ativar `active = true` quando o grupo estiver pronto

Assim, o crescimento para `N` grupos continua:

- versionado
- auditavel
- reversivel

## Regra de custo

Para economizar execucoes no `n8n`:

- nao criar um workflow por nicho
- nao criar um workflow por grupo
- nao criar um workflow por mensagem
- manter tudo no mesmo run da janela operacional

## Resultado esperado

Com essa arquitetura:

- `3` nichos podem rodar na mesma execucao
- cada nicho continua com sua propria selecao
- os grupos podem ser ligados e desligados por config
- a operacao pode crescer para `N` destinos sem reescrever o workflow
