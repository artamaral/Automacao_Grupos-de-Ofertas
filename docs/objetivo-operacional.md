# Objetivo e modelo operacional

Este documento define o objetivo do projeto e como ele deve ser operado. Ele
deve ser lido junto com `docs/analise-operacional.md`, que orienta as próximas
decisões de implementação.

## Objetivo do projeto

O projeto existe para construir uma ferramenta operacional própria,
automatizada, escalável e auditável de curadoria, ranqueamento e distribuição
controlada de ofertas de afiliados para grupos opt-in de WhatsApp e Telegram.

A referência funcional é o tipo de operação feita por plataformas de automação
para afiliados, mas o objetivo deste projeto não é criar um SaaS, vender acesso
para terceiros ou administrar clientes externos. O objetivo é operar uma esteira
própria de afiliados, com controle sobre fontes, grupos, critérios, mensagens,
aprovação e envio.

O sistema deve consultar APIs de marketplaces e fontes de ofertas. Hoje o
projeto considera Shopee e Amazon, mas a arquitetura deve assumir crescimento
para novos providers. Cada integração precisa ficar isolada, configurável,
testável e substituível, sem acoplar o fluxo principal a uma única API.

A partir de parâmetros definidos, como nicho, marketplace, limite de ofertas,
grupo de destino, desconto mínimo, comissão, reputação, vendas, frete,
aderência ao público e regras de qualidade, o sistema deve coletar ofertas e
cupons, normalizar os dados recebidos e criar uma lista ranqueada de
oportunidades.

Quando existir taxonomia de subgrupos, ela deve apoiar escopo, catalogação e
roteamento, mas não obrigatoriamente limitar a coleta principal. O fluxo alvo
deve aceitar coleta ampla por macro-nicho e classificação posterior por
subgrupo, para que o sistema descubra mais ofertas úteis antes de decidir para
qual grupo cada item deve seguir.

Até que existam dados reais suficientes, essa taxonomia deve ser tratada como
estrutura inicial de escopo e catalogação, não como regra fechada de decisão.
Classificação, roteamento e ponderação fina de score dependem da observação da
saída real da API e do comportamento real das ofertas coletadas.

Esse ranking determina quais ofertas têm qualidade suficiente para avançar no
fluxo. Cada oferta selecionada deve ter justificativas claras para sua escolha,
permitindo auditoria, revisão humana e melhoria contínua dos critérios de
decisão.

Além de divulgar produtos, o sistema deve capturar e enviar cupons
disponibilizados diariamente pelas plataformas, quando eles existirem e forem
compatíveis com o nicho ou grupo de destino. Cupons devem entrar no mesmo fluxo
de decisão: origem, validade, regras, aderência ao grupo, mensagem e auditoria.

Depois da seleção, o sistema deve gerar mensagens prontas para envio em grupos
de WhatsApp e Telegram. As mensagens devem ser claras, curtas, variadas,
compatíveis com regras de afiliado e conter aviso transparente de comissão. A
geração de mensagem deve adaptar a comunicação ao grupo, ao nicho e ao contexto
da campanha, não apenas copiar os dados brutos da oferta.

O projeto também deve gerar mensagens humanizadas e contextuais, não apenas
mensagens de produto. Exemplos:

- mensagem de boas-vindas explicando o nicho do grupo;
- explicação do tipo de oferta que o grupo receberá;
- aviso sobre quais marketplaces serão usados;
- chamada diária sobre cupons disponíveis;
- resumo do que está acontecendo em uma campanha;
- mensagem de pausa, retomada ou mudança de foco do grupo;
- avisos sobre critérios de seleção e transparência de afiliado.

Essas mensagens serão refinadas "on the go", conforme o comportamento dos
grupos, a qualidade das ofertas, o feedback humano e os resultados observados.

No início, todas as mensagens devem passar por revisão humana antes de qualquer
envio real. Essa revisão serve para validar qualidade das ofertas, tom das
mensagens, segurança operacional e aderência às regras dos canais. Conforme o
sistema ganhar confiança por meio de testes, histórico e métricas, partes do
fluxo poderão ser automatizadas de forma gradual.

