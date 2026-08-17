# Spec — Redistribuição editorial do perfil `feminino`

Status: proposta aprovada para implementação

Escopo: somente planejamento/seleção editorial do perfil `feminino`

## 1. Objetivo

Reduzir a concentração de publicações de Moda no perfil `feminino`, agregando subnichos de moda em grupos editoriais mais amplos e redistribuindo slots para beleza e cuidados, sem alterar o score comercial nem o restante do pipeline.

A mudança deve preservar:

- 112 publicações planejadas por dia;
- 96 slots `fixed_daily`;
- 16 slots `weekly_rotation`;
- score `commercial_v1` sem qualquer alteração;
- filtros de elegibilidade existentes;
- mecanismo atual de fallback para não deixar slots vazios;
- catálogo e `subniches` atuais sem migração destrutiva;
- dispatcher, copywriter e publicação sem mudança de contrato.

## 2. Limite explícito desta entrega

Esta alteração deve ficar restrita à composição editorial do plano diário do perfil `feminino`.

Não fazer nesta entrega:

- corrigir o problema conhecido de refresh/itens `STALE`;
- alterar `commercial_v1` ou qualquer componente de score;
- alterar pesos de comissão, vendas, rating, desconto, frete ou shop type;
- refatorar a taxonomia do catálogo;
- remover ou renomear `subniches` armazenados;
- implementar canonicalização/equivalência de produtos;
- alterar geração de link afiliado;
- alterar copywriter;
- alterar horários de publicação;
- alterar envio ao WhatsApp/n8n;
- criar novos CLIs sem necessidade operacional clara.

Se a implementação exigir mudança fora desse limite, interromper a expansão de escopo e registrar a dependência separadamente.

## 3. Contexto operacional

A regra atual possui dois buckets:

- `fixed_daily`: 96 slots/dia;
- `weekly_rotation`: 16 slots/dia.

Existe fallback conhecido para garantir 112 publicações mesmo quando o subnicho originalmente planejado não possui candidato utilizável, em especial durante o problema conhecido de refresh.

Os motivos observáveis que devem continuar distinguindo regra normal de contingência são:

- seleção normal: `fixed_daily:<subnicho-ou-grupo>`;
- contingência fixa: `fixed_daily:redistributed`;
- contingência da rotação: `weekly_rotation:top_score_fallback`.

O realizado não deve ser usado como fonte da regra quando estiver contaminado por fallback. Para auditoria, `selection_reason` deve continuar permitindo separar intenção editorial de contingência.

## 4. Distribuição macro atual de referência

| Macro | Fixed | Rotação | Total | % dos 112 |
|---|---:|---:|---:|---:|
| Moda | 47 | 12 | 59 | 52,7% |
| Maquiagem | 17 | 3 | 20 | 17,9% |
| Cabelo | 12 | 0 | 12 | 10,7% |
| Skincare | 7 | 0 | 7 | 6,3% |
| Lingerie e íntimos | 5 | 0 | 5 | 4,5% |
| Unhas | 4 | 0 | 4 | 3,6% |
| Bolsas e carteiras | 2 | 0 | 2 | 1,8% |
| Acessórios femininos | 2 | 0 | 2 | 1,8% |
| Cuidados pessoais | 0 | 1 | 1 | 0,9% |
| **Total** | **96** | **16** | **112** | **100%** |

## 5. Nova camada editorial: `publication_group`

Não substituir os `subniches` atuais.

Adicionar uma camada de agrupamento usada somente para planejamento editorial:

```text
subniche -> publication_group
```

Requisitos:

- `subniche` continua sendo a taxonomia do catálogo;
- `publication_group` existe apenas para competir por slots editoriais;
- preferir configuração/mapeamento explícito em vez de alterar dados do catálogo;
- não exigir migração destrutiva do catálogo para esta entrega.

## 6. Novo agrupamento de Moda

