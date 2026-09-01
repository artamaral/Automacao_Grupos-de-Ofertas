# Spec de Implementação — Automação de Comentários e DMs do Instagram via n8n

> **Legado em 2026-09-01.** Esta especificacao nao deve orientar novos deploys
> ou reativacoes. O historico, os artefatos preservados e o estado final estao
> em `docs/legacy/instagram-comentarios-dm-n8n-2026-09-01.md`.

## 1. Objetivo

Implementar, no n8n, uma automação independente dos fluxos atuais de publicação para tratar:

1. comentários recebidos em publicações do Instagram;
2. DMs recebidas no Instagram.

O fluxo deve operar sem Agent, sem LLM, sem buffer de mensagens e sem token refresher próprio.

A automação deve reutilizar apenas os dados já disponíveis e necessários para identificar publicação, produto e copy publicada, registrar todas as interações no Supabase e carregar todas as copies/configurações editoriais a partir do Google Drive.

---

## 2. Princípios obrigatórios

- Não alterar a lógica dos workflows atuais de publicação.
- Novo fluxo desacoplado dos fluxos atuais.
- Não usar Agent, LLM ou fuzzy matching.
- Não usar buffer de mensagens.
- Não implementar token refresher.
- Reutilizar a autenticação/credenciais já adotadas no fluxo atual de publicação do Instagram.
- Não hardcodar copies no n8n.
- Registrar comentários e DMs em estruturas novas e separadas no Supabase.
- Não reutilizar `offers.publication_events` como tabela de log de interação.
- `offers.publication_events` deve ser usada apenas como fonte para resolver publicação → produto/copy.
- Qualquer falha deve ser registrada e o processamento deve parar; não improvisar fallback.
- Retenção permanente dos registros no banco, sem TTL ou purge nesta fase.
- A automação deve funcionar para qualquer publicação do Instagram que possua `published_media_id` registrado, sem restringir a Reels.

---

## 3. Fontes de dados existentes

### 3.1 Supabase — publicação existente

Usar `offers.publication_events` para resolver o comentário recebido para a publicação/produto correspondente.

Campos já disponíveis e relevantes:

- `publish_id`
- `profile`
- `marketplace`
- `item_id`
- `offer_url`
- `message_text`
- `payload.published_media_id`
- `channel_adapter`
- `delivery_status`
- `sent_at`

Regra de lookup:

```text
Instagram media_id
    ↓
offers.publication_events.payload.published_media_id
    ↓
publish_id + item_id + offer_url + message_text
```

Não consultar `daily_dispatch_plan`, score, taxonomia, `offer_media_assets` ou outras tabelas se esses dados não forem necessários ao tratamento da interação.

### 3.2 Google Drive — configuração editorial

Pasta canônica:

`https://drive.google.com/drive/folders/1om8GcfC4s4UMBU9t7ujmxXawdoYIWUQy?usp=drive_link`

Arquivos obrigatórios:

1. `instagram_comment_dm_intro.txt`
   - primeira parte da DM enviada após comentário reconhecido;
   - deve ser concatenada antes de `publication_events.message_text`.

2. `instagram_comment_public_reply.txt`
   - resposta pública automática ao comentário.

3. `instagram_dm_default_reply.txt`
   - resposta padrão para DM espontânea;
   - deve conter o direcionamento definido operacionalmente para o site `https://mktdigitalofertas.com.br` e grupo WhatsApp.

4. `instagram_comment_keywords.txt`
   - lista de keywords, variações e typos aceitos;
   - uma entrada por linha;
   - ignorar linhas vazias e comentários iniciados por `#`.

Nenhuma dessas copies deve ficar hardcoded no workflow.

---

## 4. Matching de comentários

O matching será `CONTAINS`, sem IA e sem fuzzy matching.

Antes de comparar o comentário e as entradas do arquivo de keywords, normalizar ambos:

1. converter para lowercase;
2. remover acentos;
3. substituir caracteres especiais/pontuação por espaço;
4. colapsar espaços repetidos;
5. aplicar trim.

Depois da normalização:

```text
normalized_comment CONTAINS normalized_keyword
```