A publicação real só deve acontecer quando houver aprovação explícita,
configuração segura, canal permitido, grupo opt-in e logs auditáveis. O projeto
deve evitar qualquer automação que burle políticas, limites ou mecanismos de
proteção das plataformas.

## Escopo atual

O escopo atual é um MVP local em dry-run. Ele permite validar a lógica de
coleta, seleção, copy, compliance e revisão sem depender de credenciais reais,
sem chamar APIs externas automaticamente e sem enviar mensagens reais.

Estão dentro do escopo atual:

- provider `mock` para ponta a ponta;
- providers Shopee e Amazon com contratos fake/injetáveis;
- geração de lista normalizada de ofertas;
- pontuação por desconto, comissão, vendas, avaliação e frete;
- geração de mensagens com aviso de afiliado;
- validação de compliance;
- fila local de revisão;
- exportação de mensagens aprovadas;
- manifesto e bundle local para auditoria;
- testes automatizados e fluxo local reprodutível.

Estão fora do escopo atual:

- publicação real em grupos;
- chamada HTTP real sem aprovação explícita;
- uso de credenciais, tokens, cookies, QR codes ou sessões no repositório;
- automação para contornar políticas, limites ou detecção de plataformas;
- criação de novos CLIs pequenos que não simplifiquem o fluxo principal.

## Modelo operacional alvo

O fluxo alvo deve ser simples o bastante para ser chamado por automação,
agendador ou orquestrador:

```text
APIs de ofertas
  -> Normalização dos dados
  -> Classificação por subgrupo/categoria
  -> Coleta de cupons diários
  -> Aplicação de parâmetros e critérios
  -> Ranking de ofertas
  -> Roteamento para grupos elegíveis
  -> Seleção das melhores oportunidades
  -> Geração de mensagens de produto, cupom e contexto
  -> Revisão humana
  -> Aprovação
  -> Disparo controlado para WhatsApp/Telegram
  -> Registro e auditoria
```

A operação humana deve ficar restrita a decisões que realmente exigem contexto
ou responsabilidade:

- aprovar ou rejeitar mensagens;
- configurar credenciais fora do Git;
- liberar travas de HTTP real ou publicação real quando o checklist permitir;
- validar localmente o comportamento antes de avançar de fase.

O operador não deve precisar executar uma sequência longa de scripts pequenos
para concluir o fluxo diário.

## Decisao operacional atual sobre horizontalizacao

Os perfis operacionais `mae-e-bebe`, `feminino` e `auto-e-moto` passam a
compartilhar o mesmo fluxo de execucao, o mesmo contrato de artefatos e o mesmo
comportamento default. Quando uma capacidade compartilhada avancar em um
profile, ela deve avancar nos tres no mesmo bloco.

Regra obrigatoria:

- a operacao diaria deve mudar apenas o valor de `--profile`;
- diferencas de negocio devem ficar somente em configuracao versionada;
- nao deve existir desvio de implementacao por nicho no pipeline principal.

Config que pode variar por profile:

- `config/discovery_profiles.toml`: catalogo curado, contexto e limite;
- `config/selection_profiles.toml`: bandas por subnicho e teto de itens sem venda;
- `config/group_profiles.toml`: roteamento dos grupos.

Contrato comum atual:

- Shopee como marketplace operacional;
- catalogo curado `ratingStar >= 4.8` por niche;
- selecao default de `20` itens por rodada;
- no maximo `4` itens sem venda por rodada;
- template estatico compartilhado da Shopee;
- compliance obrigatorio;
- render automatico de preview HTML.

## Decisão operacional atual sobre contas por nicho

Para organizar a operação desde o início, o projeto passa a considerar a
segregação por nicho também no nível de identidade operacional.

Decisão registrada:

