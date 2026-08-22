# Spec — Reestruturação do `ofertas-instagram-supabase`: Reels + Carrossel

## Status

Spec aprovada para implementação.

Escopo deliberadamente restrito ao workflow Instagram. Não criar regras adicionais para horário, ranking, copy, schedule, modelo de status ou arquitetura de claim sem evidência concreta no código e sem que isso seja necessário para cumprir esta spec.

## 1. Objetivo

Reestruturar o workflow `ofertas-instagram-supabase` para trabalhar com dois caminhos de publicação:

- Reels;
- Carrossel.

O workflow continua sendo um único workflow n8n.

O comportamento funcional já validado do Reels deve ser usado como referência. Reels e Carrossel devem seguir as mesmas regras gerais existentes e divergir somente nas etapas específicas necessárias para criação e publicação de cada formato.

## 2. Meta diária

A meta é:

```text
3 Reels
3 Carrosséis
```

Total:

```text
6 publicações confirmadas por dia
```

Para controle dessa meta, considerar somente publicações Instagram com:

```text
delivery_status = confirmed
```

Falhas e execuções canceladas não contam como publicação realizada.

## 3. Alternância entre formatos

A sequência desejada é:

```text
Reels
Carrossel
Reels
Carrossel
Reels
Carrossel
```

O próximo formato deve ser determinado pelas publicações Instagram já confirmadas no dia.

| Reels confirmados | Carrosséis confirmados | Próximo |
|---:|---:|---|
| 0 | 0 | Reels |
| 1 | 0 | Carrossel |
| 1 | 1 | Reels |
| 2 | 1 | Carrossel |
| 2 | 2 | Reels |
| 3 | 2 | Carrossel |
| 3 | 3 | Encerrar |

Não é necessário manter uma flag física se o mesmo estado puder ser determinado de forma segura pelas publicações confirmadas do dia.

## 4. Não utilizar fallback de formato

Se o próximo formato esperado for Carrossel e não houver candidato que satisfaça as regras de Carrossel, não publicar Reels como substituição.

O próximo formato continua sendo Carrossel.

Da mesma forma, se o próximo esperado for Reels e não existir candidato válido para Reels, não substituir automaticamente por Carrossel.

Objetivo: evitar disparidade entre a quantidade de Reels e Carrosséis.

## 5. Universo de seleção

Os candidatos para publicação Instagram devem pertencer ao `offers.daily_dispatch_plan` do dia corrente.

A regra deve ser:

```sql
planned_date =
(now() at time zone 'America/Sao_Paulo')::date
```

Remover o comportamento atual que permite:

```sql
planned_date <= hoje
```

Itens de dias anteriores não podem ser utilizados para preencher a publicação Instagram do dia atual. Itens de dias futuros também não podem ser utilizados.

**Não adicionar restrição por `planned_hour` nesta alteração.**

## 6. `dispatch_status` não define elegibilidade Instagram

Remover da seleção Instagram a condição:

```sql
dispatch_status = 'planned'
```

O fato de o item ter sido processado por outro canal não deve, por si só, removê-lo do universo de seleção do Instagram.

Para o Instagram, o `daily_dispatch_plan` é utilizado para determinar os itens pertencentes ao plano do dia.

Não alterar a regra do WhatsApp como parte desta implementação.

## 7. Não redefinir o modelo de status nesta spec

A retirada de `dispatch_status = 'planned'` da elegibilidade Instagram não autoriza esta implementação a criar automaticamente:

- nova tabela de claim;
- novo status;
- novo campo de controle;
- alteração do modelo de `daily_dispatch_plan`;
- alteração do trigger de `publication_events`.

Caso seja identificado algum problema de concorrência, claim ou sincronização de status durante a implementação, primeiro demonstrar o problema com o código/query existente e reportá-lo separadamente. Não introduzir uma nova arquitetura de estado como solução implícita desta spec.

## 8. Origem de `instagram_format`

O formato disponível continua sendo determinado pelas mídias do item.

Fonte:

```text
offers.offer_media_assets
```

por meio da lógica utilizada por:

```text
offers.v_instagram_dispatch_ready
```

Os formatos possíveis são:

```text
reels
carousel
```

