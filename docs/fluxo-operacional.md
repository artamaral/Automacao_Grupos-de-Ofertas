# Fluxo operacional local

Este projeto deve ser operado por automação, agendador ou orquestrador. O objetivo é evitar execução manual de vários scripts pequenos.

## Comando principal

Use o orquestrador local:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage prepare --profile feminino
```

Os comandos completos, flags de debug, entradas e saidas estao em
[`docs/cli-rodadas.md`](cli-rodadas.md).

O perfil deve ser mantido em [`config/discovery_profiles.toml`](../config/discovery_profiles.toml)
e está documentado em [`docs/discovery-profiles.md`](discovery-profiles.md).

## Horizontalizacao obrigatoria

`mae-e-bebe`, `feminino` e `auto-e-moto` compartilham o mesmo pipeline:

```text
Catalogo curado -> Collector -> Scorer -> Selecao -> Refresh -> Template -> Compliance -> Preview
```

Quando uma capacidade compartilhada avanca em um nicho, ela deve ser entregue
para todos os profiles operacionais no mesmo bloco. Nao devem existir versoes
do fluxo ou ramificacoes de codigo exclusivas por nicho.

As diferencas permitidas sao dados versionados:

- caminho do catalogo, destino e limite em `config/discovery_profiles.toml`;
- bandas por subnicho em `config/selection_profiles.toml`;
- roteamento em `config/group_profiles.toml`.

Todo profile operacional deve usar Shopee, catalogo curado, politica de 20
itens, no maximo 4 itens sem venda, template estatico Shopee, compliance e
preview automatico. Os testes devem falhar se um dos tres profiles perder esse
contrato.

Os grupos de destino devem ser mantidos em [`config/group_profiles.toml`](../config/group_profiles.toml)
e estão descritos em [`docs/group-profiles.md`](group-profiles.md).

Quando a meta for aprender com a saída da coleta, o caminho recomendado é salvar
também a inspeção estruturada:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --profile feminino --save-inspection-json .\tmp\feminino-inspection.json
```

Esse artefato deve ser usado para observar a saída real por `profile` antes de
endurecer classificação, roteamento e score.