Se qualquer keyword configurada corresponder, o comentário é considerado acionável.

A lista inicial deve ser conservadora para evitar falsos positivos e deve incluir variações e typos comuns de `quero`.

Não usar abreviações excessivamente amplas como `qr` ou termos genéricos demais.

---

## 5. Fluxo de comentário

### 5.1 Entrada

Receber webhook do Instagram/Meta e extrair somente os campos necessários ao processamento e registro, incluindo quando disponíveis:

- identificador do evento;
- `comment_id`;
- `media_id`;
- `from_id` / identificador do usuário;
- `username`;
- texto do comentário;
- timestamp do evento;
- tipo/local da mídia;
- payload original.

### 5.2 Sequência obrigatória

```text
Webhook Instagram
    ↓
normalizar evento
    ↓
ignorar evento da própria conta
    ↓
verificar idempotência por comment_id
    ↓
registrar comentário recebido no Supabase
    ↓
normalizar texto
    ↓
carregar instagram_comment_keywords.txt do Drive
    ↓
CONTAINS de keyword/variação/typo
    ↓
sem match → registrar resultado e encerrar
    ↓
com match → resolver media_id em offers.publication_events
    ↓
se não encontrar publicação → registrar falha e encerrar
    ↓
carregar copies do Drive
    ↓
montar DM = instagram_comment_dm_intro.txt + publication_events.message_text
    ↓
responder comentário com instagram_comment_public_reply.txt
    ↓
registrar resultado da resposta pública
    ↓
se falhar → encerrar
    ↓
enviar Private Reply/DM
    ↓
registrar resultado da DM
    ↓
fim
```

### 5.3 FIFO

A ordem de negócio é obrigatória:

1. registrar comentário;
2. identificar keyword;
3. identificar publicação/produto;
4. carregar copies;
5. responder publicamente;
6. registrar o resultado da resposta pública;
7. somente após sucesso da resposta pública, enviar a Private Reply/DM;
8. registrar o resultado da DM.

Se a resposta pública falhar, não enviar DM.

Para ordenação cronológica de eventos recebidos da Meta, usar o timestamp do evento, não assumir que a ordem de chegada HTTP representa necessariamente a ordem real.

### 5.4 Composição da DM originada por comentário

```text
[conteúdo de instagram_comment_dm_intro.txt]

[conteúdo exato de offers.publication_events.message_text]
```

O link do produto e o link do grupo WhatsApp permanecem os que já fazem parte da copy original do anúncio (`message_text`). Não duplicar nem reconstruir esses links.

---

## 6. Fluxo de DM espontânea

### 6.1 Entrada

Receber evento de mensagem do Instagram contendo, quando disponíveis:

- `sender.id`;
- `recipient.id`;
- `timestamp`;
- `message.mid`;
- `message.text`;
- `username`, se disponível;
- payload original.

### 6.2 Sequência

```text
DM recebida
    ↓
ignorar evento da própria conta
    ↓
verificar idempotência por message.mid
    ↓
registrar DM recebida no Supabase
    ↓
verificar cooldown por usuário
    ↓
última resposta automática bem-sucedida < 15 min?
    ├─ sim → registrar cooldown e encerrar
    └─ não → carregar instagram_dm_default_reply.txt
                 ↓
              enviar resposta
                 ↓
              registrar resultado
```

Sem buffer e sem interpretação do conteúdo da mensagem.

---

## 7. Cooldown

Cooldown fixo inicial: **15 minutos**.

Chave do cooldown: usuário que fez a requisição (`sender.id` / identificador equivalente da conta Instagram do usuário).

Regra:

- considerar a última resposta automática bem-sucedida para aquele usuário;
- se uma nova DM chegar dentro de 15 minutos, registrar a nova DM, marcar `cooldown_applied = true` e não responder;
- se estiver fora da janela, enviar `instagram_dm_default_reply.txt`;
- o cooldown não impede o registro do evento.

Idempotência e cooldown são controles distintos:

- idempotência impede reprocessar o mesmo evento;
- cooldown impede responder repetidamente a eventos diferentes do mesmo usuário.