- usar contas de email separadas por nicho principal;
- evitar misturar credenciais, aprovações e histórico entre nichos diferentes;
- preparar o projeto para operar múltiplos contextos de publicação no futuro,
  mesmo sem frontend ou banco nesta fase.

Contas atualmente reservadas:

1. feminino
2. mãe e bebê
3. auto e moto
4. achadinhos geral

Implicações práticas desta decisão:

- cada nicho pode evoluir com credenciais, grupos, sessões e aprovações
  próprias;
- integrações futuras com WhatsApp, Telegram, n8n e marketplaces devem assumir
  isolamento por nicho quando houver credenciais distintas;
- logs, manifests e artefatos locais devem sempre deixar claro a qual nicho ou
  perfil operacional pertencem;
- nenhuma credencial, sessão, cookie, QR code ou segredo dessas contas deve ser
  versionado no repositório;
- essa separação não entra na descoberta neste momento; os perfis de descoberta
  devem continuar focados apenas em filtros de coleta e seleção.

Nesta fase, essa separação ainda é documentada e tratada por configuração
versionada. No futuro, se a operação crescer, ela poderá migrar para uma camada
administrativa mais estruturada sem mudar a regra de negócio.

## Métodos e recursos necessários

O projeto deve evoluir com uma separação clara entre recursos internos,
serviços externos e pontos de decisão humana.

### Banco de dados

O projeto deve precisar de banco de dados quando sair do MVP local em JSON. O
banco será necessário para persistir:

- offers coletadas e normalizadas;
- cupons coletados, regras de uso e validade;
- rankings gerados por execução;
- parâmetros usados na seleção;
- mensagens geradas;
- status de revisão humana;
- histórico de disparos;
- grupos, canais e regras de elegibilidade;
- perfil de cada grupo, incluindo nicho, marketplaces aceitos, tom de mensagem
  e limites operacionais;
- métricas de entrega, aprovação, rejeição e performance;
- logs auditáveis sem segredos.

Direção sugerida: começar com uma modelagem simples e migrável, mantendo JSON
apenas como artefato local/debug. A decisão entre SQLite, PostgreSQL ou outro
serviço deve considerar volume, automação e necessidade de operação em cloud.

### Orquestração e automação

O n8n pode ser usado como camada de automação para chamar o fluxo principal,
agendar execuções, conectar aprovações humanas e integrar serviços externos.

Possíveis responsabilidades do n8n:

- disparar execuções por agenda, nicho ou grupo;
- chamar uma API ou comando do projeto para gerar ofertas e mensagens;
- enviar itens para revisão humana;
- receber decisão de aprovação ou rejeição;
- acionar o envio controlado após aprovação;
- registrar resultado em banco ou planilha operacional;
- alertar falhas e bloqueios.

O n8n não deve conter regra de negócio central de ranking, compliance ou copy.
Essas regras devem continuar no projeto para serem testáveis, versionadas e
reutilizáveis.

Além disso, quando a automação evoluir, o n8n deve considerar a segregação por
nicho como contexto de execução. Isso significa que fluxos, credenciais,
aprovações e destinos podem variar por identidade operacional, e não apenas por
provider ou grupo.

### APIs de ofertas

As APIs de marketplaces devem ser tratadas como providers. Hoje existem Shopee
e Amazon, mas o desenho precisa aceitar novos providers sem reescrever o fluxo.

Cada provider deve ter:

- configuração própria;
- autenticação isolada;
- cliente/gateway testável;
- mapper para `Offer`;
- tratamento de erro padronizado;
- limite e paginação controlados;
- logs seguros;
- testes com transport fake e fixtures anonimizadas.

HTTP real deve permanecer bloqueado até haver credenciais, contrato validado,
payload anonimizado, checklist aprovado e proteção contra vazamento de dados
sensíveis.

#### Amazon como provider restrito