| `publication_group` | Subnichos incluídos |
|---|---|
| `moda-tops` | `moda-partes-de-cima` |
| `moda-bottoms` | `moda-calcas`, `moda-saias-e-shorts` |
| `moda-looks` | `moda-vestidos`, `moda-conjuntos`, `moda-macacoes-e-macaquinhos` |
| `moda-fitness-praia` | `moda-fitness`, `moda-praia` |
| `moda-especial` | `moda-plus-size`, `moda-social-e-trabalho`, `moda-casual`, `moda-inverno`, `moda-ofertas-e-basicos`, `moda-geral` |

### 6.1 Subnichos excluídos da regra de Moda

| Subnicho | Nova regra |
|---|---|
| `moda-evangelica` | não participa da distribuição editorial deste perfil |
| `moda-festa` | não participa da distribuição editorial deste perfil |
| `moda-gestante` | não participa de Moda; reservado para grupo específico de gestante em trabalho futuro |

Esses itens não devem ser apagados do catálogo.

## 7. Nova distribuição `fixed_daily`

### 7.1 Moda

| Grupo | Fixed/dia |
|---|---:|
| `moda-tops` | 6 |
| `moda-bottoms` | 8 |
| `moda-looks` | 7 |
| `moda-fitness-praia` | 6 |
| `moda-especial` | 6 |
| **Total Moda fixed** | **33** |

Moda passa de 47 para 33 slots fixos, liberando 14 slots/dia.

### 7.2 Redistribuição dos 14 slots liberados

| Macro | Fixed atual | Alteração | Novo fixed |
|---|---:|---:|---:|
| Moda | 47 | -14 | **33** |
| Maquiagem | 17 | +5 | **22** |
| Cabelo | 12 | +3 | **15** |
| Skincare | 7 | +4 | **11** |
| Unhas | 4 | +1 | **5** |
| Cuidados pessoais | 0 | +1 | **1** |
| Lingerie e íntimos | 5 | 0 | **5** |
| Bolsas e carteiras | 2 | 0 | **2** |
| Acessórios femininos | 2 | 0 | **2** |
| **Total** | **96** | **0** | **96** |

### 7.3 Distribuição interna fixa

#### Maquiagem — 22

| Subnicho | Slots |
|---|---:|
| `maquiagem-pele` | 7 |
| `maquiagem-olhos` | 6 |
| `maquiagem-labios` | 5 |
| `maquiagem-pinceis-e-esponjas` | 2 |
| `maquiagem-organizacao` | 1 |
| `maquiagem-geral` | 1 |
| **Total** | **22** |

#### Cabelo — 15

| Subnicho | Slots |
|---|---:|
| `cabelo-tratamento` | 10 |
| `cabelo-ferramentas` | 5 |
| **Total** | **15** |

#### Demais fixos

| Subnicho | Slots |
|---|---:|
| `skincare-facial` | 11 |
| `unhas-manicure` | 5 |
| `cuidados-depilacao` | 1 |
| `lingerie-e-intimos` | 5 |
| `bolsas-e-carteiras` | 2 |
| `acessorios-femininos` | 2 |

## 8. Nova distribuição `weekly_rotation`

Manter 16 slots/dia.

| Macro | Slots de rotação |
|---|---:|
| Moda | 4 |
| Maquiagem | 4 |
| Cabelo | 2 |
| Skincare | 2 |
| Lingerie e íntimos | 1 |
| Unhas | 1 |
| Bolsas/Acessórios | 1 |
| Cuidados pessoais | 1 |
| **Total** | **16** |

Regras:

- os 4 slots de Moda devem competir entre os cinco novos `publication_group`;
- `moda-evangelica`, `moda-festa` e `moda-gestante` não podem entrar por rotação;
- a ordenação de candidatos continua sendo feita pelo `commercial_score` atual;
- a rotação não cria score novo nem bônus por grupo.

## 9. Resultado editorial esperado

| Macro | Fixed | Rotação | Total planejado | % |
|---|---:|---:|---:|---:|
| Moda | 33 | 4 | 37 | 33,0% |
| Maquiagem | 22 | 4 | 26 | 23,2% |
| Cabelo | 15 | 2 | 17 | 15,2% |
| Skincare | 11 | 2 | 13 | 11,6% |
| Lingerie e íntimos | 5 | 1 | 6 | 5,4% |
| Unhas | 5 | 1 | 6 | 5,4% |
| Bolsas/Acessórios | 4 | 1 | 5 | 4,5% |
| Cuidados pessoais | 1 | 1 | 2 | 1,8% |
| **Total** | **96** | **16** | **112** | **100%** |

