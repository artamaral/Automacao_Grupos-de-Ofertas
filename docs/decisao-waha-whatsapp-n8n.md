# Decisao de canal WhatsApp: WAHA no MVP n8n

Data da decisao: 2026-08-09.

## Decisao registrada

O adapter WhatsApp escolhido para uso agora no MVP e o WAHA, usando a imagem
publica `devlikeapro/waha` em ambiente self-hosted.

O envio real continua bloqueado ate passar por teste minimo controlado. O
workflow deve manter `dry_run=true` por padrao, validar allowlist antes de
qualquer tentativa real e registrar o resultado em
`offers.publication_events`.

Fluxo alvo:

```text
Supabase ranking
  -> n8n monta message_text
  -> n8n valida allowlist
  -> n8n chama WAHA
  -> n8n registra resultado no Supabase
```

## Por que nao usar a API oficial agora

A WhatsApp Business Cloud API oficial da Meta e o caminho mais estavel e
aderente a politicas, mas ela adiciona custo por conversa/mensagem e exige
onboarding operacional proprio. Para a fase atual, o objetivo e validar a
operacao minima com baixo custo, baixo volume e destino controlado.

Essa decisao nao elimina a possibilidade de migrar para API oficial depois. Ela
define apenas o adapter inicial para provar o MVP.

## O que e WAHA hoje

WAHA e uma API HTTP self-hosted para WhatsApp. Ela roda em Docker, conecta um
numero por QR Code ou pareamento e expoe endpoints HTTP, dashboard,
Swagger/OpenAPI, webhooks/websockets, sessoes, envio e recebimento de mensagens,
grupos, canais, presenca, labels e midia.

Ponto importante: "WAHA Plus" deixou de ser uma imagem separada. Desde a versao
`2026.6.1`, a documentacao oficial informa que os recursos antes associados ao
Plus passaram para o WAHA Core gratuito, incluindo sessoes ilimitadas, mensagens
multimidia, storages e seguranca embutida. A imagem recomendada passa a ser:

```text
devlikeapro/waha
```

Alguns videos e tutoriais ainda usam o nome "WAHA Plus", mas essa nomenclatura
esta desatualizada para instalacoes novas.

Fontes consultadas:

- https://waha.devlike.pro/docs/how-to/waha-plus/
- https://github.com/devlikeapro/waha/releases
- https://waha.devlike.pro/docs/
- https://dev.to/waha/whatsapp-automation-no-code-low-code-step-by-step-guide-waha-n8n-24h1

## Comparacao com Evolution API

| Criterio | WAHA | Evolution API |
| --- | --- | --- |
| Melhor uso agora | MVP simples de canal | Operacao maior de mensageria |
| Custo self-hosted | Gratuito, apoio opcional | Open source/self-hosted |
| Instalacao basica | Mais direta, container unico para o basico | Mais estruturada, com banco e Redis recomendados |
| Integracao n8n | HTTP Request ou community node `@devlikeapro/n8n-nodes-waha` | HTTP Request e ecossistema forte no Brasil |
| Engine WhatsApp nao oficial | WEBJS, WPP, GOWS, NOWEB | Baileys para WhatsApp Web |
| API oficial Meta | Nao e o foco do WAHA | Tambem suporta Cloud API oficial |
| Midia | Suporte incluido no Core atual | Suporte amplo, com storage local/S3/MinIO |
| Grupos | Suporta automacao de grupos | Suporta automacao via Baileys |
| Complexidade operacional | Menor para comecar | Maior, mas mais completa |
| Comunidade BR | Menor | Maior |
| Risco de bloqueio | Existe, por ser uso nao oficial do WhatsApp | Existe no modo Baileys |

Fontes Evolution:

- https://github.com/evolution-foundation/evolution-api
- https://docs.evolutionfoundation.com.br/evolution-api/installation

## Riscos reconhecidos

WAHA e Evolution, quando usados fora da Cloud API oficial, dependem de
mecanismos semelhantes ao WhatsApp Web. Isso torna o adapter barato, mas menos
estavel que a API oficial.

Riscos principais:

- a sessao pode cair e exigir novo QR Code ou pareamento;
- mudancas internas do WhatsApp Web podem quebrar engine, envio, midia ou
  webhooks ate sair atualizacao;
- grupos podem falhar por mudanca de ID, permissao, admin, bloqueio de envio ou
  remocao do numero;
- mensagens repetidas com link de afiliado podem aumentar risco de bloqueio,
  denuncia ou limitacao;
- o container precisa de persistencia correta para sessoes e midias;
- nao existe garantia contratual de estabilidade como na API oficial.

## Regras de uso no MVP

WAHA so deve entrar como adapter de canal, nao como fonte de verdade.

Regras obrigatorias:

- manter `dry_run=true` como padrao;
- enviar apenas para `target` presente em allowlist;
- iniciar com destino controlado, baixo volume e uma mensagem por rodada;
- nao expor painel, dashboard, Swagger ou API sem autenticacao e HTTPS;
- persistir sessoes em volume fora do container descartavel;
- nao commitar API key, QR Code, sessao, cookie, token ou `.env`;
- registrar em `offers.publication_events` o status retornado pelo adapter;
- nao marcar como `sent` quando o WAHA responder erro, timeout ou sessao fora de
  estado operacional;
- manter canal alternativo ou processo manual caso a sessao caia.

Status recomendados para o ledger:

```text
dry_run_not_sent
blocked_by_allowlist
adapter_ready
adapter_session_disconnected
adapter_send_failed
sent_to_adapter
```

`sent_to_adapter` significa apenas que o adapter aceitou a chamada. Nao deve ser
tratado como prova absoluta de leitura, clique ou entrega final.

## Criterios para reconsiderar Evolution

Reavaliar Evolution API se qualquer uma destas necessidades aparecer:

- multiplas instancias de WhatsApp virarem requisito imediato;
- integracao com Chatwoot, Typebot, Dify, OpenAI, RabbitMQ, Kafka, SQS ou S3
  passar a ser parte do caminho principal;
- for necessario padronizar mensageria para outros canais alem de WhatsApp;
- WAHA apresentar instabilidade recorrente no tipo de grupo ou midia usado pelo
  MVP;
- a operacao deixar de ser teste controlado e passar a exigir governanca de
  plataforma.

## Proximo passo operacional

Adicionar um bloco WAHA depois de `Validar Allowlist` no workflow do n8n, ainda
com `dry_run=true` por padrao. O primeiro teste real deve usar apenas
`target=teste-whatsapp` ou outro destino explicitamente allowlisted, baixo
volume e registro completo em `offers.publication_events`.

Commit sugerido:

```text
docs(n8n): define waha como adapter whatsapp
```