O Roteador Formato não decide comercialmente qual formato será usado. O formato esperado deve ser determinado antes da seleção do candidato.

## 9. Elegibilidade para Reels

Um item pode ser candidato a:

```text
instagram_format = reels
```

quando possuir os dados de vídeo exigidos pelo fluxo atual de Reels.

Preservar as validações atualmente utilizadas pelo Reels funcional.

Não introduzir novas regras de vídeo nesta alteração.

## 10. Elegibilidade para Carrossel

Alterar a regra de Carrossel.

O item somente pode ser candidato a Carrossel quando possuir quatro ou mais imagens.

A regra atual equivalente a:

```sql
jsonb_array_length(image_urls) > 0
```

deve passar a exigir:

```sql
jsonb_array_length(image_urls) >= 4
```

O limite máximo já utilizado pelo fluxo atual de Carrossel permanece em 10 imagens.

Portanto:

```text
4 a 10 imagens
```

## 11. Validação do Carrossel

O pipeline deve utilizar as validações de mídia necessárias à publicação.

Depois dessas validações, o Carrossel somente pode continuar se ainda existirem pelo menos quatro imagens utilizáveis.

Se restarem menos de quatro:

```text
não publicar
```

Não fazer fallback automático para Reels.

## 12. Determinação do próximo formato

Antes de selecionar o produto, determinar:

```text
next_instagram_format
```

com base nas publicações Instagram confirmadas do dia.

Exemplo:

```text
Reels confirmados = 1
Carrosséis confirmados = 0
```

Resultado:

```text
next_instagram_format = carousel
```

A seleção deve então procurar exclusivamente candidato com:

```text
instagram_format = carousel
```

## 13. Preservar deterministicamente `instagram_format`

O mesmo item pode possuir `video_url` e `image_urls` e, portanto, ser tecnicamente elegível para os dois formatos.

A seleção não pode perder o formato escolhido.

O candidato deve preservar conjuntamente:

```text
dispatch_plan_id
instagram_format
```

durante a seleção e o restante da execução.

Se foi selecionado:

```text
dispatch_plan_id = X
instagram_format = carousel
```

a execução deve continuar como Carrossel.

Não recuperar posteriormente o mesmo `dispatch_plan_id` sem preservar o formato escolhido.

## 14. Roteador Formato

O roteador recebe `instagram_format` já decidido.

Seu comportamento é somente:

```text
instagram_format = reels
→ fluxo Reels

instagram_format = carousel
→ fluxo Carrossel
```

Ele não deve decidir o formato olhando novamente:

- `video_url`;
- `image_urls`;
- quantidade diária;
- prioridade entre formatos.

## 15. Estrutura do workflow

Parte comum:

```text
Trigger
↓
Contexto Instagram
↓
Validação
↓
Determinar próximo formato
↓
Selecionar candidato do plano de hoje
↓
Montar Copy
↓
Dry Run
↓
Roteador Formato
```

Depois:

```text
                  ┌─ Reels
Roteador Formato ─┤
                  └─ Carrossel
```

## 16. Pipeline Reels

O pipeline Reels existente e já validado deve ser preservado como referência funcional.

Fluxo conceitual:

```text
Revalidar mídia Reels
↓
Criar Container Reels
↓
Verificar processamento
↓
Polling / Wait conforme regra atual
↓
Publicar
↓
Registrar resultado
```

Não alterar as regras já funcionais do Reels sem necessidade diretamente relacionada a esta spec.

## 17. Pipeline Carrossel

O pipeline Carrossel deve seguir as mesmas regras gerais do fluxo Reels, divergindo onde o formato exige tratamento próprio.

Fluxo conceitual:

```text
Validar imagens
↓
garantir pelo menos 4 imagens
↓
Criar Containers Filhos
↓
Criar Container Pai
↓
Verificar processamento
↓
Polling / Wait conforme regra equivalente ao Reels
↓
Publicar
↓
Registrar resultado
```

A criação específica continua utilizando containers filhos e container pai `CAROUSEL`.

## 18. Independência entre os dois caminhos

Depois do roteador, a lógica específica de Reels não deve interferir no Carrossel e vice-versa.

O Reels já funcional deve permanecer protegido de mudanças necessárias exclusivamente ao Carrossel.

