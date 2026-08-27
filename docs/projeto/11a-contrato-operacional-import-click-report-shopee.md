# Contrato operacional — importação manual do Click Report Shopee

Status: complemento normativo da spec `11-spec-rastreamento-cliques-conversoes-shopee.md`.

## 1. Decisão

O Click Report da Shopee é obtido manualmente pelo operador no Portal/Central do Afiliado e posteriormente importado para o Supabase.

Como esta etapa é manual, **o operador é responsável por garantir que o arquivo entregue para importação esteja no formato definido neste contrato**.

O importador não deve tentar descobrir delimitadores, reorganizar Sub IDs, adivinhar formatos alternativos ou corrigir silenciosamente arquivos fora do padrão.

Arquivo incompatível com o contrato deve ser rejeitado antes de persistir eventos no Supabase.

## 2. Layout mínimo obrigatório

O arquivo preparado para importação deve preservar os campos do Click Report e apresentar, no mínimo:

| Coluna | Obrigatória | Origem |
| --- | --- | --- |
| `click_id` | sim | `ID dos Cliques` |
| `click_time` | sim | `Tempo dos Cliques` |
| `click_region` | não | `Região dos Cliques` |
| `referrer` | não | `Referenciador` |
| `sub_id_raw` | sim | valor original de `Sub_id`, preservado sem alteração |
| `tracking_channel` | sim para registros rastreáveis | primeiro Sub ID |
| `tracking_profile` | sim para registros rastreáveis | segundo Sub ID |
| `tracking_dispatch_id` | sim para registros rastreáveis | terceiro Sub ID |
| `tracking_item_id` | sim para registros rastreáveis | quarto Sub ID |

Os quatro campos de tracking devem obedecer ao contrato de geração da short URL:

```text
tracking_channel     = wa
tracking_profile     = <daily_dispatch_plan.profile>
tracking_dispatch_id = dp<dispatch_plan_id sem hifens>
tracking_item_id     = <item_id como texto>
```

Exemplo:

```text
wa
feminino
dp550e8400e29b41d4a716446655440000
18797641257
```

## 3. Responsabilidade do operador

Antes da importação, o operador deve:

1. baixar o Click Report no Portal/Central do Afiliado;
2. preservar o arquivo original para auditoria;
3. separar os `Sub_id(s)` nas quatro colunas de tracking definidas acima, conforme o recurso de separação disponibilizado pela própria Shopee/planilha;
4. conferir que a ordem dos quatro valores corresponde ao contrato do projeto;
5. não modificar `sub_id_raw`;
6. validar que `tracking_dispatch_id` segue o formato `dp` + 32 caracteres hexadecimais do UUID sem hífens;
7. validar que `tracking_item_id` contém o `item_id` anunciado;
8. somente então disponibilizar o arquivo preparado para importação no Supabase.

O teste empírico do CSV da short URL `https://s.shopee.com.br/3g3DPzjYgO` continua útil para documentar como a Shopee exporta originalmente os múltiplos Sub IDs, mas **não muda a responsabilidade operacional acima**.

## 4. Regra do importador

O importador deve ser determinístico e estrito.

Ele deve:

- aceitar somente o layout definido;
- preservar `sub_id_raw` e a linha original em `raw_row`/estrutura equivalente;
- reconstruir `dispatch_plan_id` apenas a partir de `tracking_dispatch_id` válido;
- validar o `tracking_item_id` contra `daily_dispatch_plan.item_id` quando o plano for encontrado;
- registrar erro/rejeição quando o formato obrigatório estiver ausente ou inválido;
- nunca inventar valores de tracking;
- nunca usar `referrer` como fallback de atribuição;
- nunca liberar uma linha inválida como clique atribuído.

## 5. Registros legados

Registros históricos com:

```text
Sub_id = ----
```

podem ser importados como raw clicks não atribuídos.

Nesses casos:

```text
tracking_channel     = NULL
tracking_profile     = NULL
tracking_dispatch_id = NULL
tracking_item_id     = NULL
dispatch_plan_id     = NULL
tracking_parse_status = legacy_empty
```

Eles permanecem úteis para volume bruto de cliques, mas não entram em análises por exposição que exijam `dispatch_plan_id`.

## 6. Consequência para o schema

`offers.shopee_click_events` deve preservar o raw e pode receber diretamente os campos normalizados preparados pelo operador:

```text
click_event_id
import_id
click_id
click_time
click_region
referrer
sub_id_raw
tracking_channel
tracking_profile
tracking_dispatch_id
tracking_item_id
dispatch_plan_id
tracking_parse_status
tracking_parse_error
raw_row
created_at
```

Com esse contrato, a lógica de importação não depende do delimitador originalmente utilizado pela Shopee no CSV bruto. O delimitador/export original é uma característica da etapa manual de preparação, não uma regra que o backend precise inferir.
