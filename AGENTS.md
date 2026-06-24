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
python -m ofertas_bot.harness --niche maquiagem --marketplace mock --dry-run
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
- Fluxo operacional simplificado e automatizável.

## Próximas issues sugeridas

1. Consolidar geração de lista de ofertas selecionadas.
2. Consolidar geração de mensagens a partir das ofertas selecionadas.
3. Simplificar o comunicador de API por contrato único.
4. Reduzir documentação operacional para o caminho recomendado.
5. Retomar Shopee/Amazon reais apenas após credenciais e aprovações formais.