A Amazon deve ser tratada como provider restrito enquanto a conta não tiver
elegibilidade para uso oficial da Creators API. A regra operacional conhecida é
que, além de conta de criador aprovada, pode ser necessário atingir pelo menos
10 vendas qualificadas nos últimos 30 dias para acessar a PA API por meio da
Creators API. Essa condição deve ser confirmada dentro do painel/conta usada
antes de qualquer implementação real.

Enquanto a elegibilidade não existir, o projeto não deve depender da Amazon API
para operar. A estratégia recomendada é:

1. manter `AmazonProvider` em modo mock/fake para contrato interno e testes;
2. permitir entrada manual ou curada de ofertas e cupons Amazon, quando houver
   links válidos gerados por meios permitidos da conta;
3. ranquear, gerar mensagem, revisar e enviar essas ofertas pelo mesmo fluxo dos
   demais providers;
4. avaliar scraping apenas como alternativa experimental de alto risco, se for
   permitido e operacionalmente seguro;
5. migrar para Creators API oficial quando a conta atender aos requisitos.

Qualquer avaliação de scraping para Amazon deve obedecer a limites rígidos:

- não burlar captcha, autenticação, bloqueios, detecção ou rate limits;
- não versionar cookies, sessões, tokens, QR codes ou credenciais;
- não usar scraping agressivo ou volume alto;
- isolar a implementação atrás de um provider próprio;
- registrar origem, data de captura e limitações da informação;
- manter fallback manual/curado;
- exigir aprovação explícita antes de uso real.

Scraping não deve ser o caminho principal da Amazon; ele só pode ser estudado
como ponte temporária, controlada e reversível até a API oficial ficar viável.

### API de envio de mensagens

O envio para WhatsApp e Telegram deve ficar atrás de providers de publicação,
assim como as APIs de ofertas ficam atrás de providers de coleta.

O projeto deve considerar:

- Telegram Bot API ou provider equivalente permitido;
- WhatsApp Cloud API ou outro provider oficial/permitido como referência
  segura;
- alternativa não oficial para WhatsApp somente como decisão pendente de risco,
  motivada por inviabilidade econômica da cobrança por mensagem na API oficial;
- controle de grupos/canais autorizados;
- rate limit e janela de envio;
- logs de tentativa, sucesso e falha;
- idempotência para evitar mensagens duplicadas;
- bloqueio quando `ENABLE_REAL_PUBLISH=false`;
- aprovação humana obrigatória no início.

Decisão pendente sobre WhatsApp:

- a API oficial do WhatsApp pode não fechar a conta econômica do projeto por
  cobrança por mensagem;
- por esse motivo, o uso de biblioteca não oficial pode ser avaliado como
  alternativa operacional;
- essa alternativa não está liberada para produção nesta fase;
- qualquer biblioteca não oficial deve ficar isolada atrás de um
  `PublisherProvider`, nunca misturada ao fluxo principal;
- nenhum segredo, sessão, cookie, QR code ou token pode ser versionado;
- envio real continua bloqueado por `ENABLE_REAL_PUBLISH=false`;
- antes de qualquer uso real, a decisão precisa registrar riscos de bloqueio,
  instabilidade, termos de uso, manutenção, segurança e perda de canal;
- o sistema deve manter fallback para Telegram ou outro canal permitido caso o
  WhatsApp não oficial seja bloqueado ou se torne inviável.

Não deve existir implementação para contornar mecanismos de proteção,
detecção, limites ou políticas das plataformas. Se uma alternativa não oficial
for testada, ela deve ser tratada como integração de alto risco, auditável,
reversível e sempre dependente de aprovação humana explícita.

### GPT e geração de mensagens

O GPT pode ser usado para melhorar a formatação e variação das mensagens, mas
deve operar dentro de contratos claros.

Uso esperado:

- adaptar a mensagem ao nicho e ao perfil do grupo;
- variar a linguagem sem mudar fatos da oferta;
- manter texto curto e claro;
- incluir disclosure de afiliado;
- evitar urgência falsa;
- evitar promessa de preço permanente;
- gerar alternativas para revisão humana.