---

## 8. Persistência nova no Supabase

Criar duas estruturas novas e separadas.

### 8.1 `offers.instagram_comment_events`

Uma linha por comentário recebido.

Campos mínimos propostos:

```text
id                          uuid PK
instagram_account_id        text
comment_id                  text UNIQUE
media_id                    text
media_product_type          text NULL
user_id                     text
username                    text NULL
comment_text                text
normalized_text             text
matched_keyword             text NULL
keyword_matched             boolean
publication_event_id        uuid NULL
item_id                     bigint NULL
marketplace                 text NULL
event_at                    timestamptz
received_at                 timestamptz
public_reply_text           text NULL
public_reply_status         text
public_reply_id             text NULL
private_reply_text          text NULL
private_reply_status        text
private_reply_recipient_id  text NULL
private_reply_message_id    text NULL
processing_status           text
failure_stage               text NULL
error_code                  text NULL
error_detail                text NULL
processed_at                timestamptz NULL
raw_payload                 jsonb
```

### 8.2 `offers.instagram_dm_events`

Uma linha por DM recebida.

Campos mínimos propostos:

```text
id                       uuid PK
instagram_account_id     text
message_id               text UNIQUE
user_id                  text
recipient_id             text
username                 text NULL
message_text             text
event_at                 timestamptz
received_at              timestamptz
cooldown_applied         boolean
cooldown_reference_at    timestamptz NULL
reply_text               text NULL
reply_status             text
reply_message_id         text NULL
reply_recipient_id       text NULL
processing_status        text
failure_stage            text NULL
error_code               text NULL
error_detail             text NULL
processed_at             timestamptz NULL
raw_payload              jsonb
```

### 8.3 Índices mínimos

Comentários:

- `UNIQUE(comment_id)`
- índice em `(event_at)`
- índice em `(user_id, event_at)`
- índice em `(item_id, event_at)`
- índice em `(media_id, event_at)`
- índice em `(matched_keyword, event_at)`
- índice em `(processing_status, event_at)`

DMs:

- `UNIQUE(message_id)`
- índice em `(event_at)`
- índice em `(user_id, event_at)`
- índice em `(user_id, reply_status, event_at)`
- índice em `(processing_status, event_at)`

Não criar tabela agregada nesta fase.

---

## 9. Estatísticas mínimas suportadas

A modelagem deve permitir consultas diretas para, no mínimo:

- eventos por dia;
- eventos por usuário;
- comentários por usuário;
- DMs por usuário;
- eventos por produto;
- eventos por publicação;
- keywords acionadas;
- taxa de match de keyword;
- respostas públicas enviadas;
- private replies enviadas;
- DMs espontâneas respondidas;
- DMs bloqueadas por cooldown;
- falhas por estágio;
- falhas por tipo;
- volume de intenção por `item_id`.

Manter `raw_payload` para auditoria e extrações futuras sem depender da Meta para reconstrução histórica.

---

## 10. Falhas

Regra global:

> registrar evento + contexto da falha + encerrar. Não executar fallback de negócio.

Casos mínimos:

- publicação não encontrada para `media_id`;
- `message_text` ausente;
- arquivo obrigatório do Drive indisponível;
- erro ao consultar keywords;
- erro ao responder comentário;
- erro ao enviar Private Reply;
- erro ao enviar resposta de DM;
- erro de autenticação/API;
- payload inválido ou sem identificador necessário.

Campos de erro:

- `processing_status`;
- `failure_stage`;
- `error_code`;
- `error_detail`;
- `processed_at`.

Não mascarar erro com resposta genérica ao usuário.

---

## 11. Autenticação e conexão Instagram

Não criar arquitetura nova de token.

A implementação deve reutilizar a forma de autenticação já documentada e utilizada pelo fluxo atual de publicação do Instagram na branch ativa, incluindo credenciais já configuradas no n8n/ambiente operacional.

Não implementar:

- Data Table de token;
- schedule de refresh;
- fluxo próprio de renovação;
- armazenamento adicional do access token.