## 10. Regra de seleção dentro de grupo agregado

Exemplo: `moda-bottoms` contém `moda-calcas` e `moda-saias-e-shorts`.

Para preencher seus 8 slots fixos:

1. obter candidatos pertencentes a qualquer subnicho mapeado para `moda-bottoms`;
2. aplicar os mesmos filtros de elegibilidade já existentes;
3. preservar o score `commercial_v1` existente;
4. ordenar pelo `commercial_score` existente;
5. aplicar deduplicação/limites existentes, sem criar peso novo por subnicho;
6. selecionar os melhores candidatos até preencher a quota.

Princípio:

> O agrupamento muda quem compete pelo slot; não muda como o candidato é pontuado.

## 11. Fallback

O fallback atual deve continuar funcional para impedir perda de publicação durante falhas de disponibilidade/refresh.

Nesta entrega, a prioridade é a redistribuição de quotas. Não reescrever o fallback se isso ampliar significativamente o escopo.

### 11.1 Comportamento mínimo obrigatório

- se faltarem candidatos, o plano continua buscando completar 112 slots;
- fallback deve permanecer explicitamente distinguível no `selection_reason`;
- não registrar um fallback como se fosse seleção normal do grupo planejado.

Exemplos esperados:

```text
fixed_daily:moda-bottoms
fixed_daily:redistributed
weekly_rotation:top_score_fallback
```

### 11.2 Melhoria opcional somente se já couber no mecanismo existente

Se a implementação atual permitir sem refatoração relevante, preferir fallback em camadas:

1. grupo planejado;
2. mesma macrofamília;
3. fallback global por maior `commercial_score`.

Se isso exigir mudança estrutural, não implementar nesta entrega; registrar como follow-up.

## 12. Implicações nos demais processos

### Catálogo e taxonomia

- sem migração destrutiva;
- manter `subniches` atuais;
- não reclassificar catálogo nesta entrega;
- `publication_group` é derivado para planejamento.

### Ranking comercial

- `commercial_v1` deve permanecer byte-for-byte equivalente em comportamento;
- nenhuma mudança em pesos, fórmulas ou thresholds;
- teste de regressão obrigatório.

### Refresh

- bug conhecido de refresh não faz parte desta entrega;
- implementação deve continuar funcionando quando o fallback for acionado por candidatos indisponíveis/`STALE`;
- não mascarar fallback no `selection_reason`.

### Plano diário

- é o principal componente impactado;
- deve continuar produzindo 112 registros/dia;
- deve preservar 96 `fixed_daily` + 16 `weekly_rotation`.

### Dispatcher / WhatsApp / n8n

- não devem conhecer a nova taxonomia editorial além do que já consomem do plano;
- nenhum contrato de publicação deve mudar;
- nenhuma mudança esperada em copy, mídia, horário ou envio.

### Métricas

- relatórios existentes por `primary_subniche` devem continuar válidos;
- se houver relatório da estratégia editorial, permitir agregação por `publication_group` sem substituir métricas antigas.

## 13. Testes obrigatórios

### T01 — mapping de Moda

Validar todos os mapeamentos e exclusões.

Obrigatório:

```text
moda-calcas -> moda-bottoms
moda-saias-e-shorts -> moda-bottoms
moda-partes-de-cima -> moda-tops
moda-evangelica -> EXCLUDED
moda-festa -> EXCLUDED
moda-gestante -> EXCLUDED_FROM_FEMININO_MODA
```

### T02 — quotas fixas com candidatos suficientes

Esperado:

```text
fixed_daily = 96
Moda = 33
Maquiagem = 22
Cabelo = 15
Skincare = 11
Lingerie = 5
Unhas = 5
Bolsas = 2
Acessórios = 2
Cuidados = 1
```

### T03 — total diário