O GPT não deve decidir sozinho se uma oferta é válida, alterar preço, inventar
benefícios ou remover avisos obrigatórios. A saída deve passar por compliance e
revisão humana enquanto o sistema ainda não tiver confiança operacional.

### Revisão humana

A revisão humana é parte do produto no início, não uma etapa improvisada.

Ela deve permitir:

- aprovar mensagem;
- rejeitar mensagem;
- registrar motivo de rejeição;
- revisar oferta e texto juntos;
- preservar histórico para melhorar ranking e copy;
- bloquear envio quando houver pendências.

Com histórico suficiente, o sistema pode automatizar casos de baixo risco, mas
sempre mantendo trilha de auditoria e possibilidade de bloqueio manual.

### Observabilidade e auditoria

O projeto deve registrar o suficiente para explicar decisões e investigar
problemas sem expor segredos.

Devem ser rastreados:

- execução;
- provider usado;
- parâmetros de entrada;
- ofertas coletadas;
- score e motivos;
- mensagem gerada;
- resultado de compliance;
- decisão humana;
- tentativa de envio;
- resultado do envio;
- erros e bloqueios.

Logs não devem conter tokens, chaves, cookies, QR codes, sessões ou payloads
sensíveis não anonimizados.

### Configuração e segredos

Credenciais e parâmetros sensíveis devem ficar fora do Git. O projeto deve usar
variáveis de ambiente, `.env` local ignorado e, no futuro, secret manager do
ambiente de execução.

As travas principais continuam obrigatórias:

- `ENABLE_REAL_HTTP=false` por padrão;
- `ENABLE_REAL_PUBLISH=false` por padrão;
- confirmação explícita antes de qualquer chamada ou envio real.

### Recursos ainda pendentes de decisão

Antes de produção, ainda precisam ser definidos:

- banco definitivo para histórico operacional;
- formato da API interna que o n8n ou outro orquestrador chamará;
- providers oficiais de WhatsApp e Telegram;
- interface ou processo de revisão humana;
- política de score mínimo por grupo/nicho;
- frequência de execução por grupo;
- limites de mensagens por canal;
- modelo de métricas para medir confiança e liberar automação gradual;
- estratégia de deploy e secret manager.

## Método proposto de implementação

O método recomendado é evoluir o projeto por camadas, mantendo a regra de
negócio no código Python e usando ferramentas externas apenas para orquestração,
armazenamento, geração assistida ou entrega.

Princípio central:

```text
Python decide
Banco registra
n8n orquestra
GPT redige dentro de limites
Providers enviam
Humano aprova até haver confiança
```

### 1. Consolidar serviços internos

Antes de ampliar integrações externas, o projeto deve separar o fluxo principal
em serviços internos reaproveitáveis:

- serviço de coleta/comunicação com providers de ofertas;
- serviço de ranking e seleção de ofertas;
- serviço de geração de mensagens;
- serviço de compliance;
- serviço de revisão/aprovação;
- serviço de publicação, inicialmente apenas dry-run.

Esses serviços devem poder ser chamados por CLI, API interna, teste automatizado
ou orquestrador futuro sem duplicar regra de negócio.

### 2. Definir modelo de dados mínimo

O banco deve entrar quando o projeto precisar sair do JSON local. A primeira
modelagem deve ser mínima e voltada para operação:

- `providers`: fontes de ofertas configuradas;
- `offers`: ofertas normalizadas;
- `coupons`: cupons coletados por provider, validade e regras;
- `manual_offer_inputs`: ofertas e cupons inseridos manualmente ou por curadoria
  enquanto um provider oficial não estiver disponível;
- `ranking_runs`: execuções de ranking;
- `ranked_offers`: score, motivos e posição de cada oferta;
- `message_drafts`: mensagens geradas;
- `group_profiles`: nicho, canais, marketplaces aceitos, tom e limites por grupo;
- `review_items`: status de aprovação humana;
- `delivery_targets`: grupos/canais autorizados;
- `delivery_attempts`: tentativas e resultado de envio;
- `audit_events`: eventos relevantes sem segredos.