Na implantação, validar que o token/credencial atual possui as permissões necessárias para leitura de webhooks, gerenciamento de comentários e mensagens, além das permissões de publicação já utilizadas.

---

## 12. Webhook e roteamento

Um receptor pode receber múltiplos tipos de eventos do Instagram.

O roteamento deve separar explicitamente:

```text
comentário → Comment Handler
DM         → Direct Handler
outros     → registrar/ignorar conforme escopo
```

O filtro da própria conta é obrigatório para evitar loop de automação.

O webhook deve usar a validação/autenticação compatível com a integração atual do projeto e com os requisitos da Meta.

---

## 13. Escopo de publicação

A automação não deve filtrar por formato específico.

Aceitar qualquer publicação cuja identificação possa ser resolvida por:

```text
evento.media_id = publication_events.payload.published_media_id
```

Isso inclui Reels, carrossel ou outros formatos registrados futuramente.

---

## 14. Retenção

Manter todos os registros no Supabase sem expiração automática nesta fase.

Não criar:

- TTL;
- purge job;
- política de arquivamento;
- agregação que descarte eventos individuais.

---

## 15. Fora do escopo

- Agent/IA para responder comentários.
- Agent/IA para responder DMs.
- LLM.
- memória conversacional.
- buffer de mensagens.
- Redis para conversa.
- fuzzy matching.
- follow-up automático.
- CRM.
- lead scoring.
- remarketing.
- múltiplas sequências de Direct.
- token refresher.
- alteração dos fluxos atuais de publicação.
- nova lógica de seleção de produto.
- reconstrução de copy do anúncio.

---

## 16. Critérios de aceite

A implementação só é considerada concluída quando:

1. comentário com keyword configurada é reconhecido após normalização;
2. typo presente em `instagram_comment_keywords.txt` também é reconhecido;
3. comentário sem match é registrado e não gera resposta;
4. `media_id` resolve corretamente `publication_events` e `item_id`;
5. resposta pública vem exclusivamente do arquivo do Drive;
6. DM de comentário é exatamente `instagram_comment_dm_intro.txt + publication_events.message_text`;
7. falha da resposta pública impede o envio da DM;
8. comentário duplicado não é processado duas vezes;
9. DM espontânea é registrada;
10. primeira DM fora de cooldown recebe `instagram_dm_default_reply.txt`;
11. nova DM do mesmo usuário dentro de 15 minutos é registrada e não respondida;
12. mesma `message.mid` não é processada duas vezes;
13. falhas ficam registradas com estágio e detalhe;
14. comentários e DMs ficam em tabelas distintas;
15. consultas por dia, usuário e produto funcionam sem agregação externa;
16. nenhum texto destinado ao usuário fica hardcoded no workflow;
17. nenhum token refresher novo é criado;
18. fluxo existente de publicação permanece inalterado.

---

## 17. Ordem recomendada de implementação

1. criar migration das duas tabelas e índices;
2. validar credenciais/permissões atuais do Instagram;
3. configurar/validar webhook;
4. implementar normalização e roteamento;
5. implementar leitura dos quatro arquivos do Drive;
6. implementar handler de comentário;
7. implementar lookup em `publication_events`;
8. implementar resposta pública;
9. implementar Private Reply;
10. implementar handler de DM;
11. implementar cooldown de 15 minutos;
12. implementar idempotência;
13. implementar tratamento de falhas;
14. validar estatísticas mínimas;
15. testar com payloads reais/anonimizados antes da ativação em produção.

---

## 18. Referência funcional

A estrutura funcional foi delimitada a partir do fluxo demonstrado no vídeo/transcrição `"EU QUERO" no Instagram com N8N (Alternativa ao Manychat)`, aproveitando apenas os elementos pertinentes ao projeto:

- webhook de eventos do Instagram;
- filtro da própria conta;
- separação comentário/DM;
- detecção de palavra-chave;
- resposta ao comentário específico;
- Private Reply;
- persistência e idempotência próprias do projeto.

Partes do vídeo que não fazem parte desta implementação:

- agente de IA;
- Basic LLM Chain;
- buffer;
- Redis;
- fragmentação de respostas;
- token refresher/Data Tables.