Após a aprovação/rejeição da fila por um processo humano ou interface externa, finalize os artefatos locais:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage finalize --profile feminino
```

Se o pacote foi instalado na venv, os atalhos equivalentes são:

```powershell
ofertas-local-flow --stage prepare --profile feminino
ofertas-local-flow --stage finalize --profile feminino
```

## Caminhos padrão

O fluxo usa `.data/<profile>/` por padrão:

```text
.data/<profile>/offers.json
.data/<profile>/selection_state.json
.data/<profile>/copy_briefs.json
.data/<profile>/messages.json
.data/<profile>/messages.txt
.data/<profile>/messages_preview.html
.data/<profile>/review_queue.json
.data/<profile>/review_plan.json
.data/<profile>/review_plan.txt
.data/<profile>/approved_messages.json
.data/<profile>/approved_messages.txt
.data/<profile>/approved_messages_by_group/
.data/<profile>/dispatch_artifact.json
.data/<profile>/dispatch_report.json
.data/<profile>/dispatch_report.txt
.data/<profile>/publication_manifest.json
.data/<profile>/local_review_bundle.json
```

## Etapa prepare

A etapa `prepare`:

- carrega a base de ofertas em modo seguro;
- pontua ofertas;
- aplica gate de selecao antes do copy;
- rechecagem final de preco e comissao dos itens selecionados;
- salva `copy_briefs.json` como contrato estruturado entre scorer e copywriter;
- gera mensagens;
- valida compliance;
- salva artefatos locais;
- grava estado operacional em `selection_state.json`;
- renderiza automaticamente `messages_preview.html` com a previa visual da rodada;
- cria fila de revisão pendente já roteada pelo catálogo de grupos quando houver correspondência;
- gera `review_plan.json` e `review_plan.txt` com grupos elegíveis, bloqueios e mensagens previstas por grupo;
- não envia nada;
- não chama publicação real.

Regra operacional atual:

- a construcao ampla do catalogo de marketplace fica fora do fluxo principal;
- esse catalogo pode exigir revisao manual posterior, porque score, preco,
  comissao, frete e prazo podem mudar ao longo do tempo;
- por isso, o fluxo principal deve tratar o catalogo curado como entrada do
  `Collector`, e nao como etapa automatica recorrente dentro do `prepare`.
- o arquivo passado em `--catalog-file` pode ser `json` com `Offer`
  normalizada ou `csv` derivado do catalogo limpo da Shopee.

No caminho atual da Shopee, a copy recebe apenas a cadeia:

```text
clean_catalog_rating_4_8_plus.csv -> Collector -> .data/<profile>/offers.json -> Scorer -> Selecao -> selection_state.json -> copy_briefs.json -> messages.json/html
```

Regra de manutencao:

- se a lista de termos bloqueados mudar, o catalogo curado salvo em
  `catalogs/clean/<profile>/clean_catalog_rating_4_8_plus.csv` deve ser refeito
  ou re-limpo antes da proxima rodada;
- mesmo assim, o `Collector` deve reaplicar os filtros do `profile` ao carregar
  `catalog_file`, para impedir que um catalogo antigo siga para score e copy.

A regra atual de pontuacao esta documentada em [`docs/scoring.md`](scoring.md).
Ela cobre apenas qualidade comercial basica da oferta; aderencia fina ao grupo,
subnicho e cupom continuam como camadas futuras de decisao.

O arquivo `.data/<profile>/copy_briefs.json` e o contrato entre selecao e
geracao de mensagem. Ele deriva de `ScoredOffer` e contem apenas fatos
permitidos da oferta, `score`, motivos do score, disclosures obrigatorios,
restricoes de copy e alegacoes proibidas. Na Shopee, esses dados alimentam
diretamente o template estatico; nao ha assistente ou GPT na geracao do texto.

Decisao operacional atual para Shopee:

- a mensagem base pode ser gerada por template estatico;
- esse template deve ser preenchido diretamente com os campos estruturados do
  brief, sem apoio de assistente;
- o template oficial atual da Shopee fica em
  [`config/message_templates/shopee.txt`](../config/message_templates/shopee.txt);
- o mesmo template atende todos os nichos operacionais, sem override por nicho;
- a URL global de cupom fica em
  [`config/coupon_urls.toml`](../config/coupon_urls.toml);
- o preview visual validado desta etapa fica em
  [`tmp/mae-e-bebe-message-preview.html`](../tmp/mae-e-bebe-message-preview.html).

Regra complementar desta etapa:

- o preview HTML da rodada deixa de ser um mock manual e passa a ser artefato
  automatico do `prepare`/harness quando o caminho de saida for informado;
- o preview deve refletir apenas as mensagens aprovadas pelo compliance;
- no template estatico atual da Shopee, `(anúncio)` cumpre o disclosure exigido
  pelo compliance.

Antes de gerar `.data/<profile>/copy_briefs.json`, o fluxo deve passar por uma camada de
selecao operacional. O scorer pode rankear uma base ampla, mas o copywriter nao
deve receber todos os itens pontuados. Apenas itens aprovados pelo gate devem
virar brief de copy.

Regra de comportamento padrao do harness:

- se existir politica default registrada para o nicho e nenhum parametro extra
  sobrescrever a selecao, essa politica deve ser aplicada automaticamente;
- o harness nao deve inventar filtros paralelos fora do contrato documentado;
- na ausencia de parametro especifico, a saida padrao para copy deve ser sempre
  a selecao deterministica definida para o nicho.
- nas rodadas padrao dos tres profiles operacionais, itens sem venda podem
  entrar, mas nunca ultrapassar `4` itens no total.

### Gate de selecao

O gate entre `Scorer` e `Copywriter` deve aplicar quatro blocos de regra:

1. recorrencia temporal:
   toda oferta selecionada grava `selected_at` e entra em `cooldown`; depois de
   estourar a janela configurada, ela volta a ser elegivel;
2. banda por nicho e subnicho:
   a rodada deve respeitar percentuais configurados por nicho/subnicho, com
   base em histograma de vendas e nao em divisao uniforme;
3. similaridade e diversidade:
   itens muito parecidos devem disputar entre si antes do copy, para evitar
   repeticao excessiva de descricao e vendedor;
4. refresh final:
   os itens selecionados da rodada devem ter preco e comissao rechecados via
   API usando `itemId`; nesta etapa o refresh olha apenas `price` e
   `commissionRate`; se algum item mudar, a lista inteira precisa ser
   rescored, reselecionada e revalidada ate estabilizar.

Dentro de cada subnicho, a regra de corte deve ser:

- primeiro filtrar os itens elegiveis;
- depois ordenar os elegiveis por `score` desc;
- por fim aplicar a cota do subnicho.

Isso significa que item nao elegivel nao pode ocupar slot da cota, mesmo com
score maior que outro item elegivel do mesmo subnicho.

O config implementado dessa camada fica centralizado em
[`config/selection_profiles.toml`](../config/selection_profiles.toml), incluindo:

- total de itens por rodada;
- minimo de execucoes diarias;
- `cooldown_hours_default`;
- teto de itens sem venda;
- percentual e quantidade por subnicho;
- caminho da evidencia usada na decisao.

No estado atual de implementacao, esse refresh operacional fica ativo no
harness da Shopee quando `ENABLE_REAL_HTTP=true`.

No estado atual, o cooldown operacional ja grava:

- `selected_at`: instante em que a oferta entrou na rodada;
- `cooldown_until`: instante ate o qual a oferta fica inelegivel;
- `last_sent_at`: instante em que a oferta entrou no artefato final de dispatch da rodada.
- `selection_count`: quantas vezes a oferta ja entrou em rodada selecionada;

Esses campos ficam persistidos em `.data/<profile>/selection_state.json` e
tambem aparecem nas ofertas serializadas quando disponiveis.

Similaridade continua como evolucao separada. A selecao por banda, o cooldown e
o refresh de preco/comissao ja fazem parte do fluxo compartilhado.

## Etapa finalize

A etapa `finalize`:

- aplica gate da fila;
- exporta somente aprovadas;
- separa aprovadas por grupo em artefatos prontos para operacao;
- cria manifesto local usando o destino roteado em cada item aprovado da fila;
- valida manifesto;
- gera artefato de disparo agrupado por destino, ainda sem envio real;
- executa o artefato em dry-run e salva relatório por destino;
- atualiza `last_sent_at` das ofertas que entraram no artefato de dispatch;
- cria bundle local de auditoria;
- executa doctor local;
- para na primeira falha;
- não envia nada;
- não chama publicação real.

Dentro de `.data/approved_messages_by_group/`, cada grupo gera um par de arquivos
`<group-slug>.json` e `<group-slug>.txt`, mantendo o destino da revisão já pronto
para uso posterior no disparo.

O arquivo `.data/dispatch_artifact.json` consolida as mensagens prontas por
`target`, junto com o `adapter_kind` configurado por grupo, servindo como contrato de entrada para um futuro disparador local ou
automatizado.

O arquivo `.data/dispatch_report.json` registra a simulação da rodada de
disparo, por destino e por mensagem, sem qualquer envio real.

O arquivo `.data/dispatch_report.txt` resume a rodada em formato legível para
operação e auditoria rápida, incluindo `planned_at` por mensagem em
`America/Sao_Paulo`.

No estado atual, o executor de disparo trabalha com adaptadores `dry-run` de
canal. O adaptador de cada destino passa a ser definido no catálogo de grupos,
e os adaptadores `whatsapp`, `telegram` e `console` permanecem disponíveis para
simulação e testes.

Cada destino também pode declarar no config:

- quantas mensagens entram em cada rodada;
- o intervalo fixo planejado entre mensagens do mesmo destino.

Essa cadência é operacional e auditável. O fluxo não usa intervalo aleatório
para tentar parecer humano.

Cadencia operacional registrada para a rodada atual:

- `20` mensagens por execucao;
- minimo de `5` execucoes por dia;
- alvo operacional de `100` mensagens por dia.

## Papel humano

O humano não deve operar vários CLIs manualmente no fluxo principal.

O humano participa apenas para:

- aprovar ou rejeitar mensagens;
- configurar credenciais;
- liberar travas de segurança quando for apropriado;
- validar localmente quando solicitado.

## Ferramentas auxiliares

Os CLIs menores existentes permanecem úteis para debug, auditoria e manutenção, mas não devem ser o caminho operacional principal.

Exemplos:

```text
ofertas-review-list
ofertas-review-decide
ofertas-review-export
ofertas-review-gate
ofertas-manifest-validate
ofertas-local-doctor
```

Na revisão humana, o item deve ser avaliado já com o contexto de `group`, `destination_ref`
e tom configurado no catálogo operacional, para reduzir decisão solta fora da configuração.

## Validação de desenvolvimento

Após mudanças no código:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

No Windows PowerShell, se a saída do fluxo falhar por encoding ao imprimir
textos acentuados ou símbolos da mensagem, habilite UTF-8 antes de rodar o
comando:

```powershell
$env:PYTHONUTF8='1'
```

## Timezone operacional

O horario oficial do sistema deve ser tratado como `GMT-3`, usando
`America/Sao_Paulo` como timezone de referencia para artefatos, janelas de
silencio e auditoria local.

No dispatch:

- `generated_at` deve sair em `America/Sao_Paulo`;
- `quiet_periods` devem ser avaliados em `America/Sao_Paulo`;
- o relatorio deve mostrar quantas mensagens estavam disponiveis, quantas foram
  selecionadas, quantas ficaram de fora e se houve bloqueio por quiet period ou
  corte por limite operacional.
