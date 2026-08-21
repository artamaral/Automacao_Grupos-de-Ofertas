# Spec - Mensagens pontuais com arquivamento no n8n

## Objetivo

Adicionar um fluxo separado para mensagens estaticas pontuais do grupo
feminino, preservando o fluxo atual de mensagens estaticas recorrentes.

O problema operacional a resolver e:

- `msg_001` e `msg_002` podem ser mensagens fixas de aviso, reenviadas todos
  os dias;
- ofertas ou comunicados pontuais nao devem ser reenviados no dia seguinte;
- o historico das copies e imagens deve ser mantido;
- a regra de recorrencia nao deve ficar misturada com a regra de
  arquivamento.

## Decisao proposta

Manter dois processos independentes:

1. **Mensagens recorrentes**
   - fluxo atual;
   - nao move pastas;
   - nao apaga pastas;
   - pode reenviar `msg_001`, `msg_002` etc. diariamente;
   - usado para avisos fixos, lembretes e comunicados recorrentes.

2. **Mensagens pontuais**
   - novo fluxo;
   - envia mensagens preparadas em uma pasta de entrada propria;
   - apos envio confirmado e registro em `offers.publication_events`, move a
     pasta da mensagem para uma area de enviados;
   - usado para ofertas ou comunicados que nao devem repetir.

Essa separacao evita uma regra unica com excecoes do tipo "se for recorrente,
nao move; se for pontual, move", que aumentaria o risco operacional no fluxo
que ja esta funcionando.

## Regra de implementacao 1:1

O fluxo pontual deve ser uma copia operacional 1:1 do fluxo atual de mensagens
estaticas recorrentes, com somente estas diferencas:

1. A pasta raiz de leitura muda de `ofertas-femininas` para
   `ofertas-femininas-pendentes`.
2. O fluxo passa a localizar ou usar a pasta raiz
   `ofertas-femininas-enviados`.
3. Depois do envio e do registro em `offers.publication_events`, o fluxo move a
   pasta `msg_XXX` processada para
   `ofertas-femininas-enviados/YYYY-MM-DD/msg_XXX`.

Nao faz parte desta implementacao:

- criar outra estrategia de sequenciamento;
- trocar o formato das pastas `msg_XXX`;
- alterar o contrato `copy.txt` + `image.jpg`;
- mudar WAHA, sessao, endpoint, grupo ou allowlist;
- criar novo schema, nova tabela ou novo status;
- transformar o fluxo pontual em um seletor de todas as pastas disponiveis;
- introduzir regras condicionais de recorrente vs pontual no mesmo bloco.

Em termos praticos:

```text
Fluxo pontual = fluxo recorrente atual
  + raiz de entrada diferente
  + raiz de enviados
  + mover pasta apos registro
```

Qualquer implementacao que mude comportamento alem desses tres pontos deve ser
tratada como desvio da spec.

## Estrutura no Google Drive

Estrutura recomendada:

```text
ofertas-femininas/
  msg_001/
    copy.txt
    image.jpg
  msg_002/
    copy.txt
    image.jpg

ofertas-femininas-pendentes/
  msg_001/
    copy.txt
    image.jpg
  msg_002/
    copy.txt
    image.jpg

ofertas-femininas-enviados/
  2026-08-21/
    msg_001/
      copy.txt
      image.jpg
```

Regras:

- `ofertas-femininas/` permanece como origem das mensagens recorrentes;
- `ofertas-femininas-pendentes/` e a origem das mensagens pontuais;
- `ofertas-femininas-enviados/` preserva o historico das mensagens pontuais
  ja processadas;
- mensagens recorrentes nunca devem ser movidas para `enviados`;
- mensagens pontuais so devem ser movidas depois de envio confirmado ou apos
  uma decisao explicita de arquivar canceladas.

## Fluxo recorrente

O fluxo recorrente permanece igual ao processo atual de mensagens estaticas:

```text
Schedule Trigger
  -> resolver msg_XXX da execucao do dia
  -> buscar ofertas-femininas/msg_XXX
  -> validar copy.txt e image.jpg
  -> enviar WAHA
  -> registrar em offers.publication_events
  -> finalizar sem mover a pasta
```

Comportamento esperado:

- se `msg_001` existe hoje, ela pode ser enviada hoje;
- se `msg_001` continuar existindo amanha, ela pode ser enviada novamente;
- a idempotencia deve continuar sendo diaria;
- ausencia de pasta ou arquivo deve registrar `cancelled` e nao chamar WAHA.

## Fluxo pontual

O novo fluxo pontual deve ser independente do fluxo recorrente, mas deve
preservar a mesma sequencia funcional do bloco recorrente ja validado:

