# Catalogo de grupos de destino

O catálogo operacional de grupos de destino fica em:

```text
config/group_profiles.toml
```

Esse arquivo define, por grupo:

- `slug`
- `name`
- `allowed_niches`
- `allowed_marketplaces`
- `destinations`
- `destination_kind`
- `destination_ref`
- `channel_adapter`
- `message_tone`
- `allowed_content_types`
- `max_offers_per_run`
- `min_minutes_between_posts`
- `active`

Objetivo desta camada:

- organizar destinos lógicos antes da API real;
- separar macro-nicho de destino operacional;
- declarar por qual canal o destino deve ser tratado no disparo;
- registrar tom e tipos de conteúdo aceitos por grupo;
- preparar a futura decisão de roteamento sem endurecer regra cedo demais.

Regra atual:

- este catálogo é fonte de verdade para grupos de destino;
- um grupo pode declarar um destino simples ou uma lista `destinations`;
- a fila de revisão deve usar esse catálogo para gerar itens já roteados por grupo;
- um mesmo draft pode aparecer mais de uma vez na fila se for elegível para mais de um grupo ou para mais de um destino dentro do mesmo grupo;
- itens sem correspondência continuam possíveis e devem aparecer como sem rota;
- ele ainda não implementa decisão automática completa;
- ele serve para estruturar a operação e reduzir improviso quando os dados reais
  chegarem.

Exemplo de múltiplos destinos no mesmo grupo:

```toml
[[profiles]]
slug = "beleza-ofertas"
name = "Beleza Ofertas"
allowed_niches = ["beleza"]

[[profiles.destinations]]
destination_kind = "group"
destination_ref = "grupo-beleza"
channel_adapter = "whatsapp"

[[profiles.destinations]]
destination_kind = "channel"
destination_ref = "canal-beleza"
channel_adapter = "telegram"
```
