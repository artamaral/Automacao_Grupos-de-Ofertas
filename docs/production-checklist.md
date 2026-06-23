# Checklist antes de habilitar chamadas reais

Este checklist bloqueia a ativação de qualquer chamada HTTP real para marketplaces e qualquer publicação fora de dry-run.

Enquanto todos os itens obrigatórios não estiverem concluídos, `enable_real_http` e `enable_real_publish` devem permanecer `False`.

## 1. Segurança de configuração

- [ ] `.env` local criado fora do Git.
- [ ] `.env` confirmado no `.gitignore`.
- [ ] `.env.example` sem valores reais.
- [ ] Nenhuma credencial versionada em commits, issues ou logs.
- [ ] Chaves reais armazenadas apenas em ambiente local seguro.
- [ ] Rotação de credenciais planejada caso algum segredo seja exposto.

## 2. Travas de execução

- [ ] `enable_real_http=False` por padrão.
- [ ] `enable_real_publish=False` por padrão.
- [ ] Chamada real exige configuração explícita.
- [ ] Publicação real exige configuração explícita separada da chamada HTTP.
- [ ] CLI continua aceitando `--marketplace mock` como caminho seguro.
- [ ] Execuções sem transport real continuam sem chamada externa.

## 3. Logs e mensagens

- [ ] Nenhum log imprime chaves, tokens, cookies, QR code ou sessões.
- [ ] Nenhum log imprime headers de autenticação.
- [ ] Erros esperados mostram `ERRO`, `DETALHE` e `AÇÃO`.
- [ ] Traceback só aparece para erro inesperado durante desenvolvimento.
- [ ] Mensagens do CLI orientam fallback para `--marketplace mock` quando aplicável.

## 4. HTTP real

- [ ] Timeout configurado.
- [ ] Erro de rede tratado como erro amigável.
- [ ] JSON inválido tratado como erro amigável.
- [ ] Status não 2xx tratado por `ProviderHttpError`.
- [ ] Retry e rate limit avaliados antes de produção.
- [ ] Teste fake continua cobrindo o contrato do transport.
- [ ] Transport real só conectado quando `enable_real_http=True`.

## 5. Shopee

- [ ] Assinatura validada contra documentação oficial ou ambiente controlado.
- [ ] Payload real anonimizado salvo como fixture de teste.
- [ ] Mapper validado com payload real anonimizado.
- [ ] Erros de payload cobertos por `ShopeePayloadError`.
- [ ] Teste com transport fake cobre request e normalização.
- [ ] Nenhum dado sensível da Shopee aparece em logs.

## 6. Amazon

- [ ] Assinatura real da PA API implementada em módulo isolado.
- [ ] Payload real anonimizado salvo como fixture de teste.
- [ ] Mapper validado com payload real anonimizado.
- [ ] Erros de payload cobertos por `AmazonPayloadError`.
- [ ] Teste com transport fake cobre request e normalização.
- [ ] Nenhum dado sensível da Amazon aparece em logs.

## 7. Publicação

- [ ] Publicador real ainda desativado por padrão.
- [ ] Grupos de destino são opt-in.
- [ ] Mensagens incluem disclosure de afiliado.
- [ ] Compliance bloqueia publicação real quando `enable_real_publish=False`.
- [ ] Teste dry-run aprovado antes de qualquer envio real.
- [ ] Lista de destinos reais revisada manualmente.

## 8. Qualidade

- [ ] `ruff check .` sem erros.
- [ ] `pytest` sem erros.
- [ ] Testes de providers usando transport fake sem internet.
- [ ] Testes do harness cobrindo erros amigáveis.
- [ ] Documentação atualizada antes de ativação real.

## Critério de liberação

A ativação de `enable_real_http=True` só pode acontecer depois que as seções 1 a 6 estiverem concluídas.

A ativação de `enable_real_publish=True` só pode acontecer depois que todas as seções estiverem concluídas e revisadas manualmente.