Esperado invariável:

```text
fixed_daily = 96
weekly_rotation = 16
total = 112
```

### T04 — score intacto

Usar amostra estática de ofertas e comparar antes/depois.

Critério:

```text
commercial_score_before == commercial_score_after
```

para 100% da amostra.

### T05 — ordenação dentro de grupo

Exemplo:

```text
moda-calcas score 61
moda-saias-e-shorts score 73
moda-calcas score 68
```

Todos em `moda-bottoms`.

Esperado: 73, 68, 61.

Nenhum bônus ou penalidade pela origem do subnicho.

### T06 — grupo sem candidatos

Zerar candidatos de um grupo agregado.

Validar:

- o sistema continua tentando completar 112;
- slots de contingência ficam marcados como fallback/redistribuição;
- nenhum slot desaparece silenciosamente.

### T07 — cenário de refresh problemático

Simular indisponibilidade equivalente ao problema conhecido de refresh.

Validar:

- o plano continua completo quando houver candidatos de fallback suficientes;
- `selection_reason` separa claramente regra normal de contingência.

### T08 — nenhum falso sucesso

Um slot preenchido por fallback não pode sair como:

```text
fixed_daily:moda-bottoms
```

se o candidato veio da redistribuição.

Deve permanecer marcado como fallback/redistribuição.

### T09 — exclusões

Mesmo com scores altos, nenhum item exclusivamente classificado como:

- `moda-evangelica`;
- `moda-festa`;
- `moda-gestante`;

pode receber slot por esta regra de Moda.

### T10 — regressão do perfil fora de `feminino`

Executar testes para confirmar que `mae-e-bebe`, `auto-e-moto` e demais perfis não mudaram por efeito colateral.

## 14. Teste de integração — dia ideal

Gerar dry-run com candidatos suficientes para todos os grupos.

Critérios:

| Check | Esperado |
|---|---|
| total | 112 |
| fixed | 96 |
| rotation | 16 |
| Moda total planejada | 37 |
| Moda fixed | 33 |
| `moda-evangelica` | 0 |
| `moda-festa` | 0 |
| `moda-gestante` via Moda | 0 |
| score alterado | 0 itens |
| fallback no cenário ideal | 0 |

## 15. Teste comparativo antiga x nova regra

Com o mesmo conjunto estático de candidatos, executar as duas configurações.

Comparar:

- total de slots;
- distribuição por macro;
- score médio;
- score mediano;
- menor score selecionado;
- número de fallbacks;
- número de produtos únicos;
- comissão média/estimada quando disponível no mesmo dataset.

Esperado:

- regra antiga: Moda aproximadamente 59/112 na intenção editorial;
- regra nova: Moda 37/112 na intenção editorial;
- total permanece 112;
- `commercial_v1` não muda.

Registrar alerta, não necessariamente falha automática, se o score médio global cair mais de 2 pontos no dataset comparativo.

## 16. Shadow mode recomendado

Antes de ativar em produção, quando houver mecanismo seguro para isso, comparar:

```text
current_plan
new_plan_shadow
```

Sem publicar o plano shadow.

Comparar diariamente:

- score médio;
- comissão média/estimada;
- vendas médias;
- distribuição macro;
- quantidade de fallback;
- produtos repetidos;
- cobertura dos grupos;
- quantidade de candidatos por grupo.

O shadow mode é recomendação de validação e não deve ampliar esta implementação se o mecanismo ainda não existir.

## 17. Critérios de aceite

- [ ] produz exatamente 112 slots quando houver candidatos/fallback suficientes;
- [ ] mantém 96 `fixed_daily` + 16 `weekly_rotation`;
- [ ] Moda possui 33 slots fixos;
- [ ] Moda possui 4 slots planejados de rotação;
- [ ] `moda-evangelica` não recebe slot por esta regra;
- [ ] `moda-festa` não recebe slot por esta regra;
- [ ] `moda-gestante` não recebe slot via Moda;
- [ ] Maquiagem recebe 22 fixed;
- [ ] Cabelo recebe 15 fixed;
- [ ] Skincare recebe 11 fixed;
- [ ] Unhas recebe 5 fixed;
- [ ] Cuidados recebe 1 fixed;
- [ ] `commercial_v1` permanece idêntico;
- [ ] catálogo não sofre migração destrutiva;
- [ ] fallback continua garantindo preenchimento quando possível;
- [ ] fallback continua distinguível via `selection_reason`;
- [ ] dispatcher/copy/WhatsApp/n8n não mudam de contrato;
- [ ] outros perfis não sofrem regressão;
- [ ] `ruff` e `pytest` passam.

