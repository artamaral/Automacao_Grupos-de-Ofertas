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
  -> n8n consulta ranking
  -> n8n monta mensagem
  -> n8n envia para allowlist
  -> Supabase registra historico
```

Diretrizes obrigatorias:

- Priorizar simplicidade operacional.
- Implementar somente mudancas que ajudem diretamente o MVP ou reduzam
  complexidade do caminho principal.
- O catalogo ativo do Supabase e a base operacional inicial.
- n8n consulta `offers.v_offer_ranking_current` diretamente.
- n8n monta mensagens por template simples no workflow ou em configuracao
  segura do proprio n8n.
- n8n so envia para destinos explicitamente allowlisted.
- n8n registra tentativa e resultado em `offers.publication_events`.
- Cloud Run nao e requisito do MVP; fica como evolucao futura ou ponte tecnica
  opcional.
- Descoberta, paginacao ampla, limpeza e curadoria de catalogos permanecem
  fora da rodada diaria.
- Coleta automatica e revisao de nichos/subnichos sao melhorias pos-MVP.

## Regra de trabalho GitHub/local

- Mudancas de codigo e documentacao sao feitas diretamente no repositorio.
- Testes locais, `.env`, credenciais e validacoes com ambiente real sao feitos
  pelo usuario no VSCode.
- Segredos, tokens, chaves de API, cookies, QR codes e sessoes nunca devem ser
  enviados ao GitHub.
- Nao criar branches novas sem aprovacao explicita do usuario.
- O fluxo padrao deve acontecer na `main`, salvo pedido diferente.

### Continuidade

- Nao pedir validacao apos cada alteracao pequena.
- Agrupar mudancas relacionadas em blocos maiores antes de solicitar teste
  local.
- Executar em sequencia as etapas seguras que nao exigem decisao humana.
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

No MVP, o ranking operacional e consumido via `offers.v_offer_ranking_current`.

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
- n8n consulta `offers.v_offer_ranking_current` diretamente.
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
