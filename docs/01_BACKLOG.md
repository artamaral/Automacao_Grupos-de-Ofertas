# Backlog

Este arquivo registra ideias, melhorias, riscos, pendencias e evolucoes
possiveis do projeto.

Regras:

- backlog nao define execucao imediata;
- backlog pode registrar hipoteses ainda nao validadas;
- itens so devem virar implementacao quando forem puxados para a priorizacao
  operacional do projeto;
- itens concluidos podem permanecer aqui apenas como referencia historica curta,
  para evitar reabrir decisoes ja validadas;
- itens explicitamente fora do MVP atual nao devem ser tratados como bloqueio da
  operacao minima.

## Leitura atual do backlog

O projeto hoje tem duas frentes distintas:

- operacao minima ja validada em `Supabase -> n8n -> WAHA -> publication_events`;
- evolucoes de descoberta, refresh, taxonomia, roteamento e score semantico.

Por isso, este backlog foi reorganizado em quatro blocos:

- `Concluido`: o que ja tem implementacao ou validacao operacional relevante;
- `Fora do MVP atual`: o que continua valido, mas nao bloqueia a operacao minima;
- `Aberto prioritario`: o que falta fechar para endurecer o caminho principal;
- `Aberto exploratorio`: hipoteses, melhorias e pesquisa futura.

## Concluido

### MVP Supabase, n8n e WAHA

- Definido o caminho canonico do MVP: `Catalogo ativo no Supabase -> n8n
  consulta ranking -> n8n monta mensagem -> n8n envia para allowlist ->
  Supabase registra historico`.
- Workflow `ofertas-mvp-supabase` versionado e importavel em
  `n8n/workflows/ofertas-mvp-supabase.json`.
- Ajustado o workflow MVP do n8n para registrar `delivery_status=confirmed`
  somente depois de aceite do adapter WAHA.
- Atualizado o JSON versionado do workflow para substituir os nodes `Set` que
  importaram com output vazio no n8n 2.32.6 por nodes `Code` equivalentes,
  preservando os nomes `Set Contexto MVP` e `Simular Envio MVP`.
- Ajustado `sent_at` no workflow MVP para permanecer `null` quando
  `dry_run=true`.
- Validado o bloqueio de destino fora da allowlist antes do canal real.
- Validada a regra anti-repost para nao reenviar a mesma oferta ja confirmada
  ao mesmo `target` e `channel_adapter`.
- WAHA definido como adapter WhatsApp atual, com operacao self-hosted na VPS e
  uso apenas como canal de envio, nunca como fonte de verdade.
- Acoplado o envio real por imagem + legenda via `POST /api/sendImage`.
- Preparado o schedule automatico controlado do workflow, mantendo
  `active=false` como estado seguro padrao.
- Primeira execucao automatica da nova versao do schedule reportada pelo
  operador em 2026-08-11 as 17:00, encerrando a pendencia de validar o disparo
  automatico inicial do workflow em producao controlada.
- Monitoramento Hermes ajustado para detectar o caso de `success sem entrega`,
  usando `publication_events.confirmed` como prova operacional da rodada. Essa
  mudanca fecha a lacuna exposta pela execucao `78` de 2026-08-11.
- Freshness operacional da frente do ranking hoje esta coberta pelo desenho do
  refresh diario: 500 itens refreshados por dia, consumo atual abaixo de 50,
  plano de 135 mensagens por dia ainda com folga e selecao concentrada no topo
  do score, alem do cron do Hermes que verifica a execucao e o status do
  refresh.

### Fundacao de dados no Supabase

- Modelado e aplicado o schema operacional de catalogo, score e publicacao no
  Supabase.
- Criadas as tabelas `catalog_imports`, `catalog_items`,
  `offer_selection_state`, `publication_events`, `candidate_refresh_policies`,
  `offer_snapshots` e `offer_refresh_attempts`.
- Criadas as views `v_offer_ranking_current`, `v_offer_latest_snapshot`,
  `v_offer_refresh_status` e `v_offer_scoring_current`.
- Validada a importacao idempotente de catalogos locais para o Supabase.
- Validada a view de ranking e elegibilidade usada pelo n8n.
- Validada a idempotencia operacional de `publication_events`.
- Ajustado o timezone padrao do database para `America/Sao_Paulo`.
- Atualizado o catalogo ativo `feminino/shopee` em 2026-08-11 com relimpeza
  operacional e reativacao controlada.

### Refresh progressivo de candidatos

- Implantada a primeira versao do refresh progressivo orientado ao ranking para
  `profile=feminino`.
- Definido o uso de `productOfferV2(itemId)` como fonte de refresh comercial
  por snapshot, sem reescrever `catalog_items`.
- Implantados TTL, fila orientada ao ranking, snapshots historicos e auditoria
  de tentativas.
- Validado smoke real de refresh em 2026-08-11.
- Validado lote real com 500 chamadas, 490 snapshots e top 20 de `feminino`
  integralmente em `commercial_data_source=snapshot` e `refresh_status=FRESH`.

## Fora do MVP atual

Os itens abaixo continuam validos como evolucao, mas nao devem ser tratados
como bloqueio da operacao minima:

- implementar no Cloud Run geracao e disparo de mensagens sem incluir
  descoberta;