## 18. Arquivos/processos a inspecionar antes de alterar

O implementador deve localizar no estado atual do repositório onde vivem efetivamente:

- configuração das quotas de `fixed_daily`;
- configuração/regras de `weekly_rotation`;
- seleção por `primary_subniche`;
- produção de `selection_reason`;
- fallback `redistributed` / `top_score_fallback`;
- testes existentes do planner/selection;
- eventual persistência no Supabase ligada ao plano diário.

Não assumir nomes de módulos a partir desta spec. Primeiro localizar a implementação real e fazer a menor mudança possível.

## 19. Prompt para o Codex

Copie o bloco abaixo integralmente para o Codex.

```text
Implemente a spec `docs/projeto/08-spec-distribuicao-editorial-feminino.md` neste repositório.

Objetivo: alterar somente a composição editorial do plano diário do perfil `feminino`, reduzindo Moda e redistribuindo slots conforme a spec.

Regras obrigatórias de escopo:
1. Leia `AGENTS.md` e a spec inteira antes de editar.
2. Inspecione a implementação real antes de decidir quais arquivos mudar. Localize configuração/geração de `fixed_daily`, `weekly_rotation`, `selection_reason` e fallback.
3. Faça a menor alteração possível. Prefira configuração + mapper `subniche -> publication_group` + testes do planner/selection.
4. NÃO altere `commercial_v1`, pesos/fórmulas de score, catálogo, importação Shopee, canonicalização de produto, copywriter, dispatcher, horários, n8n ou WhatsApp.
5. NÃO tente corrigir o bug conhecido de refresh/STALE nesta tarefa.
6. Preserve 112 slots/dia, sendo 96 `fixed_daily` e 16 `weekly_rotation`.
7. Implemente os cinco grupos de Moda e quotas exatamente como especificado.
8. Exclua `moda-evangelica`, `moda-festa` e `moda-gestante` da distribuição de Moda sem apagar/reclassificar itens do catálogo.
9. Preserve fallback existente. `selection_reason` deve continuar distinguindo seleção normal de `fixed_daily:redistributed` e `weekly_rotation:top_score_fallback`.
10. Não implemente fallback hierárquico novo se isso exigir refatoração relevante; trate essa parte como follow-up.
11. Garanta que outros perfis não mudem.
12. Adicione/ajuste testes cobrindo T01–T10 e o teste de integração descritos na spec, reutilizando a estrutura de testes já existente sempre que possível.
13. Inclua teste de regressão explícito comprovando que `commercial_score` não muda para uma amostra estática antes/depois desta alteração.
14. Não crie CLIs auxiliares novos sem necessidade operacional clara.

Ao terminar:
- rode `python -m ruff check .`;
- rode `python -m pytest`;
- apresente um resumo dos arquivos alterados;
- explique onde a regra de quotas ficou configurada;
- mostre os resultados dos testes relevantes;
- destaque qualquer parte da spec que não pôde ser implementada sem ampliar escopo;
- não faça mudanças adicionais fora da spec para “melhorar” arquitetura.

Critério principal de sucesso em cenário ideal:
- total 112;
- fixed 96;
- rotation 16;
- Moda fixed 33;
- Moda rotation 4;
- Moda total planejado 37;
- Maquiagem fixed 22;
- Cabelo fixed 15;
- Skincare fixed 11;
- Unhas fixed 5;
- Cuidados fixed 1;
- evangelica/festa/gestante via Moda = 0;
- score comercial inalterado;
- fallback auditável por `selection_reason`;
- nenhuma regressão em outros perfis.
```