A implementação do Carrossel deve reutilizar as regras gerais já validadas no Reels sempre que forem aplicáveis, mas os dois caminhos devem permanecer independentes após o roteamento nas etapas específicas de mídia, container, polling, publicação e registro.

## 19. Dry Run

Preservar o comportamento atual de dry-run.

Dry-run não publica no Instagram e não deve ser contado como publicação confirmada para a sequência Reels → Carrossel.

Não criar novas regras de dry-run nesta alteração.

## 20. Fora de escopo

Não faz parte desta spec:

- alterar ranking;
- alterar taxonomia;
- alterar critérios comerciais do plano diário;
- alterar a distribuição horária dos itens;
- introduzir restrição por `planned_hour`;
- redesenhar `daily_dispatch_plan`;
- criar nova tabela de controle sem análise específica;
- alterar fluxo do WhatsApp;
- alterar copy;
- alterar credenciais;
- alterar conta Instagram;
- alterar API version;
- redefinir schedule;
- definir quantidade de execuções do Schedule;
- alterar outras regras não necessárias ao desmembramento Reels/Carrossel.

## 21. Alterações objetivas

A implementação deve realizar somente as seguintes mudanças de regra.

### Seleção diária

De:

```text
planned_date <= hoje
```

Para:

```text
planned_date = hoje
```

### Status do plano

Remover da elegibilidade Instagram:

```text
dispatch_status = planned
```

### Carrossel

De:

```text
1 ou mais imagens
```

Para:

```text
4 ou mais imagens
```

### Distribuição

Implementar meta:

```text
3 Reels
3 Carrosséis
```

### Alternância

Implementar:

```text
Reels → Carrossel → Reels → Carrossel → Reels → Carrossel
```

avançando com base em publicações confirmadas.

### Formato esperado indisponível

```text
não usar outro formato como fallback
```

### Formato selecionado

Preservar deterministicamente:

```text
dispatch_plan_id + instagram_format
```

durante a execução.

### Estrutura

Preservar Reels funcional e separar o processamento específico de Reels e Carrossel dentro do mesmo workflow.

## 22. Critérios de aceite

A implementação estará correta quando:

- [ ] candidatos Instagram pertencerem exclusivamente ao `daily_dispatch_plan` de hoje;
- [ ] itens de dias anteriores não forem usados;
- [ ] não existir restrição nova por `planned_hour`;
- [ ] elegibilidade Instagram não exigir `dispatch_status = planned`;
- [ ] Carrossel exigir no mínimo 4 imagens;
- [ ] Carrossel continuar limitado ao máximo de 10 imagens;
- [ ] Reels continuar com o comportamento funcional atual;
- [ ] formato esperado for calculado antes da seleção;
- [ ] formato selecionado for preservado durante a execução;
- [ ] roteador apenas encaminhar Reels ou Carrossel;
- [ ] meta diária for 3 Reels + 3 Carrosséis;
- [ ] somente publicação confirmada contar para a alternância;
- [ ] ausência do formato esperado não utilizar o outro como fallback;
- [ ] mudança específica do Carrossel não alterar o comportamento funcional do Reels;
- [ ] nenhuma regra adicional de horário, ranking, copy, schedule ou seleção comercial for introduzida.

---

# Prompt para Codex implementar esta spec

Implemente a spec deste documento no repositório `artamaral/Automacao_Grupos-de-Ofertas`, trabalhando na branch `feat/supabase-cloud-run`.

O workflow alvo versionado é:

```text
n8n/workflows/ofertas-instagram-supabase.json
```

Leia antes de alterar:

```text
AGENTS.md
docs/commit-pattern.md
docs/spec-instagram-reels-carousel.md
n8n/workflows/ofertas-instagram-supabase.json
```

Inspecione também migrations, views, testes e documentação diretamente relacionados às queries utilizadas pelo workflow antes de modificar SQL ou Supabase.

## Regra principal de execução

Implemente **somente** o que está definido nesta spec.

Não complete lacunas com novas regras de negócio ou arquitetura por inferência.

Em particular, não introduza por conta própria:

