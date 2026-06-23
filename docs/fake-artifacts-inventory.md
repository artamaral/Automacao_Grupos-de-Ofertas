# Inventário de artefatos fake e temporários

## Objetivo

Este documento registra os artefatos fake, temporários ou de simulação usados durante a implantação.

A regra é simples:

- manter quando o artefato protege testes, segurança ou desenvolvimento local;
- tratar quando existir contrato real anonimizado ou integração validada;
- remover quando deixar de ter função prática ou virar duplicação.

## Artefatos fake atuais

| Artefato | Tipo | Motivo atual | Ação futura |
| --- | --- | --- | --- |
| `MockOfferProvider` | Provider fake | Permite testar o pipeline completo sem marketplace real. | Manter como provider de teste enquanto for útil para CI e desenvolvimento local. |
| `StaticHttpTransport` | Transport fake | Simula respostas HTTP sem internet. | Manter como utilitário de teste, mesmo após HTTP real. |
| `SequentialTransport` em testes | Transport fake local | Simula múltiplas respostas para retry e paginação. | Manter dentro dos testes; extrair para helper comum apenas se houver muita repetição. |
| Fixtures em `tests/fixtures/` | Payload fake anonimizado | Validam contrato mínimo sem dados reais. | Substituir ou complementar com fixtures reais anonimizadas quando disponíveis. |
| `docs/provider-fake-flow.md` | Documento de transição | Explica os fluxos fake/injetáveis. | Atualizar quando os providers reais forem conectados; remover se virar duplicado. |
| `docs/status-paginacao-fake.md` | Documento de transição | Registra a etapa de paginação fake criada fora do status principal. | Integrar ao status principal quando possível; remover depois da integração. |
| `docs/fake-artifacts-inventory.md` | Inventário | Centraliza o controle dos artefatos fake. | Manter enquanto houver artefatos fake relevantes. |
| `provider_settings.py` com default `https://example.com` | Configuração segura | Evita base real por padrão e contorna edição direta de settings sensíveis. | Reavaliar quando a configuração final de produção estiver definida. |
| `execute_paginated_search()` nos gateways | Fluxo fake/opcional | Permite testar paginação sem chamada real. | Manter se o desenho bater com o contrato real; adaptar ou remover se o contrato real for diferente. |
| `RetryPolicy` com sleeper fake nos testes | Simulação controlada | Permite testar retry sem espera real. | Manter como estrutura de teste e produção controlada. |

## Critérios para remover

Um artefato fake pode ser removido quando todos os critérios abaixo forem verdadeiros:

1. Existe alternativa real ou permanente coberta por testes.
2. O artefato não é mais usado por testes, CI, documentação ou desenvolvimento local.
3. A remoção não reduz segurança contra chamadas externas acidentais.
4. A remoção não dificulta reproduzir bugs localmente.

## Critérios para manter

Um artefato fake deve ser mantido quando ele:

- evita chamada externa acidental;
- facilita teste determinístico;
- ajuda a validar payloads anonimizados;
- protege contra regressão no pipeline;
- permite rodar o projeto sem credenciais reais.

## Próxima revisão sugerida

Revisar este inventário quando ocorrer qualquer uma das situações:

- entrada do primeiro payload real anonimizado;
- conexão de HTTP real controlado;
- implementação da assinatura real da Amazon;
- validação de paginação contra contrato real;
- preparação para publicação real fora de dry-run.
