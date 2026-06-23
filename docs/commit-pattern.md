# Padrão de Commits — Automação de Grupos de Ofertas

Este documento é o recurso oficial do projeto para gerar, revisar e padronizar mensagens de commit.

## Objetivo

Padronizar os commits para garantir:

- clareza sobre mudanças;
- rastreabilidade técnica;
- facilidade de debug;
- organização conforme o projeto escala;
- histórico utilizável como documentação.

## Formato obrigatório

```text
tipo(escopo): descrição curta no presente
```

Exemplos:

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
```

## Tipos de commit

### feat — nova funcionalidade

```text
feat(collector): adiciona provider da shopee
feat(amazon): adiciona busca via pa api
feat(queue): cria fila de aprovacao humana
```

### fix — correção de bug

```text
fix(copywriter): corrige desconto arredondado
fix(compliance): bloqueia oferta sem link
fix(harness): respeita limite de ofertas informado
```

### refactor — melhoria interna sem mudar comportamento

```text
refactor(agents): separa copywriter e compliance
refactor(providers): padroniza interface de marketplace
refactor(settings): centraliza configuracao de ambiente
```

### docs — documentação

```text
docs(readme): atualiza instrucoes de instalacao
docs(workflow): define padrao de commits
docs(copy): documenta formato da linha de preco
```

### chore — tarefas operacionais

```text
chore(repo): adiciona gitignore
chore(env): atualiza variaveis de exemplo
chore(deps): atualiza dependencias de desenvolvimento
```

### test — testes e validações

```text
test(scorer): valida ranking por desconto e vendas
test(copywriter): valida aviso de afiliado
test(compliance): bloqueia publicacao real desabilitada
```

### perf — performance

```text
perf(queue): reduz consultas repetidas
perf(provider): cacheia resposta de marketplace
perf(scoring): otimiza calculo de pontuacao
```

### build — build e empacotamento

```text
build(package): ajusta configuracao do pyproject
build(deps): adiciona dependencia de runtime
build(docker): cria imagem do worker
```

### ci — integração contínua

```text
ci(github): adiciona workflow de pytest e ruff
ci(actions): publica artefatos de teste
ci(release): valida pacote antes de tag
```

## Escopos padrão do projeto

Use sempre um escopo relevante.

### Núcleo

- agents
- collector
- scorer
- copywriter
- compliance
- publisher
- harness
- settings
- models

### Providers e integrações

- providers
- shopee
- amazon
- whatsapp
- queue
- scheduler

### Dados e qualidade

- data
- data-quality
- scoring
- offers
- media

### Gestão e documentação

- docs
- readme
- roadmap
- workflow
- repo
- env

### Automação

- ci
- build
- tests

## Boas práticas

Faça:

- commits pequenos;
- uma mudança por commit;
- mensagens específicas;
- verbo no presente;
- escopo coerente com o arquivo alterado.

Evite:

- commits grandes demais;
- misturar integração real, testes e documentação sem necessidade;
- mensagens genéricas;
- múltiplos problemas no mesmo commit.

## Regra de validação

Antes de commitar, pergunte:

1. O que foi feito está claro?
2. Onde foi feito está claro?
3. O motivo está implícito?

Se não estiver claro, reescreva a mensagem.

## Regra de branch antes de commitar

Antes de criar qualquer commit ou atualizar qualquer documento, verificar a branch correta.

Regra principal:

- `main` recebe documentação geral, decisões técnicas, roadmap, modelos, agentes, providers, harness, testes e mudanças que afetam o projeto como um todo.
- branches de feature devem receber trabalho experimental ou mudanças maiores antes de PR.

Checklist obrigatório antes de editar localmente:

1. Rodar `git branch --show-current`.
2. Confirmar se a tarefa é geral ou experimental.
3. Se for geral e pequena, trabalhar em `main` ou em branch curta com PR.
4. Se for experimental, criar branch `feat/<tema>` ou `fix/<tema>`.
5. Não misturar mudanças não relacionadas no mesmo commit.

Exemplos:

```bash
# Correto para documentação geral
git commit -m "docs(workflow): define padrao de commits"

# Correto para copy
git commit -m "fix(copywriter): corrige formato da linha de preco"

# Correto para teste
git commit -m "test(compliance): valida aviso de afiliado"
```

## Diretriz final

> O commit é a memória técnica do projeto.

Se você não consegue entender um commit depois de 30 dias, ele está errado.