- manter Cloud Run como executor obrigatorio do fluxo diario;
- voltar a usar runner HTTP como caminho principal;
- usar Google Planilhas como fonte principal da rodada operacional;
- automatizar descoberta ampla como parte obrigatoria do runtime em nuvem;
- fazer revisao humana item a item antes de provar a operacao minima;
- endurecer toda a arquitetura final antes de estabilizar o MVP;
- mover perfis e grupos para banco/interface antes de consolidar as regras
  minimas atuais;
- avaliar aprovacao operacional via WhatsApp como interface de decisao humana;
- modelar camada de "produto equivalente / anuncios concorrentes" antes de
  consolidar a curadoria base.

## Aberto prioritario

### Operacao do MVP

- Endurecer TLS da credencial Postgres do Supabase no n8n, substituindo
  `Ignore SSL Issues (Insecure)` por validacao completa da cadeia via CA
  confiavel quando a UI/container permitir.
- Atualizar `offers.offer_selection_state` no fluxo MVP apos envio confirmado,
  registrando `selected_at`, `last_sent_at`, `cooldown_until` e
  `selection_count`, para evitar loop de reoferta do mesmo item elegivel.
- Endurecer a operacao da VPS apos a primeira subida do MVP: revisar firewall
  sem bloquear SSH ou servicos Hostinger, fixar e atualizar a versao do
  Traefik, configurar backup externo com teste de restore e remover a stack
  legada depois do periodo de estabilizacao.

### Shopee operacional

- Confirmar o escopo final da coleta ampla por macro-nicho na Shopee real, sem
  confundir discovery ampla com o refresh operacional por item.
- Definir estrategia de paginacao e volume por `profile` para discovery ampla.
- Definir regra de coleta incremental por nicho quando discovery voltar para a
  pauta operacional.
- Validar com mais evidencia quais campos reais da Shopee ajudam de fato na
  classificacao de subnicho.
- Confirmar como tratar respostas `no_node` e respostas vazias de
  `productOfferV2` em cenarios recorrentes, sem inferir indisponibilidade onde
  ela nao foi provada.

### Catalogo e qualidade semantica

- Refinar keywords e taxonomia de `auto-e-moto`, reduzindo concentracao em
  subnichos genericos e volume de `unmapped_source_keywords`.
- Revisar a qualidade semantica dos subnichos nos catalogos operacionais `4.8+`,
  porque preenchimento completo de `subniches` nao garante coerencia real.
- Levantar e corrigir falsos positivos semanticos nos tops por subnicho.
- Revisar a base de palavras-chave e a logica de classificacao usando como
  evidencia os artefatos `top10_por_subnicho.csv` e as analises mais recentes de
  feed/catalogo.
- Reduzir casos em que um item entra em subnicho tecnicamente preenchido, mas
  semanticamente fraco, ambiguo ou fora do contexto principal do nicho.

## Aberto exploratorio

### Descoberta, classificacao e roteamento

- Reaproveitar os codigos existentes de descoberta e classificacao semantica
  quando essa frente sair do backlog, simplificando o fluxo antes de amplia-lo.
- Manter local a camada de descoberta ampla por `profile`, sem depender de
  `subgroup` como entrada principal.
- Criar uma camada de classificacao que atribua `subgroup`, categorias,
  aderencia e sinais de contexto a cada oferta coletada.
- Criar uma camada de roteamento que decida para quais grupos uma oferta pode
  seguir.
- Permitir que uma mesma coleta ampla gere ofertas para multiplos grupos.
- Definir estrutura intermediaria para representar `offer + score +
  classification + routing`.
- Validar os `subgroups` atuais contra retorno real da Shopee antes de trata-los
  como contrato rigido.
- Medir quais queries amplas funcionam melhor por macro-nicho.
- Medir quais `subgroups` tem cobertura util e quais geram ruido demais.
- Adiar regra rigida de classificacao e roteamento ate haver dados reais
  suficientes para calibrar decisao com evidencia.

### Score e selecao

- Separar score de qualidade comercial do score de aderencia ao grupo.
- Criar score especifico para cupom versus score para produto.
- Adicionar explicacoes claras de por que a oferta foi roteada para cada grupo.
- Definir score minimo por grupo e por macro-nicho.
- Tratar conflito quando uma oferta servir para mais de um grupo.
- Adiar ponderacao fina de score comercial ate observar volume, qualidade e
  estrutura real das ofertas retornadas.

### Mensagens e manifestos

- Gerar mensagens a partir de uma lista de ofertas ja selecionadas, em vez de
  acoplar tudo ao harness.
- Diferenciar mensagem de produto, cupom e mensagem contextual/humanizada.
- Ajustar variacao de copy por grupo e por tipo de oferta.
- Definir quando vale mensagem unica por oferta e quando vale resumo por lote.
- Criar catalogo formal de grupos de destino e regras por grupo.
- Definir manifestos minimos para auditoria operacional sem excesso de artefato.
- Planejar evolucao do config para suportar perfis ativos/inativos e prioridade.
- Decidir quando perfis e grupos saem de arquivo versionado para banco/interface.

## Pontos em aberto sinteticos

Para consulta rapida, os principais pontos realmente em aberto hoje sao:

- endurecer TLS da conexao n8n -> Supabase;
- atualizar `offer_selection_state` apos envio confirmado no fluxo real;
- melhorar a qualidade semantica dos subnichos, especialmente em
  `auto-e-moto` e `feminino`;
- definir claramente o limite entre discovery ampla, refresh operacional e
  roteamento por grupo;
- separar score comercial de aderencia semantica;
- decidir quando cupons entram na mesma esteira dos produtos e quando precisam
  de regra propria.