Essa modelagem deve permitir responder perguntas simples: qual oferta foi
coletada, por que foi ranqueada, qual mensagem foi gerada, quem aprovou e se o
envio aconteceu.

### 3. Criar API interna para automação

O fluxo não deve depender de humanos executando vários comandos. A evolução
natural é expor uma API interna ou camada de serviço que o n8n possa chamar.

Endpoints ou operações esperadas:

- gerar ranking por nicho, provider e grupo;
- listar cupons diários compatíveis com grupo ou nicho;
- gerar mensagens a partir de ofertas selecionadas;
- gerar mensagens contextuais de grupo, campanha ou cupom;
- listar itens pendentes de revisão;
- aprovar ou rejeitar item;
- consultar status de execução;
- solicitar envio controlado de itens aprovados.

Essa API interna deve manter as travas de segurança do projeto. O n8n não deve
conseguir publicar nada se o projeto bloquear.

### 4. Usar n8n como orquestrador

O n8n deve coordenar o fluxo, não substituir o sistema. Ele pode:

- agendar execuções por nicho, grupo ou horário;
- chamar a API interna do projeto;
- encaminhar mensagens para revisão humana;
- receber decisões de aprovação ou rejeição;
- acionar envio controlado após aprovação;
- registrar status em banco;
- emitir alertas de falha.

Ranking, compliance, critérios de qualidade e regras de publicação devem ficar
no projeto Python, com testes e versionamento.

### 5. Implementar revisão humana como produto

A revisão humana deve ser tratada como parte oficial do método, especialmente no
início. Ela deve validar:

- qualidade da oferta;
- coerência do ranking;
- tom da mensagem;
- presença de disclosure;
- adequação ao grupo;
- risco de envio.

O histórico de aprovação e rejeição deve alimentar ajustes futuros de score,
copy e automação gradual.

### 6. Introduzir GPT com contrato fechado

O GPT deve ser usado depois que a estrutura de mensagem estiver clara. Ele deve
receber dados estruturados e devolver texto dentro de limites.

Entrada esperada:

- título da oferta;
- preço e preço anterior;
- desconto;
- cupom disponível, quando existir;
- marketplace;
- link;
- motivos do score;
- nicho;
- perfil do grupo;
- objetivo da mensagem: produto, cupom, boas-vindas, resumo ou aviso;
- restrições de compliance.

Saída esperada:

- uma ou mais variações de mensagem;
- mensagem adaptada ao nicho e ao momento do grupo;
- sem inventar preço, benefício ou disponibilidade;
- com aviso de afiliado;
- sem urgência falsa;
- adequada para revisão humana.

Compliance continua obrigatório após a geração.

### 7. Implementar publishers por canal

Telegram e WhatsApp devem ser implementados como providers de publicação. O
contrato do sistema deve ser o mesmo, independentemente do canal:

```text
MessageDraft aprovado + destino autorizado -> tentativa de envio -> resultado auditável
```

Ordem sugerida:

1. manter `DryRunPublisher`;
2. criar `TelegramPublisher` com API permitida;
3. avaliar `WhatsAppPublisher` com biblioteca não oficial apenas após decisão
   de risco registrada;
4. manter fallback entre canais;
5. adicionar idempotência para evitar duplicidade.

### 8. Controlar escala com fila, limites e idempotência

Quando houver múltiplos providers, grupos e horários, o projeto deve evitar
execução síncrona simples para tudo. A arquitetura deve prever:

- fila de execuções;
- worker ou job runner;
- limite por provider;
- limite por grupo;
- janela de envio;
- retentativas controladas;
- chave idempotente por oferta, grupo e campanha;
- bloqueio de duplicidade.

Esses recursos devem ser adicionados quando o volume justificar, não antes.

### 9. Medir confiança antes de automatizar

A automação de envio deve aumentar apenas com evidência. Métricas mínimas:

