# Padrão de Commits — Automação de Grupos de Ofertas

Este documento é o recurso oficial do projeto para gerar, revisar e padronizar mensagens de commit.

Foi adaptado a partir do padrão usado no projeto `social_media-analytics`, ajustando exemplos, escopos e regras para o contexto de ofertas, afiliados, specs, providers e fluxo local dry-run.

## Objetivo

Padronizar os commits para garantir:

- clareza sobre mudanças;
- rastreabilidade técnica;
- facilidade de debug;
- organização conforme o projeto escala;
- histórico utilizável como documentação;
- facilidade para revisar mudanças feitas por GPT, Codex ou humano.

## Formato obrigatório

```text
tipo(escopo): descrição curta no presente
```

A descrição deve estar no presente e explicar o que o commit faz.

Exemplos corretos:

```text
feat(collector): adiciona provider mock de ofertas
fix(copywriter): corrige formato da linha de preco
docs(workflow): documenta padrao de commits
test(compliance): valida bloqueio sem aviso de afiliado
chore(repo): adiciona gitignore
```

## Exemplos proibidos

```text
update geral
ajustes
mudancas
teste
corrigindo coisas
codigo novo
arruma bot
final
wip
```

Esses exemplos são proibidos porque não deixam claro o que mudou, onde mudou ou por que a mudança existe.

## Tipos de commit

### feat — nova funcionalidade

Use quando o commit adiciona uma capacidade nova ao sistema.

```text
feat(collector): adiciona leitura de catalogo curado
feat(shopee): adiciona builder de consulta fake
feat(queue): cria fila de aprovacao humana
feat(local-flow): adiciona etapa de finalize
```

### fix — correção de bug

Use quando o commit corrige comportamento incorreto.

```text
fix(copywriter): corrige desconto arredondado
fix(compliance): bloqueia oferta sem link
fix(harness): respeita limite de ofertas informado
fix(local-flow): impede finalize sem fila revisada
```

### refactor — melhoria interna sem mudar comportamento

Use quando reorganiza código sem alterar a saída esperada.

```text
refactor(agents): separa copywriter e compliance
refactor(providers): padroniza interface de marketplace
refactor(settings): centraliza configuracao de ambiente
refactor(local-flow): extrai montagem de artefatos
```

### docs — documentação

Use para documentação, specs, políticas e decisões.

```text
docs(readme): atualiza fluxo operacional local
docs(workflow): define padrao de commits
docs(copy): documenta formato da linha de preco
docs(specs): adiciona contrato de ingestao de catalogo
```

### chore — tarefas operacionais

Use para manutenção de repositório, dependências, arquivos auxiliares ou ajustes sem impacto direto de produto.

```text
chore(repo): adiciona gitignore
chore(env): atualiza variaveis de exemplo
chore(deps): atualiza dependencias de desenvolvimento
chore(data): limpa artefatos locais versionados por engano
```

### test — testes e validações

Use quando adiciona ou ajusta testes automatizados, fixtures ou validações.

```text
test(scorer): valida ranking por desconto e vendas
test(copywriter): valida aviso de afiliado
test(compliance): bloqueia publicacao real desabilitada
test(local-flow): valida prepare com marketplace mock
```

### perf — performance

Use quando melhora desempenho sem alterar comportamento funcional.

```text
perf(queue): reduz consultas repetidas
perf(provider): cacheia resposta de marketplace
perf(scoring): otimiza calculo de pontuacao
perf(local-flow): reduz leituras repetidas de artefatos
```

### build — build e empacotamento

Use para empacotamento, build, packaging, Docker ou configuração de distribuição.

```text
build(package): ajusta configuracao do pyproject
build(deps): adiciona dependencia de runtime
build(docker): cria imagem do worker
build(cli): registra entrypoint do fluxo local
```

### ci — integração contínua

Use para GitHub Actions, validações automáticas e automações de CI.

```text
ci(github): adiciona workflow de pytest e ruff
ci(actions): publica artefatos de teste
ci(release): valida pacote antes de tag
ci(docs): valida links internos da documentacao
```

## Escopos padrão do projeto

Use sempre um escopo relevante. O escopo deve apontar a parte principal afetada.

### Núcleo

- agents
- collector
- scorer
- copywriter
- compliance
- publisher
- harness
- local-flow
- settings
- models

### Providers e integrações

- providers
- shopee
- amazon
- whatsapp
- telegram
- api
- queue
- scheduler

### Dados, catálogo e qualidade

- data
- catalog
- data-quality
- scoring
- offers
- media
- fixtures

### Specs e documentação

- docs
- specs
- readme
- roadmap
- workflow
- repo
- env
- architecture

### Automação e testes

- ci
- build
- tests
- lint

## Como escolher tipo e escopo

Pergunte primeiro: qual é a natureza da mudança?

```text
Adicionou comportamento novo?         -> feat
Corrigiu comportamento errado?        -> fix
Só reorganizou código?                -> refactor
Mudou documentação/spec?              -> docs
Mudou teste ou fixture?               -> test
Mudou build/dependência/config repo?   -> build ou chore
Mudou CI?                             -> ci
Melhorou desempenho?                  -> perf
```

Depois pergunte: qual área foi mais afetada?