```text
Schedule Trigger
  -> resolver msg_XXX da execucao do dia
  -> buscar ofertas-femininas-pendentes/msg_XXX
  -> validar copy.txt e image.jpg
  -> baixar copy.txt e image.jpg
  -> preparar texto e imagem em base64
  -> validar allowlist
  -> enviar WAHA
  -> registrar em offers.publication_events
  -> mover pasta para ofertas-femininas-enviados/YYYY-MM-DD/
  -> registrar metadados de arquivamento no payload
```

O fluxo pontual deve usar os mesmos contratos do fluxo atual:

- mesmo tipo de `Schedule Trigger`;
- mesmo metodo de resolver `msg_XXX`, adaptado apenas para a raiz de
  pendentes;
- mesmas validacoes de pasta, `copy.txt` e `image.jpg`;
- mesma montagem de texto e imagem em base64;
- mesmo destino allowlisted;
- mesma sessao WAHA;
- mesmo endpoint WAHA;
- mesmo mecanismo de registro em `offers.publication_events`;
- nenhum segredo ou credential versionado;
- nenhuma alteracao nos nodes do fluxo legado.

A diferenca funcional obrigatoria e somente o arquivamento da pasta apos o
registro.

## Ordem segura de operacao

A ordem recomendada para mensagens pontuais e:

```text
validar arquivos
  -> consultar ledger/idempotencia
  -> enviar WAHA
  -> registrar confirmed/failed/cancelled
  -> mover pasta quando aplicavel
```

Nao mover antes do envio. Mover antes do envio reduz duplicacao, mas cria o
risco de retirar da fila uma mensagem que nunca foi publicada.

## Idempotencia

Para mensagens recorrentes:

- a mesma pasta pode ser usada em dias diferentes;
- o registro deve diferenciar a data operacional;
- `msg_001` confirmado hoje nao deve bloquear `msg_001` amanha.

Para mensagens pontuais:

- a mesma pasta nao deve ser enviada novamente depois de confirmada;
- usar o mesmo padrao de chave/idempotencia que o fluxo recorrente usa hoje,
  alterando apenas os metadados necessarios para identificar
  `static_one_shot`, a pasta de pendentes e a pasta arquivada;
- se a implementacao exigir precheck em `offers.publication_events`, esse
  precheck deve ser uma extensao minima do padrao atual, nao uma nova
  estrategia de ledger.

## Arquivamento

O arquivamento recomendado e mover a pasta inteira para:

```text
ofertas-femininas-enviados/YYYY-MM-DD/msg_XXX
```

Metadados tecnicos a registrar no `payload` existente:

- `message_flow_type`: `static_one_shot`;
- `msg_id`;
- `message_folder_id`;
- `archive_folder_id`;
- `archive_parent_id`;
- `archive_status`: `moved`, `move_failed`, `not_applicable`;
- `archive_error`, quando houver;
- resposta WAHA ja usada no fluxo atual.

Falha ao arquivar depois de envio confirmado nao deve transformar o envio em
falha. O envio e o arquivamento sao efeitos diferentes:

- envio confirmado: `delivery_status='confirmed'`;
- arquivamento falhou: registrar `archive_status='move_failed'` no `payload`
  e acionar correcao operacional.

## Cancelamentos

Mensagens pontuais devem registrar `cancelled` sem chamar WAHA quando ocorrer:

- pasta raiz de pendentes ausente ou duplicada;
- pasta `msg_XXX` ausente ou duplicada;
- `copy.txt` ausente, duplicado ou vazio;
- `image.jpg` ausente, duplicado, vazio ou com MIME type incompativel;
- destino fora da allowlist;
- mensagem ja confirmada anteriormente, se a politica for bloquear repeticao;
- falha de validacao do Google Drive.

Por padrao, pastas canceladas devem permanecer em `pendentes/` para correcao
manual. Arquivar canceladas e uma decisao separada e deve ser configurada
explicitamente.

## Agendamento

O fluxo pontual deve ter `Schedule Trigger` proprio, separado do trigger das
mensagens recorrentes.

O trigger deve seguir o mesmo desenho operacional ja usado no fluxo recorrente:

- um unico trigger para o fluxo pontual;
- multiplas regras de horario quando houver mais de uma mensagem pontual por
  dia;
- sequenciamento `1a execucao -> msg_001`, `2a execucao -> msg_002` etc.;
- nenhuma conexao com o trigger das mensagens recorrentes.

Durante teste, a execucao manual controlada pode ser usada somente como etapa
de validacao operacional. Ela nao substitui o desenho final com trigger
proprio.

Nao usar o mesmo trigger das mensagens recorrentes para o fluxo pontual.

## Harness e guard

Esta spec deve ser usada como contrato para gerar e validar o workflow. O
harness deve ser forte o suficiente para rejeitar qualquer implementacao que
pareca correta visualmente, mas mude o comportamento acordado.

O guard deve validar, no minimo:

1. Os 18 nodes legados continuam canonicos e sem alteracao funcional.
2. O fluxo recorrente de mensagens estaticas continua sem arquivamento.
3. O fluxo pontual nao tem conexao com o fluxo legado nem com o fluxo
   recorrente.
