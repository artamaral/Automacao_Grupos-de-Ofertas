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
- [ ] Guarda de HTTP real integrada aos providers.
- [ ] Bloqueio da guarda de HTTP real tratado como erro amigável no harness.

## 3. Logs e mensagens

- [ ] Nenhum log imprime chaves, tokens, cookies, QR code ou sessões.
- [ ] Nenhum log imprime headers de autenticação.
- [ ] Erros esperados mostram `ERRO`, `DETALHE` e `AÇÃO`.
- [ ] Traceback só aparece para erro inesperado durante desenvolvimento.
- [ ] Mensagens do CLI orientam fallback para `--marketplace mock` quando aplicável.
- [ ] Erro de escrita do `--save-json` retorna mensagem amigável e exit code `3`.
- [ ] Aviso de `--save-json` na raiz recomenda `.data/`, `tmp/` ou `exports/`.
- [ ] Bloqueio de HTTP real inseguro retorna mensagem amigável e exit code `3`.

## 4. HTTP real

- [ ] Timeout configurado.
- [ ] Erro de rede tratado como erro amigável.
- [ ] JSON inválido tratado como erro amigável.
- [ ] Status não 2xx tratado por `ProviderHttpError`.
- [ ] Retry e rate limit avaliados antes de produção.
- [ ] Teste fake continua cobrindo o contrato do transport.
- [ ] Transport real só conectado quando `enable_real_http=True`.
- [ ] Base URL real precisa ser HTTPS.
- [ ] Base URL real não pode ser placeholder.
- [ ] Configurações obrigatórias do provider precisam estar presentes.

## 5. Retry e rate limit

- [ ] Retry permanece opcional e desligado por padrão.
- [ ] Tentativas máximas são limitadas.
- [ ] Backoff configurado e testado.
- [ ] Códigos retryable são explícitos.
- [ ] Não existe retry infinito.
- [ ] Testes usam sleeper fake para não esperar tempo real.
- [ ] Rate limit real de cada marketplace revisado antes de produção.

## 6. Paginação

- [ ] Paginação fake coberta por testes.
- [ ] Parada por `has_next_page` coberta por testes.
- [ ] Parada por página vazia coberta por testes.
- [ ] Parada por `limit` coberta por testes.
- [ ] Parada por `max_pages` coberta por testes.
- [ ] Paginação real validada contra contrato oficial antes de HTTP real.
- [ ] Payload real de paginação entra apenas como fixture anonimizada.

## 7. Persistência local

- [ ] `--save-json` continua opcional.
- [ ] Fluxo padrão não grava arquivo.
- [ ] JSON salva apenas campos normalizados de oferta.
- [ ] JSON não salva payload bruto sensível.
- [ ] Caminhos recomendados são ignorados pelo Git.
- [ ] Falha de escrita é tratada sem traceback.
- [ ] Saídas locais são revisadas antes de qualquer uso com dados reais anonimizados.

## 8. Artefatos fake e temporários

- [ ] Inventário de artefatos fake atualizado.
- [ ] Cada artefato fake tem motivo atual registrado.
- [ ] Cada artefato fake tem ação futura definida.
- [ ] Artefatos fake sem função prática são removidos.
- [ ] Artefatos fake úteis para segurança e testes são mantidos.

## 9. Shopee

- [ ] Assinatura validada contra documentação oficial ou ambiente controlado.
- [ ] Payload real anonimizado salvo como fixture de teste.
- [ ] Mapper validado com payload real anonimizado.
- [ ] Erros de payload cobertos por `ShopeePayloadError`.
- [ ] Teste com transport fake cobre request e normalização.
- [ ] Nenhum dado sensível da Shopee aparece em logs.
- [ ] Guarda de HTTP real validada para base URL e configuração da Shopee.

## 10. Amazon

- [ ] Assinatura real da PA API implementada em módulo isolado.
- [ ] Payload real anonimizado salvo como fixture de teste.
- [ ] Mapper validado com payload real anonimizado.
- [ ] Erros de payload cobertos por `AmazonPayloadError`.
- [ ] Teste com transport fake cobre request e normalização.
- [ ] Nenhum dado sensível da Amazon aparece em logs.
- [ ] Guarda de HTTP real validada para base URL e configuração da Amazon.

## 11. Publicação

- [ ] Publicador real ainda desativado por padrão.
- [ ] Grupos de destino são opt-in.
- [ ] Mensagens incluem disclosure de afiliado.
- [ ] Compliance bloqueia publicação real quando `enable_real_publish=False`.
- [ ] Teste dry-run aprovado antes de qualquer envio real.
- [ ] Lista de destinos reais revisada manualmente.

## 12. Qualidade

- [ ] `ruff check .` sem erros.
- [ ] `pytest` sem erros.
- [ ] Testes de providers usando transport fake sem internet.
- [ ] Testes do harness cobrindo erros amigáveis.
- [ ] Testes da guarda de HTTP real cobrindo bloqueios e cenário permitido.
- [ ] Documentação atualizada antes de ativação real.

## Critério de liberação

A ativação de `enable_real_http=True` só pode acontecer depois que as seções 1 a 10 estiverem concluídas.

A ativação de `enable_real_publish=True` só pode acontecer depois que todas as seções estiverem concluídas e revisadas manualmente.
