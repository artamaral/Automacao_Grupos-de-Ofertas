# AGENTS.md

Este arquivo define as regras de trabalho do projeto.

## Diretrizes do projeto

- Linguagem padrao: Python 3.11+.
- Toda integracao externa deve ficar atras de interface/provider.
- O modo padrao continua sendo `dry-run`.
- Nao versionar segredos, tokens, cookies, QR codes ou sessoes.
- Nao implementar mecanismos para burlar politicas, limites ou deteccao de
  plataformas.
- Publicacao real so existe com configuracao explicita, canal permitido,
  destino em allowlist e logs auditaveis.
- Mensagens de commit devem seguir `docs/commit-pattern.md`.

## Decisao operacional atual

A decisao canonica vigente esta em
[`docs/decisao-mvp-supabase-n8n.md`](docs/decisao-mvp-supabase-n8n.md).

O MVP deve ser lido assim:

```text
Catalogo ativo no Supabase
  -> planejador persiste a fila diaria do feminino
  -> n8n consulta a janela pronta
  -> n8n monta mensagem
  -> n8n envia para allowlist
  -> Supabase registra historico
```

Diretrizes obrigatorias:

- Priorizar simplicidade operacional.
- Implementar somente mudancas que ajudem diretamente o MVP ou reduzam
  complexidade do caminho principal.
- O catalogo ativo do Supabase e a base operacional inicial.
- Para `feminino`, o planejador consulta `offers.v_offer_ranking_current` e
  persiste `offers.daily_dispatch_plan` somente com itens
  `refresh_status='FRESH'`; o n8n consulta `offers.v_daily_dispatch_ready` por
  data e hora e so claima slots que continuam prontos nessa view.
- n8n monta mensagens por template simples no workflow ou em configuracao
  segura do proprio n8n.
- n8n so envia para destinos explicitamente allowlisted.
- n8n registra tentativa e resultado em `offers.publication_events`.
- Cloud Run nao e requisito do MVP; fica como evolucao futura ou ponte tecnica
  opcional.
- Bandas, rotacao semanal, fallback e sequenciamento nao devem morar no n8n.
- Descoberta, paginacao ampla, limpeza e curadoria de catalogos permanecem
  fora da rodada diaria.
- Coleta automatica e revisao de nichos/subnichos sao melhorias pos-MVP.

## Regra de trabalho GitHub/local

- Mudancas de codigo e documentacao sao feitas diretamente no repositorio.
- Testes locais, `.env`, credenciais e validacoes com ambiente real sao feitos
  pelo usuario no VSCode.
- Segredos, tokens, chaves de API, cookies, QR codes e sessoes nunca devem ser
  enviados ao GitHub.
- E proibido criar uma branch nova sem que o usuario tenha solicitado isso de forma clara e explicita. Aprovacao implicita, conveniencia tecnica ou inferencia de fluxo nao autorizam criar branch.
- Na duvida, permanecer e trabalhar na branch atual. Nunca trocar para `main` ou criar outra branch apenas por suposicao; usar a branch indicada pelo usuario ou a branch atual verificada no repositorio.
- O GPT nao esta autorizado a criar, trocar, publicar ou usar branch diferente sem solicitacao ou autorizacao explicita do usuario.
- Antes de qualquer commit ou push, o GPT deve confirmar a branch ativa e informar em qual branch a mudanca sera registrada.

### Continuidade

- Nao pedir validacao apos cada alteracao pequena.
- Agrupar mudancas relacionadas em blocos maiores antes de solicitar teste
  local.
- Executar em sequencia as etapas seguras que nao exigem decisao humana.
- Apos implementar qualquer mudanca de codigo, sempre rodar os testes
  relevantes antes de finalizar a tarefa. Se a mudanca tocar comportamento
  compartilhado ou fluxo operacional, rodar tambem a suite completa quando
  viavel.
- Se `pytest` nao estiver disponivel, instalar as dependencias de
  desenvolvimento em `.venv` com `python3 -m venv .venv` e
  `.venv/bin/python -m pip install -e '.[dev]'`; depois executar os testes com
  `.venv/bin/python -m pytest`.
- Solicitar interacao somente quando houver credencial, aprovacao externa,
  definicao humana, validacao local indispensavel ou alteracao de trava.
- Quando varios testes validarem o mesmo bloco, solicitar uma unica rodada de
  `ruff` e `pytest` ao final.

### Testes e chamadas de API

- Em testes de API, executar exatamente parametros, filtros, keywords e campos
  solicitados pelo usuario.
- Nao inferir nem acrescentar `keyword`, `listType`, `matchId`, `sortType`,
  `shopId`, `itemId`, `productCatId`, `isAMSOffer`, `isKeySeller` ou qualquer
  outro parametro sem pedido explicito.
- Separar com clareza o que foi pedido, o que foi enviado e o que voltou.
- Se faltar dado para montar chamada com seguranca, parar e solicitar o dado.
- Sugestoes alternativas devem ser separadas da execucao principal.

Comandos locais recomendados apos mudancas:

```powershell
git pull
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

## Agentes internos

### Collector Agent

Carrega ofertas normalizadas a partir de provider, catalogo curado ou outra
fonte controlada.

No MVP, a base operacional e o catalogo ativo no Supabase, nao uma nova
descoberta diaria.

### Scorer Agent

Ranqueia ofertas por sinais comerciais simples: desconto, comissao, vendas,
avaliacao, frete e aderencia.

No `feminino`, o ranking alimenta previamente `offers.daily_dispatch_plan`; o
n8n consome a view `offers.v_daily_dispatch_ready`, que revalida elegibilidade
e freshness no momento do envio.

### Copywriter Agent

Gera mensagem curta e clara, com disclosure de afiliado e sem promessa de preco
permanente.

No MVP, essa montagem pode acontecer diretamente no n8n por template simples.

### Compliance Agent

Valida disclosure, link, preco e travas de publicacao.

No MVP, a trava minima obrigatoria e allowlist de destino no n8n.

### Publisher Agent

Publica ou simula publicacao.

No MVP, o envio real controlado acontece no n8n; o publisher Python permanece
apoio de desenvolvimento ou evolucao futura.

## Criterios de aceite do MVP

- Catalogo ativo do Supabase e usado como base.
- o planejador do `feminino` persiste somente itens `FRESH`.
- n8n consulta `offers.v_daily_dispatch_ready` para o `feminino` e nao pode
  claimar slot stale.
- n8n monta mensagem com aviso de afiliado.
- n8n bloqueia destino fora da allowlist.
- n8n registra tentativa/resultado em `offers.publication_events`.
- Retry de registro nao duplica publicacao.

## Proximas issues sugeridas

1. Validar query MVP do n8n para 1 profile.
2. Configurar template simples e disclosure no n8n.
3. Configurar allowlist e bloqueio de destino nao permitido.
4. Registrar envios em `offers.publication_events` com idempotencia.
5. Depois do MVP, automatizar coleta e revisar nichos/subnichos.

## Commit sugerido

```text
docs(mvp): simplifica operacao supabase n8n
```