4. O fluxo pontual replica a sequencia funcional do fluxo recorrente:
   resolver `msg_XXX`, buscar pasta, validar arquivos, baixar arquivos,
   preparar payload, validar allowlist, enviar WAHA, registrar Supabase.
5. As unicas diferencas permitidas no fluxo pontual sao:
   `ofertas-femininas-pendentes`, `ofertas-femininas-enviados` e o node de
   mover pasta apos o registro.
6. Existe exatamente um `Schedule Trigger` proprio para o fluxo pontual.
7. O trigger pontual aceita multiplas regras de horario.
8. Cada execucao pontual resolve somente uma pasta `msg_XXX`.
9. Ausencia, duplicidade ou invalidade de pasta/arquivo registra `cancelled` e
   nao alcanca WAHA.
10. O node de mover pasta so pode ser alcancado depois do registro do resultado
    no Supabase.
11. O node de mover pasta nunca pode ser alcancado por caminhos de
    `cancelled`, salvo se houver decisao explicita futura para arquivar
    canceladas.
12. O envio usa o mesmo endpoint, sessao, credencial WAHA, grupo e allowlist do
    fluxo atual.
13. O JSON nao contem tokens, segredos, credential ID do Google Drive ou dados
    sensiveis.
14. O JSON final e importavel pelo n8n.

Testes obrigatorios do harness:

- mutacao em qualquer node legado deve falhar;
- conexao cruzada entre fluxos deve falhar;
- remocao ou alteracao funcional de etapa 1:1 do fluxo pontual deve falhar;
- troca de raiz `ofertas-femininas-pendentes` deve falhar;
- troca de raiz `ofertas-femininas-enviados` deve falhar;
- mover pasta antes do registro Supabase deve falhar;
- permitir WAHA em caminho `cancelled` deve falhar;
- alterar grupo, sessao, endpoint ou allowlist deve falhar;
- adicionar credential Google Drive versionada deve falhar.

## Riscos e cuidados

- **Janela de crash**: se o WAHA aceitar o envio e o n8n cair antes de registrar
  ou mover, a pasta pode continuar em `pendentes/`. Por isso a checagem no
  Supabase e mais importante que apenas mover a pasta.
- **Entrega real vs adapter**: sucesso do n8n ou aceite do WAHA nao basta como
  prova isolada; a evidencia operacional continua sendo
  `offers.publication_events`.
- **Permissao OAuth**: mover pastas exige escopo de escrita no Google Drive. Se
  a credencial foi criada apenas para leitura, sera necessario reautorizar.
- **Pasta de enviados duplicada**: o fluxo deve exigir exatamente uma pasta
  `ofertas-femininas-enviados`.
- **Pasta diaria duplicada**: criar ou localizar `YYYY-MM-DD` de forma
  deterministica e tratar duplicidade como erro operacional.
- **Concorrencia**: execucoes simultaneas podem tentar mover a mesma pasta.
  Usar ledger/idempotencia antes do WAHA e tratar `folder_not_found` no move
  como caso diagnosticavel.
- **Guard do workflow**: qualquer implementacao deve atualizar o guard e os
  testes para reconhecer o novo fluxo sem permitir alteracao nos nodes legados.

## Criterios de aceite

1. O fluxo recorrente continua sem arquivamento e sem alteracao funcional.
2. `msg_001` e `msg_002` recorrentes podem permanecer no Drive e reenviar todos
   os dias.
3. O fluxo pontual usa pasta de entrada separada.
4. O fluxo pontual e 1:1 do fluxo recorrente atual, exceto pela raiz de entrada,
   raiz de enviados e movimento final da pasta.
5. O fluxo pontual nao tem conexao com os nodes do fluxo recorrente nem com os
   18 nodes legados.
6. O fluxo pontual registra em `offers.publication_events`.
7. O fluxo pontual nao chama WAHA quando a mensagem esta ausente, duplicada ou
   invalida.
8. O fluxo pontual move a pasta somente depois do envio confirmado ou conforme
   politica explicita.
9. Falha no arquivamento nao apaga evidencia de envio confirmado.
10. O JSON versionado permanece sem tokens, segredos ou credenciais Google.
11. O guard valida a regra 1:1, ausencia de conexoes cruzadas e preservacao do
    fluxo atual.

## Fora de escopo inicial

- Apagar pastas do Drive apos envio.
- Reaproveitar o mesmo bloco de nodes com uma flag de tipo de mensagem.
- Criar novo schema, nova tabela ou novo status de publicacao.
- Alterar o fluxo atual de mensagens recorrentes.
- Usar o n8n para escolher ofertas, rankear produtos ou gerar copy.

## Commit sugerido

```text
docs(n8n): especifica fluxo pontual com arquivamento
```