- filtro por `planned_hour`;
- mudança de ranking ou ordem comercial dos produtos;
- alteração da copy;
- mudança de schedule ou quantidade de execuções diárias;
- nova tabela de claim;
- novo status ou novo modelo de estado;
- alteração do fluxo WhatsApp;
- alteração de credenciais, conta Instagram ou versão da Graph API;
- fallback Reels ↔ Carrossel.

Se durante a implementação encontrar uma dependência que torne alguma parte da spec insegura ou impossível sem uma mudança fora de escopo, **não invente a solução**. Documente a evidência concreta — arquivo, node, SQL, trigger ou constraint envolvida — e deixe essa mudança fora do patch até decisão explícita.

## Mudanças obrigatórias

1. Restringir a seleção Instagram a `planned_date = hoje` em `America/Sao_Paulo`; não usar `<= hoje`.
2. Remover `dispatch_status = 'planned'` como requisito de elegibilidade Instagram.
3. Não adicionar filtro por `planned_hour`.
4. Alterar a elegibilidade de Carrossel para no mínimo 4 imagens e máximo de 10 conforme o fluxo atual.
5. Determinar `next_instagram_format` antes da seleção usando somente publicações Instagram `confirmed` do dia.
6. Implementar a sequência alvo `Reels → Carrossel → Reels → Carrossel → Reels → Carrossel`, com meta máxima de 3 confirmados por formato.
7. Não avançar a alternância por `failed`, `cancelled` ou dry-run.
8. Se não existir candidato para o formato esperado, não usar o outro formato como fallback.
9. Fazer a seleção filtrar pelo `next_instagram_format`.
10. Preservar deterministicamente `dispatch_plan_id + instagram_format` para impedir que um item elegível aos dois formatos troque de formato depois da seleção.
11. Manter o workflow único e separar, após o roteador, os caminhos específicos de Reels e Carrossel.
12. Preservar o caminho Reels funcional como baseline. Não refatorar comportamento Reels que não seja necessário para cumprir esta spec.
13. No caminho Carrossel, após validação das imagens, prosseguir somente se restarem pelo menos 4 imagens utilizáveis; não fazer fallback para Reels.
14. Manter independentes, após o roteador, as etapas específicas de validação de mídia, criação de container, polling/wait, publicação e registro de Reels e Carrossel.
15. Preservar o comportamento atual de dry-run, sem contabilizá-lo como `confirmed`.

## Cuidado com `dispatch_status`

A spec aprova apenas remover `dispatch_status = 'planned'` da **elegibilidade Instagram**.

Não use essa mudança como autorização para redesenhar o modelo de status, triggers, claims ou `daily_dispatch_plan`.

Se o código existente escrever em `dispatch_status` ou houver trigger de `publication_events` que gere efeito colateral relevante para o Instagram/WhatsApp, apresente a evidência no relatório final. Só altere esse comportamento se a alteração for estritamente necessária para implementar uma regra explicitamente definida nesta spec e puder ser feita sem introduzir nova arquitetura de estado.

## Validação obrigatória

Antes de concluir:

- validar que o JSON do workflow continua válido e importável;
- executar testes existentes diretamente relacionados às mudanças;
- adicionar ou atualizar testes determinísticos quando houver infraestrutura de teste existente para a regra modificada;
- conferir que não foi introduzido `planned_hour` na seleção Instagram;
- conferir que `dispatch_status = 'planned'` não permanece como condição de elegibilidade Instagram;
- conferir que Carrossel exige `>= 4` imagens;
- conferir que o formato esperado é determinado antes da seleção;
- conferir que `dispatch_plan_id + instagram_format` não perde o formato selecionado;
- conferir que não existe fallback de formato;
- conferir que Reels permanece funcionalmente equivalente no que não faz parte da mudança.

Não faça chamadas reais à Instagram Graph API durante testes automatizados.

## Entrega esperada

Ao terminar, apresente:

1. arquivos alterados;
2. resumo objetivo das mudanças;
3. testes executados e resultados;
4. evidência de cada critério de aceite relevante;
5. qualquer dependência ou risco encontrado que tenha sido deixado fora do patch por estar fora do escopo;
6. diff final revisado para confirmar que nenhuma regra não solicitada foi introduzida.

Não faça mudanças adicionais apenas por considerar que seriam melhorias.