```text
Copy de mensagem                      -> copywriter
Validação de mensagem                 -> compliance
Busca ou carga de ofertas             -> collector
Ranqueamento                          -> scorer
Fluxo local prepare/finalize          -> local-flow
Integração Shopee                     -> shopee
Integração Amazon                     -> amazon
Specs numeradas                       -> specs
Documentação de processo              -> workflow
```

## Exemplos reais para este projeto

### Catálogo e coleta

```text
feat(collector): adiciona carga de catalogo curado
fix(catalog): remove ofertas sem preco valido
test(catalog): valida deduplicacao por url canonica
docs(catalog): define regras de qualidade de ofertas
```

### Scoring

```text
feat(scorer): adiciona peso de reputacao no ranking
fix(scoring): impede vantagem para desconto invalido
refactor(scorer): isola calculo de score por criterio
test(scoring): valida ordenacao por desconto e vendas
```

### Copy e compliance

```text
fix(copywriter): corrige formato da linha de preco
test(copywriter): valida preco com valor antigo
docs(copy): documenta aviso obrigatorio de afiliado
fix(compliance): bloqueia mensagem sem disclosure
```

### Providers

```text
feat(shopee): adiciona mapper de resposta da api
fix(amazon): preserva detail page url do provider
refactor(providers): padroniza transport fake
test(providers): valida bloqueio de http real por padrao
```

### Fluxo local

```text
feat(local-flow): gera bundle de revisao local
fix(local-flow): bloqueia finalize sem aprovacao
refactor(local-flow): separa prepare e finalize
docs(readme): atualiza comandos do fluxo recomendado
```

### Specs e governança

```text
docs(specs): adiciona spec de ingestao de catalogo
docs(workflow): define regra de numeracao de arquivos
docs(architecture): descreve camadas do pipeline
docs(agents): adiciona regra de trabalho por specs
```

## Tamanho e boas práticas

Faça:

- commits pequenos;
- uma mudança por commit;
- mensagens específicas;
- verbo no presente;
- escopo coerente com o arquivo alterado;
- commit de docs separado de mudança de código quando forem assuntos independentes;
- commit de teste junto da correção quando o teste prova a correção.

Evite:

- commits grandes demais;
- misturar provider real, testes, docs e refactor no mesmo commit sem necessidade;
- mensagens genéricas;
- múltiplos problemas no mesmo commit;
- usar escopo genérico quando existir escopo específico;
- commitar `.env`, tokens, cookies, QR codes, sessões ou artefatos locais de `.data`.

## Regra de validação do commit

Antes de commitar, pergunte:

1. O que foi feito está claro?
2. Onde foi feito está claro?
3. O motivo está implícito?
4. O commit respeita a branch correta?
5. O commit não mistura assuntos diferentes?

Se a resposta não for clara, reescreva ou divida o commit.

## Regra de branch antes de commitar

Antes de criar qualquer commit ou atualizar qualquer documento, verificar a branch correta.

Regra principal:

- `main` recebe mudanças revisadas e aceitas para o projeto como um todo.
- `docs/spec-governance` recebe a revisão atual de documentação, specs, governança e regras de trabalho.
- branches `feat/<tema>` recebem funcionalidades novas antes de revisão.
- branches `fix/<tema>` recebem correções isoladas antes de revisão.
- branches experimentais não devem ser usadas para publicação real nem para ativar HTTP real.

Checklist obrigatório antes de editar localmente:

1. Rodar `git branch --show-current`.
2. Confirmar se a tarefa é documentação, spec, feature, fix ou experimento.
3. Se for revisão de specs/governança, trabalhar em `docs/spec-governance`.
4. Se for feature nova, criar ou usar `feat/<tema>`.
5. Se for correção isolada, criar ou usar `fix/<tema>`.
6. Não misturar mudanças não relacionadas no mesmo commit.
7. Não commitar segredos ou artefatos locais.

Exemplos:

```bash
# Correto para documentação geral de governança
git commit -m "docs(workflow): atualiza padrao de commits"

# Correto para copy
git commit -m "fix(copywriter): corrige formato da linha de preco"

# Correto para teste
git commit -m "test(compliance): valida aviso de afiliado"

# Correto para spec
git commit -m "docs(specs): adiciona contrato do orquestrador local"
```

## Padrão diário

Exemplo de sequência saudável de commits:

```bash
git commit -m "docs(specs): adiciona contrato de ingestao de catalogo"
git commit -m "feat(collector): implementa carga de catalogo curado"
git commit -m "test(collector): valida remocao de oferta sem preco"
git commit -m "docs(readme): atualiza fluxo de catalogo curado"
```

## Commits gerados por GPT ou Codex

Quando este assistente fizer mudanças no GitHub:

- usar o mesmo padrão obrigatório;
- preferir commits pequenos e rastreáveis;
- não criar branch nova sem aprovação explícita do usuário;
- não atualizar `main` se o usuário pediu branch separada;
- explicar no resumo final quais arquivos foram alterados;
- lembrar que testes locais ficam com o usuário quando a mudança depender do ambiente local.

## Diretriz final

> O commit é a memória técnica do projeto.

Se você não consegue entender um commit depois de 30 dias, ele está errado.

Este padrão é obrigatório para manter clareza, controle, escalabilidade e confiabilidade do projeto.
