# Checklist da primeira chamada real controlada na Shopee

> Nota: este checklist registra a primeira tentativa REST/historica. Para a proxima chamada real, use `docs/checklist-operacional-pre-chamada-real.md`, que esta atualizado para Shopee GraphQL.

## Objetivo

Preparar a primeira chamada real controlada na Shopee com o menor risco possÃ­vel.

Esse checklist nÃ£o habilita publicaÃ§Ã£o real e nÃ£o altera o padrÃ£o seguro do projeto.

## PrÃ©-requisitos obrigatÃ³rios

Antes de rodar qualquer chamada real:

- [ ] `ruff check .` sem erros.
- [ ] `pytest` sem erros.
- [ ] `.env` local criado fora do Git.
- [ ] HTTP real habilitado apenas no ambiente local de teste.
- [ ] PublicaÃ§Ã£o real continua desligada.
- [ ] Base URL real da Shopee configurada fora do Git.
- [ ] Caminho do endpoint confirmado na documentaÃ§Ã£o oficial da conta Shopee usada.
- [ ] ConfiguraÃ§Ã£o obrigatÃ³ria da Shopee preenchida fora do Git.
- [ ] Preview seguro do request revisado antes da chamada.
- [ ] `--limit 1` usado na primeira execuÃ§Ã£o.
- [ ] Nenhum `--save-json` usado na primeira execuÃ§Ã£o.
- [ ] Nenhum destino real de grupo usado na primeira execuÃ§Ã£o.

## Ordem recomendada

### 1. Atualizar e validar o projeto

```text
cd C:\Automacao_Grupos-de-Ofertas
git pull
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

### 2. Confirmar endpoint oficial

Antes do diagnÃ³stico, conferir o endpoint atual em:

```text
docs/status-endpoint-shopee.md
```

O caminho atual no cÃ³digo estÃ¡ registrado como provisÃ³rio. Se o caminho oficial da conta Shopee usada for diferente, nÃ£o seguir para chamada real.

### 3. Rodar o diagnÃ³stico

```text
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --diagnose-real-http
```

SaÃ­da aprovada esperada:

```text
INFO | DiagnÃ³stico de HTTP real aprovado para marketplace=shopee
INFO | Nenhuma chamada HTTP foi executada.
INFO | Nenhuma publicaÃ§Ã£o foi executada.
INFO | Nenhum JSON foi salvo automaticamente.
```

Se esse diagnÃ³stico falhar, nÃ£o rode o preview e nÃ£o rode a chamada real.

### 4. Gerar preview seguro do request

```text
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 1 --print-provider-request
```

SaÃ­da esperada:

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
INFO | Nenhuma publicaÃ§Ã£o foi executada.
INFO | Nenhum JSON foi salvo automaticamente.
```

Antes da chamada real, conferir:

- se o mÃ©todo Ã© o esperado;
- se a URL base estÃ¡ correta;
- se o caminho do endpoint bate com o endpoint oficial;
- se `page_size` estÃ¡ em `1`;
- se `partner_id` aparece mascarado;
- se `sign` aparece mascarado;
- se nenhum valor sensÃ­vel aparece no terminal.

Se o preview estiver errado, nÃ£o rode a chamada real.

### 5. Rodar a primeira chamada controlada

```text
.\.venv\Scripts\python.exe -m ofertas_bot.harness --marketplace shopee --niche maquiagem --limit 1 --execute-real-http-once
```

SaÃ­da aprovada esperada:

```text
INFO | Chamada HTTP real controlada concluÃ­da para marketplace=shopee
INFO | Ofertas normalizadas recebidas: 1
INFO | Nenhuma publicaÃ§Ã£o foi executada.
INFO | Nenhum JSON foi salvo automaticamente.
```

## O que observar na primeira resposta

ApÃ³s a execuÃ§Ã£o, verificar:

- se houve erro HTTP;
- se houve erro de transporte;
- se houve erro de payload;
- se a quantidade de ofertas normalizadas estÃ¡ correta;
- se nenhum valor sensÃ­vel apareceu no terminal;
- se nÃ£o houve publicaÃ§Ã£o;
- se nenhum arquivo JSON foi criado automaticamente.

## Se a chamada falhar

### Falha por guarda

AÃ§Ã£o:

- revisar `.env` local;
- revisar base URL;
- revisar se HTTP real foi habilitado apenas localmente;
- rodar diagnÃ³stico novamente.

### Falha no preview

AÃ§Ã£o:

- revisar base URL configurada fora do Git;
- revisar endpoint esperado;
- revisar parÃ¢metros nÃ£o sensÃ­veis;
- nÃ£o executar chamada real atÃ© entender a diferenÃ§a.

### Falha HTTP

AÃ§Ã£o:

- revisar endpoint configurado;
- revisar status retornado;
- revisar limite/rate limit;
- nÃ£o repetir vÃ¡rias vezes sem entender o motivo.

### Falha de payload

AÃ§Ã£o:

- nÃ£o publicar;
- nÃ£o salvar payload bruto no Git;
- anonimizar a resposta antes de transformar em fixture;
- atualizar mapper/testes somente com dados seguros.

## Depois de uma chamada bem-sucedida

Se a chamada real controlada funcionar:

1. revisar a saÃ­da;
2. confirmar que nÃ£o houve vazamento de dados;
3. criar fixture anonimizada a partir do formato real;
4. validar mapper contra a fixture;
5. atualizar status de implantaÃ§Ã£o;
6. sÃ³ entÃ£o discutir aumento de `limit`.

## O que ainda continua proibido

Mesmo depois de uma chamada bem-sucedida:

- publicaÃ§Ã£o real continua proibida;
- envio para grupos continua proibido;
- salvar JSON real sem revisÃ£o continua proibido;
- commitar payload bruto continua proibido;
- aumentar volume sem revisar rate limit continua proibido.
