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
- Mudanças de comportamento devem nascer em `specs/` antes de serem implementadas, salvo correções pequenas e óbvias de bug, lint ou documentação.
- Regras de numeração, locais e criação de arquivos devem seguir `docs/regras-de-arquivos.md`.

## Fluxo por specs

O projeto deve usar specs versionadas para reduzir ambiguidade entre planejamento, GPT, Codex e implementação.

Fluxo oficial para novas funcionalidades:

```text
ideia -> spec em specs/ -> revisão humana -> implementação -> testes -> documentação atualizada
```

Regras obrigatórias:

- Specs implementáveis ficam em `specs/NNN_nome_curto.md`.
- O número da spec tem três dígitos e nunca deve ser reutilizado.
- Não renumerar specs antigas.
- Não implementar comportamento fora do escopo aprovado na spec.
- Cada spec deve conter objetivo, entrada, saída, regras obrigatórias, fora de escopo, critérios de aceite, testes esperados e validação local.
- Specs em status `Rascunho` podem ser usadas para discussão, mas não devem ser tratadas como aprovação final de implementação.
- Quando uma spec virar código, atualizar seu status e a documentação permanente relacionada.
- Documentação permanente fica em `docs/`; contratos implementáveis ficam em `specs/`.

## Decisão operacional atual

O projeto deve priorizar simplicidade operacional. A partir desta decisão, o foco é reduzir comandos, flags e artefatos soltos, consolidando o fluxo em poucos pontos de entrada automatizáveis.

A definição oficial de objetivo, escopo e modelo operacional está em [`docs/objetivo-operacional.md`](docs/objetivo-operacional.md).
A análise oficial que orienta as próximas decisões está em [`docs/analise-operacional.md`](docs/analise-operacional.md).

Diretrizes obrigatórias:

- Implementar apenas mudanças que ajudem diretamente um destes eixos: comunicador com API, geração de lista de ofertas ou geração de mensagens.
- Não criar novos CLIs pequenos ou flags auxiliares sem necessidade operacional clara.
- Tratar os CLIs já existentes como ferramentas internas de suporte, não como fluxo principal para operação humana diária.
- O fluxo final deve ser pensado para ser chamado por automação/agendador/orquestrador, não por um humano executando vários scripts manualmente.
- Humanos participam apenas nas decisões necessárias: aprovação/rejeição, credenciais, configuração de travas e validações locais importantes.
- A próxima prioridade de implementação é simplificar o fluxo principal em torno de API -> lista de ofertas -> mensagens.
- Documentação deve destacar o fluxo recomendado e mover detalhes avançados para seções de apoio ou debug.
- Segurança continua obrigatória: nada de envio real, HTTP real, credenciais ou publicação real sem configuração explícita, canal permitido e aprovação humana.

## Regra de trabalho GitHub/local

Para reduzir erro manual de copia e cola, o fluxo oficial deste projeto é:

- Mudanças de código e documentação são feitas diretamente no GitHub por este assistente.
- Testes locais, arquivo `.env`, credenciais e validações com ambiente real são feitos pelo usuário no VSCode.
- Após cada mudança feita no GitHub, o usuário deve rodar `git pull` em `C:\Automacao_Grupos-de-Ofertas` antes de testar localmente.
- Segredos, tokens, chaves de API, cookies, QR codes e sessões nunca devem ser enviados ao GitHub.
- O GPT não deve criar branchs novas sem aprovação explícita do usuário.
- O fluxo padrão de trabalho deve acontecer na `main`, salvo quando o usuário pedir outra estratégia.

### Continuidade e agrupamento de etapas

Para reduzir interrupções durante o desenvolvimento assistido:

- Não pedir validação após cada alteração pequena.
- Agrupar mudanças relacionadas em blocos maiores antes de solicitar teste local.
- Executar em sequência todas as etapas seguras que não exigem decisão do usuário.
- Solicitar interação somente quando houver necessidade de definição humana, credencial, aprovação externa, validação local indispensável ou alteração de trava de segurança.
- Quando vários testes validarem o mesmo bloco de mudanças, solicitar uma única rodada de `ruff` e `pytest` ao final do bloco.
- Se uma etapa falhar por lint ou teste, corrigir a falha antes de iniciar nova funcionalidade.

### Regra para testes e chamadas de API

Para evitar confusão na leitura dos resultados:

- Em testes de API, executar exatamente os parâmetros, filtros, keywords e campos solicitados pelo usuário.
- Não inferir nem acrescentar `keyword`, `listType`, `matchId`, `sortType`, `shopId`, `itemId`, `productCatId`, `isAMSOffer`, `isKeySeller` ou qualquer outro parâmetro sem pedido explícito do usuário.
- Não trocar nomes da API por apelidos internos ao descrever query, parâmetro, campo ou resultado.
- Quando houver necessidade de paginação, deixar explícito que a mesma query foi repetida mudando apenas `page`.
- Sempre separar com clareza:
  - o que foi pedido pelo usuário;
  - o que foi realmente enviado na query;
  - o que voltou na resposta.
- Se a informação fornecida pelo usuário for insuficiente para montar a chamada com segurança, parar e solicitar os dados faltantes ao usuário antes de executar.
- Se for útil sugerir um cenário alternativo de teste, apresentar isso como sugestão separada, nunca misturada com a execução principal pedida pelo usuário.

Comandos locais recomendados após mudanças no GitHub:

```powershell
git pull
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

O harness dry-run pode ser rodado como validação operacional adicional, sem substituir `ruff` e `pytest`:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.harness --niche maquiagem --marketplace mock --dry-run
```

## Agentes

### 1. Collector Agent

Responsavel por carregar a base de ofertas que entra no pipeline principal.

Decisao operacional atual:

- a geracao de catalogo amplo, longa e exploratoria fica fora do fluxo
  automatizado principal;
- quando houver catalogo curado e salvo em arquivo, esse catalogo passa a ser a
  entrada operacional do `Collector`;
- chamadas exploratorias de marketplace continuam existindo como etapa separada
  de descoberta, nao como parte obrigatoria do pipeline diario.

Entradas:

- arquivo de catalogo curado ou outra fonte controlada equivalente
- marketplace de referencia: `shopee`, `amazon` ou `mock`
- nicho
- limite de produtos, quando aplicavel

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
python -m ofertas_bot.harness --niche maquiagem --marketplace mock --dry-run
```

Fluxo:

```text
Collector -> Scorer -> Copywriter -> Compliance -> Publisher
```

No estado atual, esse fluxo deve ser lido assim:

```text
Catalogo curado -> Collector -> Scorer -> Copywriter -> Compliance -> Publisher
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
- Fluxo operacional simplificado e automatizável.
- Specs e documentação permanente são atualizadas quando uma mudança altera comportamento esperado.

## Próximas issues sugeridas

1. Revisar `specs/001_catalog_ingestion.md`.
2. Revisar `specs/002_product_scoring.md`.
3. Revisar `specs/003_copywriter_agent.md`.
4. Consolidar geração de lista de ofertas selecionadas.
5. Consolidar geração de mensagens a partir das ofertas selecionadas.
6. Simplificar o comunicador de API por contrato único.
7. Reduzir documentação operacional para o caminho recomendado.
8. Retomar Shopee/Amazon reais apenas após credenciais e aprovações formais.
