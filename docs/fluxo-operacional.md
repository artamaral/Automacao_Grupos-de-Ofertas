# Fluxo operacional local

Este projeto deve ser operado por automação, agendador ou orquestrador. O objetivo é evitar execução manual de vários scripts pequenos.

## Comando principal

Use o orquestrador local:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage prepare --profile feminino
```

Fluxo recomendado para operação recorrente:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --profile feminino
```

Quando a rodada usar um catalogo curado local como entrada operacional do
`Collector`, o caminho recomendado passa a ser:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --profile feminino --catalog-file .\.data\catalogos\feminino.csv
```

O perfil deve ser mantido em [`config/discovery_profiles.toml`](../config/discovery_profiles.toml)
e está documentado em [`docs/discovery-profiles.md`](discovery-profiles.md).

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
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage finalize
```

Se o pacote foi instalado na venv, os atalhos equivalentes são:

```powershell
ofertas-local-flow --stage prepare --profile feminino
ofertas-local-flow --stage finalize
```

## Caminhos padrão

O fluxo usa `.data` por padrão:

```text
.data/offers.json
.data/copy_briefs.json
.data/messages.json
.data/messages.txt
.data/review_queue.json
.data/review_plan.json
.data/review_plan.txt
.data/approved_messages.json
.data/approved_messages.txt
.data/approved_messages_by_group/
.data/dispatch_artifact.json
.data/dispatch_report.json
.data/dispatch_report.txt
.data/publication_manifest.json
.data/local_review_bundle.json
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

A regra atual de pontuacao esta documentada em [`docs/scoring.md`](scoring.md).
Ela cobre apenas qualidade comercial basica da oferta; aderencia fina ao grupo,
subnicho e cupom continuam como camadas futuras de decisao.

O arquivo `.data/copy_briefs.json` deve ser tratado como a entrada operacional
do futuro copywriter com GPT. Ele deriva de `ScoredOffer` e contem apenas fatos
permitidos da oferta, `score`, motivos do score, disclosures obrigatorios,
restricoes de copy e alegacoes proibidas. O GPT deve redigir dentro desse
contrato, sem inventar preco, disponibilidade, prazo, beneficio ou urgencia.

Antes de gerar `.data/copy_briefs.json`, o fluxo deve passar por uma camada de
selecao operacional. O scorer pode rankear uma base ampla, mas o copywriter nao
deve receber todos os itens pontuados. Apenas itens aprovados pelo gate devem
virar brief de copy.

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
   todo item selecionado deve ter preco e comissao rechecados via API; se
   algum item mudar, a lista precisa ser reordenada e revalidada ate estabilizar.

Dentro de cada subnicho, a regra de corte deve ser:

- primeiro filtrar os itens elegiveis;
- depois ordenar os elegiveis por `score` desc;
- por fim aplicar a cota do subnicho.

Isso significa que item nao elegivel nao pode ocupar slot da cota, mesmo com
score maior que outro item elegivel do mesmo subnicho.

O config dessa camada nao deve ficar espalhado em flags soltas. A direcao
registrada e manter essas decisoes em um bloco de config proprio de selecao,
com itens como:

- `selection.cooldown_hours_default`
- `selection.band_allocation`
- `selection.similarity`
- `selection.refresh_before_copy`

Enquanto a implementacao nao existir, `copy_briefs.json` deve ser lido como
contrato alvo da etapa, nao como prova de que todas essas travas ja estao
ativas no codigo.

## Etapa finalize

A etapa `finalize`:

- aplica gate da fila;
- exporta somente aprovadas;
- separa aprovadas por grupo em artefatos prontos para operacao;
- cria manifesto local usando o destino roteado em cada item aprovado da fila;
- valida manifesto;
- gera artefato de disparo agrupado por destino, ainda sem envio real;
- executa o artefato em dry-run e salva relatório por destino;
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