- taxa de aprovação humana;
- taxa de rejeição por motivo;
- falhas de provider;
- mensagens bloqueadas por compliance;
- duplicidades evitadas;
- performance por grupo quando houver dados disponíveis;
- incidentes ou bloqueios de canal.

Enquanto a confiança for baixa, o padrão deve ser revisão humana obrigatória.

### 10. Evoluir para produção por fases

Fases recomendadas:

1. MVP local com mock, JSON e dry-run;
2. serviços internos claros e testáveis;
3. banco de dados mínimo;
4. API interna para automação;
5. n8n orquestrando execução e revisão;
6. Telegram real controlado;
7. avaliação de WhatsApp não oficial com aceite de risco;
8. métricas e automação gradual;
9. múltiplos providers de ofertas em escala.

Cada fase deve manter testes, logs seguros, segredos fora do Git e travas de
HTTP/envio real.

## Fluxo operacional atual

O comando principal atual é o orquestrador local:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage prepare --niche maquiagem --marketplace mock --target grupo-maquiagem
```

A etapa `prepare`:

- carrega ofertas em modo seguro a partir da base operacional disponivel;
- pontua as ofertas;
- gera mensagens;
- valida compliance;
- salva ofertas, mensagens e fila de revisão em `.data`;
- não envia nada;
- não chama publicação real.

Decisao operacional atual para catalogo:

- a geracao ampla de catalogo nao faz parte do fluxo automatizado principal;
- essa geracao pode ser longa e exige revisao posterior de score efetivo,
  porque preco, prazo, comissao e outras condicoes podem mudar;
- por isso, o pipeline principal nao deve depender de reexecutar descoberta
  completa a cada rodada;
- o `Collector` do fluxo principal deve passar a consumir o catalogo curado
  como entrada operacional.

Depois da revisão humana ou de uma interface externa alterar a fila para
`approved` ou `rejected`, a etapa final consolida os artefatos:

```powershell
.\.venv\Scripts\python.exe -m ofertas_bot.local_flow_cli --stage finalize --target grupo-maquiagem
```

A etapa `finalize`:

- bloqueia se ainda houver itens pendentes;
- exporta somente mensagens aprovadas;
- cria manifesto local;
- valida manifesto;
- cria bundle local de auditoria;
- executa doctor local;
- não envia nada;
- não chama publicação real.

## Contratos principais

O sistema deve preservar contratos internos simples:

- `Offer`: oferta normalizada recebida de mock, Shopee, Amazon ou outro provider;
- `ScoredOffer`: oferta pontuada com justificativas;
- `MessageDraft`: mensagem gerada a partir de uma oferta;
- `ComplianceResult`: aprovação ou bloqueio antes de publicar;
- artefatos JSON locais: saída auditável para revisão, debug e orquestração.

Novas implementações devem fortalecer esses contratos, não criar formatos
paralelos sem necessidade.

## Critérios para evoluir o projeto

Uma mudança nova deve ser priorizada quando ajudar diretamente um destes pontos:

- simplificar a comunicação com APIs de ofertas;
- tornar a lista de ofertas selecionadas mais clara;
- tornar a geração de mensagens mais clara e reaproveitável;
- reduzir comandos e artefatos soltos no fluxo principal;
- aumentar segurança, testes ou rastreabilidade sem expandir o escopo real.

Mudanças que adicionam auditorias, manifests, doctors ou CLIs auxiliares devem
ser adiadas, salvo correção de bug ou manutenção necessária.

## Próxima direção

A próxima direção técnica deve ser consolidar o fluxo principal em camadas
operacionais reaproveitáveis:

1. serviço de comunicação/coleta com entrada e saída simples;
2. serviço de geração de lista de ofertas selecionadas;
3. serviço de geração de mensagens com compliance obrigatório;
4. orquestrador local chamando essas camadas com poucos parâmetros.

Somente depois disso o projeto deve retomar persistência mais robusta, payloads
reais anonimizados, HTTP real controlado e publicação real.
