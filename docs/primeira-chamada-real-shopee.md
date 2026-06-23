# Checklist da primeira chamada real controlada na Shopee

## Objetivo

Preparar a primeira chamada real controlada na Shopee com o menor risco possível.

Esse checklist não habilita publicação real e não altera o padrão seguro do projeto.

## Pré-requisitos obrigatórios

Antes de rodar qualquer chamada real:

- [ ] `ruff check .` sem erros.
- [ ] `pytest` sem erros.
- [ ] `.env` local criado fora do Git.
- [ ] HTTP real habilitado apenas no ambiente local de teste.
- [ ] Publicação real continua desligada.
- [ ] Base URL real da Shopee configurada fora do Git.
- [ ] Caminho do endpoint confirmado na documentação oficial da conta Shopee usada.
- [ ] Configuração obrigatória da Shopee preenchida fora do Git.
- [ ] Preview seguro do request revisado antes da chamada.
- [ ] `--limit 1` usado na primeira execução.
- [ ] Nenhum `--save-json` usado na primeira execução.
- [ ] Nenhum destino real de grupo usado na primeira execução.

## Ordem recomendada

### 1. Atualizar e validar o projeto

```text
cd C:\Automacao_Grupos-de-Ofertas
git pull
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

### 2. Confirmar endpoint oficial

Antes do diagnóstico, conferir o endpoint atual em:

```text
docs/status-endpoint-shopee.md
```

O caminho atual no código está registrado como provisório. Se o caminho oficial da conta Shopee usada for diferente, não seguir para chamada real.

### 3. Rodar o diagnóstico

```text
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --diagnose-real-http
```

Saída aprovada esperada:

```text
INFO | Diagnóstico de HTTP real aprovado para marketplace=shopee
INFO | Nenhuma chamada HTTP foi executada.
INFO | Nenhuma publicação foi executada.
INFO | Nenhum JSON foi salvo automaticamente.
```

Se esse diagnóstico falhar, não rode o preview e não rode a chamada real.

### 4. Gerar preview seguro do request

```text
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 1 --print-provider-request
```

Saída esperada:

```text
INFO | Preview seguro do request da Shopee
INFO | method=GET
INFO | url=https://api.shopee.test/api/v2/product/search_item
INFO | param.keyword=maquiagem
INFO | param.page_size=1
INFO | param.partner_id=<masked:9 chars>
INFO | param.sign=<masked:64 chars>
INFO | param.timestamp=1234567890
INFO | Nenhuma chamada HTTP foi executada.
INFO | Nenhuma publicação foi executada.
INFO | Nenhum JSON foi salvo automaticamente.
```

Antes da chamada real, conferir:

- se o método é o esperado;
- se a URL base está correta;
- se o caminho do endpoint bate com o endpoint oficial;
- se `page_size` está em `1`;
- se `partner_id` aparece mascarado;
- se `sign` aparece mascarado;
- se nenhum valor sensível aparece no terminal.

Se o preview estiver errado, não rode a chamada real.

### 5. Rodar a primeira chamada controlada

```text
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 1 --execute-real-http-once
```

Saída aprovada esperada:

```text
INFO | Chamada HTTP real controlada concluída para marketplace=shopee
INFO | Ofertas normalizadas recebidas: 1
INFO | Nenhuma publicação foi executada.
INFO | Nenhum JSON foi salvo automaticamente.
```

## O que observar na primeira resposta

Após a execução, verificar:

- se houve erro HTTP;
- se houve erro de transporte;
- se houve erro de payload;
- se a quantidade de ofertas normalizadas está correta;
- se nenhum valor sensível apareceu no terminal;
- se não houve publicação;
- se nenhum arquivo JSON foi criado automaticamente.

## Se a chamada falhar

### Falha por guarda

Ação:

- revisar `.env` local;
- revisar base URL;
- revisar se HTTP real foi habilitado apenas localmente;
- rodar diagnóstico novamente.

### Falha no preview

Ação:

- revisar base URL configurada fora do Git;
- revisar endpoint esperado;
- revisar parâmetros não sensíveis;
- não executar chamada real até entender a diferença.

### Falha HTTP

Ação:

- revisar endpoint configurado;
- revisar status retornado;
- revisar limite/rate limit;
- não repetir várias vezes sem entender o motivo.

### Falha de payload

Ação:

- não publicar;
- não salvar payload bruto no Git;
- anonimizar a resposta antes de transformar em fixture;
- atualizar mapper/testes somente com dados seguros.

## Depois de uma chamada bem-sucedida

Se a chamada real controlada funcionar:

1. revisar a saída;
2. confirmar que não houve vazamento de dados;
3. criar fixture anonimizada a partir do formato real;
4. validar mapper contra a fixture;
5. atualizar status de implantação;
6. só então discutir aumento de `limit`.

## O que ainda continua proibido

Mesmo depois de uma chamada bem-sucedida:

- publicação real continua proibida;
- envio para grupos continua proibido;
- salvar JSON real sem revisão continua proibido;
- commitar payload bruto continua proibido;
- aumentar volume sem revisar rate limit continua proibido.
