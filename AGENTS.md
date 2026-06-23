# AGENTS.md

Este arquivo define os agentes internos, o fluxo de implementação e o harness do projeto.

## Diretrizes do projeto

- Linguagem padrão: **Python 3.11+**.
- Toda integração externa deve ficar atrás de uma interface/provider.
- O modo padrão é `dry-run`.
- Não versionar segredos, tokens, cookies, QR codes ou sessões.
- Não implementar mecanismos para burlar políticas, limites ou detecção de plataformas.
- Publicação real só deve existir após aprovação humana, logs e configuração explícita.
- Mensagens de commit devem seguir `docs/commit-pattern.md`.

## Regra de trabalho GitHub/local

Para reduzir erro manual de copia e cola, o fluxo oficial deste projeto é:

- Mudanças de código e documentação são feitas diretamente no GitHub por este assistente.
- Testes locais, arquivo `.env`, credenciais e validações com ambiente real são feitos pelo usuário no VSCode.
- Após cada mudança feita no GitHub, o usuário deve rodar `git pull` em `C:\Automacao_Grupos-de-Ofertas` antes de testar localmente.
- Segredos, tokens, chaves de API, cookies, QR codes e sessões nunca devem ser enviados ao GitHub.

Comandos locais recomendados após mudanças no GitHub:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ofertas_bot.harness --niche maquiagem --marketplace shopee --dry-run
```

## Agentes

### 1. Collector Agent

Responsável por buscar produtos em marketplaces.

Entradas:

- marketplace: `shopee`, `amazon` ou `mock`
- nicho
- limite de produtos

Saída:

- lista normalizada de `Offer`

### 2. Scorer Agent

Responsável por ranquear ofertas.

Critérios iniciais:

- desconto percentual;
- comissão;
- vendas/reputação;
- frete/prime;
- aderência ao nicho.

Saída:

- lista de `ScoredOffer`

### 3. Copywriter Agent

Gera mensagem curta, clara e variada.

Regras:

- informar que o link pode gerar comissão;
- não prometer preço permanente;
- evitar urgência falsa;
- não ocultar a origem do link.

### 4. Compliance Agent

Valida a mensagem antes de publicar.

Bloqueia:

- mensagem sem disclosure de afiliado;
- oferta sem link;
- preço ou desconto inválido;
- publicação real quando `ENABLE_REAL_PUBLISH=false`.

### 5. Publisher Agent

Publica ou simula publicação.

Na fase inicial:

- apenas `DryRunPublisher`.

No futuro:

- provider oficial/permitido;
- logs auditáveis;
- fila com aprovação humana.

## Harness

O harness executa o pipeline completo localmente:

```bash
python -m ofertas_bot.harness --niche maquiagem --marketplace shopee --dry-run
```

Fluxo:

```text
Collector -> Scorer -> Copywriter -> Compliance -> Publisher
```

## Commits

Use `docs/commit-pattern.md` como recurso oficial para gerar mensagens de commit.

Formato obrigatório:

```text
tipo(escopo): descrição curta no presente
```

Exemplo:

```text
docs(workflow): adiciona padrao de commits
```

## Critérios de aceite do MVP

- `pytest` passa localmente.
- Harness roda sem segredos.
- Nenhuma publicação real acontece.
- Mensagens contêm aviso de afiliado.
- Código organizado por agentes/providers.

## Próximas issues sugeridas

1. Implementar provider real da Shopee.
2. Implementar provider real da Amazon PA API.
3. Adicionar persistência SQLite.
4. Criar fila de aprovação humana.
5. Criar CI com pytest e ruff.
