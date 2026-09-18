# Spec — Overlay Dinâmico para Reels com ASS + FFmpeg + n8n

**Status:** rascunho revisado — contrato VPS/n8n parcialmente definido
**Escopo:** geração do overlay textual/visual de Reels de ofertas, seleção aleatória de template, adaptação à duração do vídeo e normalização de resolução antes da renderização.

## Decisões desta revisão

- O n8n continua sendo o orquestrador. Um script executado na VPS recebe o
  job, gera o ASS, renderiza o MP4 e devolve ao n8n a referência do arquivo.
- O fluxo atual de seleção, publicação, credenciais, dry-run, allowlist e
  registro permanece inalterado. A renderização apenas prepara o vídeo que o
  fluxo atual já publica.
- `template_id` é metadado obrigatório do processamento e da publicação.
- O overlay pode terminar alguns centésimos antes do fim do vídeo; não é
  necessário perseguir o último frame.
- `testeFonte.ass` é referência visual/técnica fornecida pelo usuário, não uma
  instrução operacional nem um arquivo a ser versionado automaticamente.
- Os vídeos atuais são produzidos para consumo em celular no ecossistema da
  Shopee e as publicações observadas mantêm posicionamento adequado.
- O enquadramento vertical original deve ser preservado. A normalização para
  `1080x1920` só deve alterar a geometria quando necessário; não aplicar crop
  adicional em vídeos verticais adequados.
- `COVER + CROP CENTRAL` fica somente como fallback para diferenças de
  proporção que impeçam a saída obrigatória.
- A seleção do candidato para cada horário permanece exatamente conforme o
  fluxo atual: não reservar nem atribuir candidatos a horários durante o
  pré-render. O pré-render é preparado para consumo posterior por `item_id`.
- O primeiro horário de publicação é 10:00 BRT; o job independente de
  preparação está previsto para 09:00 BRT e encerra normalmente quando não há
  itens disponíveis no `daily_dispatch_plan`.
- A chave para localizar o artefato pré-renderizado é `item_id`. Ela não
  substitui `source_dispatch_plan_id`, que continua identificando o slot/plano
  de publicação e sua auditoria. O manifesto do MP4 carrega os dois valores e
  valida que o `item_id` pertence ao `dispatch_plan_id` consultado.
- Aceita-se o baixo risco de o preço embutido no vídeo refletir o dado obtido
  pela manhã, mesmo que mude durante o dia; não haverá re-render por horário.
- A limpeza diária terá como alvo 00:00 BRT (GMT-3), removendo somente jobs
  concluídos e artefatos que não estejam em uso.

## 1. Objetivo

Implementar uma etapa de geração de criativo em vídeo na qual o **n8n apenas orquestra e seleciona uma das 10 variações visuais**, enquanto um gerador monta dinamicamente um arquivo `.ass` compatível com FFmpeg/libass.

O overlay deve:

- funcionar para vídeos de durações diferentes;
- repetir iterativamente a composição escolhida até o fim real do vídeo;
- exibir o preço durante todo o vídeo;
- alternar os textos/CTAs conforme o template sorteado;
- manter `QUERO` sempre em maiúsculas;
- suportar vídeos cuja resolução/orientação não seja 1080x1920;
- produzir sempre uma saída final 1080x1920, adequada ao formato vertical de Reels;
- manter a lógica de design fora do n8n: o workflow escolhe o `template_id`, mas não monta individualmente cores, posições ou animações.

## 2. Responsabilidades

### 2.1 n8n

O n8n é responsável por:

1. receber/localizar o vídeo de entrada;
2. na preparação independente das 09:00, consultar os itens do
   `daily_dispatch_plan` do dia e formar jobs para os que têm mídia resolvida,
   fornecendo `item_id`, preço do refresh, URL de origem e contexto do plano;
3. ler do Google Drive o arquivo ASS de produção;
4. fornecer ao script da VPS:
   - preço;
   - `template_id`;
   - referência do vídeo de entrada;
   - conteúdo ou binário do ASS lido do Drive;
5. encaminhar o vídeo e o ASS à VPS conforme o contrato do serviço;
6. receber status, resultado e logs sanitizados do render;
7. selecionar aleatoriamente um `template_id` entre 1 e 10 por job de
   pré-render e preservá-lo no artefato;
8. no horário de publicação, executar a seleção de candidato atual sem
   alteração e localizar o artefato correspondente por `item_id`;
9. se o artefato não existir ou não estiver pronto, manter o vídeo original;
   falhas de render têm uma tentativa inicial e um retry (duas tentativas no
   total), sem bloquear a publicação;
10. preservar resultado, `item_id`, `template_id` e logs sanitizados no evento
    de publicação existente.

O n8n **não deve calcular manualmente posições, cores, fontes, animações,
duração ou dimensões**. Essas regras e leituras pertencem ao script da VPS e
à definição dos templates.

### 2.2 Gerador de ASS

O gerador é responsável por:

- carregar a definição do template selecionado;
- gerar os estilos `[V4+ Styles]`;
- calcular todos os intervalos de tempo em função da duração real;
- criar os eventos `[Events]` até próximo do término do vídeo;
- impedir eventos com `Start >= End`;
- encerrar o último evento no máximo `0,10 s` antes do término do vídeo;
- escrever o arquivo ASS em UTF-8.

### 2.3 FFmpeg

O FFmpeg é responsável por:

- normalizar resolução/aspect ratio do vídeo;
- renderizar o `.ass` usando libass;
- utilizar as fontes necessárias;
- gerar o MP4 final.

### 2.4 Script de renderização na VPS

O script deve ser o único executor de `ffprobe`, gerador ASS e FFmpeg. Deve
executar cada job em diretório isolado e retornar ao n8n um resultado
estruturado. O contrato mínimo proposto é:

```json
{
  "status": "succeeded",
  "template_id": 4,
  "artifact_url": "https://.../rendered.mp4",
  "artifact_mime_type": "video/mp4",
  "duration_seconds": 51.2,
  "width": 1080,
  "height": 1920,
  "source_width": 720,
  "source_height": 1280,
  "render_engine": "ffmpeg"
}
```

Em caso de falha, retornar `status: "failed"`, um código estável e uma
mensagem/log sanitizado, sem segredos ou caminhos sensíveis. A VPS não decide
se o Reel será publicado: depois de esgotar a tentativa inicial e um retry, o
n8n usa o vídeo original como fallback.

## 3. Formato visual padrão

### 3.1 Canvas lógico

Todos os templates utilizam o mesmo canvas ASS:

```text
PlayResX: 1080
PlayResY: 1920
```

As posições do overlay são definidas nesse sistema de coordenadas, independentemente da resolução original do vídeo.

### 3.2 Área principal dos overlays

Referência atual:

- CTA principal: região de `y = 1660`;
- preço: região de `y = 1810`;
- centro horizontal padrão: `x = 540`;
- preço exibido durante toda a duração do vídeo.

Esses valores fazem parte do template base e podem variar individualmente quando a animação exigir, mas o resultado deve permanecer dentro da mesma região visual inferior.

## 4. Fontes

São utilizadas duas fontes:

- `Smithen`: textos manuscritos/CTAs;
- `Happy Camper`: preço e, nos templates 01 e 02, `QUERO` isolado.

As fontes devem existir no ambiente que executa FFmpeg/libass. Não é suficiente que estejam instaladas apenas no computador usado para editar/testar no Aegisub.

O nome utilizado no ASS deve corresponder ao nome interno reconhecido pela fonte:

```text
Smithen
Happy Camper
```

## 5. Placeholder do preço

Durante geração/teste:

```text
R$ XX.XX
```

Em produção o gerador recebe o preço real e substitui esse placeholder.

O preço:

- permanece visível durante todo o vídeo;
- utiliza `Happy Camper`;
- fica na região inferior;
- possui caixa colorida conforme o template;
- deve preservar contraste mínimo entre texto e fundo.

## 6. Regra de seleção do template

Existem exatamente 10 templates habilitados nesta versão.

O sorteio é uniforme e sem peso:

```javascript
const templateId = Math.floor(Math.random() * 10) + 1;
```

Faixa válida:

```text
1..10
```

Não há, nesta versão, regra adicional de histórico, peso, performance ou bloqueio de repetição consecutiva. O objetivo é manter o workflow simples.

O `template_id` selecionado deve ser preservado no contexto do job e no
`payload` de `offers.publication_events`. Esta spec não cria uma nova tabela ou
um novo mecanismo de logging.

## 7. Regra de duração e geração iterativa

A duração do ASS **nunca deve ser fixa**.

Antes da geração, obter a duração real do vídeo via `ffprobe`:

```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 input.mp4
```

Exemplo:

```text
51.200000
```

### 7.1 Unidade de geração

O template é dividido em duas fases de CTA:

- `phase_a`;
- `phase_b`.

Valor padrão de cada fase:

```text
1.40 s
```

Portanto um ciclo completo do template possui:

```text
2.80 s
```

O gerador repete:

```text
A -> B -> A -> B -> A -> B ...
```

até atingir a duração real do vídeo.

O preço é um evento separado com:

```text
Start = 0
End = duração total do vídeo
```

### 7.2 Algoritmo conceitual

```javascript
const phaseDuration = 1.4;
let start = 0;
let phaseIndex = 0;

while (start < videoDuration) {
  const end = Math.min(start + phaseDuration, videoDuration);

  if (end > start) {
    const phase = phaseIndex % 2 === 0 ? 'A' : 'B';
    events.push(renderPhase(template, phase, start, end));
  }

  start = end;
  phaseIndex += 1;
}
```

### 7.3 Conversão para tempo ASS

ASS utiliza:

```text
H:MM:SS.cc
```

onde `cc` representa centésimos de segundo.

Exemplo:

```text
51.20 s -> 0:00:51.20
```

Para o horário final, a implementação deve trabalhar internamente em
milissegundos ou centésimos inteiros e somente formatar para ASS na escrita
final. É aceitável que o último evento termine alguns centésimos antes do
vídeo; não é necessário ajustar o overlay ao último frame. A tolerância
proposta é de no máximo `0,10 s` antes do fim, sem gap entre eventos.

### 7.4 Regra obrigatória

Nunca gerar:

```text
Start == End
```

ou:

```text
Start > End
```

Eventos assim não são válidos para o resultado esperado e podem não aparecer no Aegisub/libass.

## 8. Normalização de vídeo para 1080x1920

O ASS utiliza coordenadas fixas 1080x1920. Por isso, antes de aplicar o overlay, o vídeo deve ser normalizado para essa resolução.

### 8.1 Leitura das dimensões

Obter largura e altura com `ffprobe`:

```bash
ffprobe -v error -select_streams v:0 \
-show_entries stream=width,height \
-of csv=s=x:p=0 input.mp4
```

Exemplo:

```text
720x1280
```

### 8.2 Saída obrigatória

```text
1080x1920
```

### 8.3 Estratégia de enquadramento: preservar vertical; crop como fallback

A primeira versão deve preservar o enquadramento dos vídeos verticais atuais,
que já foram observados com posicionamento adequado nas publicações. Não deve
haver crop adicional quando a origem já for compatível com o canvas vertical.

Quando a origem não for compatível com `1080x1920`, aplicar, nesta ordem:

1. escalar preservando a proporção;
2. preservar o quadro inteiro sempre que isso não comprometer o canvas;
3. usar `COVER + CROP CENTRAL` somente como fallback;
4. manter o crop centralizado quando o fallback for necessário.

Filtro conceitual para origem vertical compatível, preservando o quadro:

```bash
scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2
```

Isso garante que todas as coordenadas ASS tenham comportamento previsível,
mantendo o enquadramento original como prioridade.

Somente quando a origem não puder ser usada com preservação do quadro, o
fallback de cobertura será:

```bash
scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920
```

### 8.4 Exemplos

Entrada 1080x1920:

```text
não precisa alterar geometria
```

Entrada 720x1280:

```text
scale -> 1080x1920
```

Entrada 1080x1350:

```text
scale preservando proporção
crop central para 1080x1920
```

Entrada horizontal:

```text
scale para cobrir o canvas vertical
crop central
```

Nesta versão não há detecção de rosto/produto para crop inteligente. A análise
dos vídeos e publicações atuais não indicou necessidade de crop adicional para
o cenário preferencial de celular da Shopee.

## 9. Renderização FFmpeg

Fluxo conceitual:

```text
input.mp4
   ↓
normalização 1080x1920
   ↓
overlay ASS
   ↓
output.mp4
```

Exemplo de filtro único:

```bash
ffmpeg -i input.mp4 \
-vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,ass=overlay.ass" \
-c:v libx264 \
-c:a copy \
output.mp4
```

Na implementação real, o caminho do `.ass` e do MP4 deve ser específico da
execução/job para evitar colisão entre processamentos simultâneos. O arquivo
final precisa estar disponível por HTTPS para a Instagram Graph API antes da
criação do container do Reel.

O destino escolhido é armazenamento temporário na VPS, com entrega por uma rota
HTTPS dedicada no Traefik usando o domínio já configurado para o n8n. Não se
prevê contratar outro storage ou domínio nesta fase. A rota de mídia ainda
precisa ser implementada.

## 10. Templates

Todos os textos que contêm a palavra `QUERO` devem usar exatamente:

```text
QUERO
```

Nunca `Quero`, `quero` ou outra capitalização.

### Template 01 — Vermelho

**Paleta principal:** `#F81838`

**Fase A**

```text
Comente
QUERO
```

`QUERO` é elemento visual isolado em `Happy Camper`.

**Fase B**

```text
Receba o link do grupo
```

**Animação:** pop/scale curto.

**Preço:** branco sobre caixa vermelha.

### Template 02 — Rosa

**Paleta principal:** `#FF3B7D`

**Fase A**

```text
Digite
QUERO
```

`QUERO` é elemento visual isolado em `Happy Camper`.

**Fase B**

```text
E entre no nosso grupo
```

**Animação:** slide horizontal convergente.

**Preço:** branco sobre caixa rosa.

### Template 03 — Coral

**Paleta principal:** `#FF6B5E`

**Fase A**

```text
Quer entrar?
```

**Fase B**

```text
Comente QUERO e receba o link
```

Não existe `QUERO` isolado.

**Animação:** leve rotação de entrada + estabilização.

**Preço:** branco sobre caixa coral.

### Template 04 — Laranja

**Paleta principal:** `#FF8A00`

**Fase A**

```text
Gostou?
```

**Fase B**

```text
Comente QUERO para entrar no grupo
```

Não existe `QUERO` isolado.

**Animação:** entrada vertical/bounce curto.

**Preço:** preto sobre caixa laranja.

### Template 05 — Amarelo

**Paleta principal:** `#FFD23F`

**Fase A**

```text
Comente QUERO
```

**Fase B**

```text
E eu te mando o grupo
```

Não existe `QUERO` isolado.

**Animação:** fade + scale.

**Preço:** preto sobre caixa amarela.

### Template 06 — Teal

**Paleta principal:** `#15B8A6`

**Fase A**

```text
Seu achado está aqui
```

**Fase B**

```text
Digite QUERO para o grupo
```

Não existe `QUERO` isolado.

**Animação:** slide de baixo para cima.

**Preço:** branco sobre caixa teal.

### Template 07 — Azul

**Paleta principal:** `#3B82F6`

**Fase A**

```text
Quer entrar no grupo?
```

**Fase B**

```text
Comente QUERO e receba o acesso
```

Não existe `QUERO` isolado.

**Animação:** wiggle/rotação curta.

**Preço:** branco sobre caixa azul.

### Template 08 — Roxo

**Paleta principal:** `#8B5CF6`

**Fase A**

```text
Vem pro grupo
```

**Fase B**

```text
Escreva QUERO nos comentários
```

Não existe `QUERO` isolado.

**Animação:** squeeze/expansão horizontal.

**Preço:** branco sobre caixa roxa.

### Template 09 — Rosa queimado

**Paleta principal:** `#E86A92`

**Fase A**

```text
Não perca
```

**Fase B**

```text
Comente QUERO e receba o link do grupo
```

Não existe `QUERO` isolado.

**Animação:** movimento diagonal curto.

**Preço:** branco sobre caixa rosa queimado.

### Template 10 — Preto + vermelho

**Paleta principal:** preto + `#F81838`

**Fase A**

```text
Aproveite todas as ofertas
```

**Fase B**

```text
Digite QUERO e receba o grupo
```

Não existe `QUERO` isolado.

**Animação:** pulse/scale.

**Preço:** branco, com composição preto/vermelho.

## 11. Estrutura sugerida da configuração

Nesta versão, a referência concreta de estilos, posições, tamanhos, cores e
animações é `testeFonte.ass`. O gerador deve reproduzir essa referência e
substituir apenas os valores dinâmicos, principalmente preço, duração e
template selecionado. A conversão dessa referência para uma configuração
declarativa ainda precisa ser formalizada antes da implementação.

A definição de cada template deve ser declarativa, para impedir que o workflow n8n precise conhecer detalhes de ASS.

Exemplo conceitual:

```javascript
const templates = {
  1: {
    id: 1,
    name: 'red_pop',
    phaseA: {
      type: 'split',
      parts: ['Comente', 'QUERO'],
      animation: 'pop'
    },
    phaseB: {
      type: 'single',
      text: 'Receba o link do grupo',
      animation: 'scale'
    },
    palette: {
      accent: '#F81838',
      text: '#FFFFFF'
    }
  },
  // ... 2 a 10
};
```

A implementação pode utilizar outra estrutura equivalente, desde que o n8n continue recebendo/gerando apenas o `template_id` e dados do vídeo.

O arquivo de referência contém as dez variações em sequência em um showcase de
`51,20 s` (`5,12 s` por template). Ele não representa sozinho o comportamento
de produção definido nesta spec, que sorteia um `template_id`. O gerador deve
extrair a definição do template escolhido e aplicar suas fases ao vídeo inteiro;
não deve publicar automaticamente as dez variações em sequência.

## 12. Fluxo n8n/VPS proposto

```text
09:00 BRT, após refresh + planejamento + tracking + resolução de mídia
    ↓
Enumerar candidatos pela elegibilidade atual (sem fixar os 6 horários)
    ↓
Para cada item do plano com mídia disponível: item_id + video_url + preço do
refresh + template_id
    ↓
n8n lê ASS de produção no Google Drive e entrega os dados à VPS
    ↓
VPS renderiza e publica artefato temporário HTTPS, indexado por item_id
    ↓
10:00, 12:00, 14:00, 16:00, 18:00 e 20:00 BRT
    ↓
Executar seleção atual, sem mudar query/ordenação/exclusões
    ↓
Encontrar artefato por item_id; se indisponível, usar video_url original
    ↓
Publicar e confirmar pelo fluxo atual; registrar item_id/template/logs
    ↓
00:00 BRT: limpar apenas jobs concluídos e artefatos seguros para remoção
```

O pré-render não escolhe antecipadamente qual candidato será publicado em cada
horário. A seleção atual continua sendo a autoridade no momento do post; o
`item_id` serve somente para recuperar o MP4 preparado para aquele item.

## 13. Entradas mínimas

```json
{
  "item_id": "identificador-do-item-shopee",
  "planned_date": "YYYY-MM-DD",
  "video_url": "https://.../shopee-source.mp4",
  "price": "R$ 39.97",
  "template_id": 4,
  "ass_template": "conteúdo/binário lido pelo n8n do Google Drive",
  "job_id": "identificador-único-do-job-de-render"
}
```

Dados derivados automaticamente:

```json
{
  "item_id": "identificador-do-item-shopee",
  "planned_date": "YYYY-MM-DD",
  "duration_seconds": 51.2,
  "source_width": 1080,
  "source_height": 1920,
  "template_id": 4
}
```

## 14. Saídas mínimas

Por job:

```text
artifact_url
output.mp4
```

Quando as duas tentativas de render falharem, não há `artifact_url` de saída:
o n8n continua com o `video_url` original e registra o fallback no resultado
da publicação.

O resultado inclui `item_id`, data do plano, `template_id`, estado e metadados
do artefato. O `item_id` localiza o artefato pré-renderizado; o identificador
do plano de despacho continua sendo registrado separadamente na publicação.
O `.ass` pode ser temporário e removido após o processamento. A limpeza dos
MP4s está prevista para 00:00 BRT, condicionada a não haver processamento ou
publicação em andamento.

## 15. Validações obrigatórias

Antes da renderização:

- vídeo de entrada existe;
- duração > 0;
- largura > 0;
- altura > 0;
- `template_id` entre 1 e 10;
- preço não vazio;
- fontes disponíveis;
- FFmpeg possui suporte a libass;
- arquivo ASS foi gerado;
- nenhum evento possui `Start >= End`.

Depois da renderização:

- `output.mp4` existe;
- duração de saída é compatível com a entrada;
- resolução final é 1080x1920;
- FFmpeg terminou com código 0.
- `artifact_url` está acessível por HTTPS para o consumidor de publicação;
- o resultado contém `template_id` e metadados de origem/saída;
- uma repetição do mesmo job não mistura nem sobrescreve o artefato de outra
  execução.

## 16. Critérios de aceite

A implementação será considerada conforme quando:

1. processar corretamente vídeo 1080x1920;
2. processar vídeo de outra resolução e entregar 1080x1920;
3. gerar ASS para vídeos curtos e longos, encerrando no máximo `0,10 s` antes
   do fim do vídeo;
4. não criar eventos de duração zero;
5. selecionar qualquer um dos 10 templates por sorteio uniforme;
6. manter o preço durante todo o vídeo;
7. alternar continuamente as fases A/B até o final;
8. manter `QUERO` sempre em maiúsculas;
9. renderizar Smithen e Happy Camper corretamente no ambiente FFmpeg;
10. preservar as cores e animações definidas por template;
11. manter o n8n livre de regras específicas de layout;
12. executar o processamento na VPS e devolver ao n8n um `artifact_url` válido;
13. preservar `template_id` no resultado e no registro de publicação;
14. buscar o ASS no Google Drive e encaminhá-lo à VPS;
15. fazer no máximo duas tentativas de render e, se ambas falharem, publicar o
    vídeo Shopee original sem overlay;
16. manter inalteradas as regras atuais de publicação e confirmação;
17. devolver os erros de render ao n8n e registrá-los no payload do evento de
    publicação existente.
18. iniciar o pré-render diário às 09:00 BRT somente após concluir a cadeia
    atual; uma preparação incompleta nunca atrasa o post e usa o vídeo original.
19. preservar a seleção atual do candidato e recuperar o render por `item_id`.
20. limpar às 00:00 BRT apenas arquivos concluídos/expirados e não utilizados.

## 17. Fora do escopo desta versão

Não implementar nesta etapa:

- escolha de template por performance histórica;
- IA para escolher cor conforme o vídeo;
- crop inteligente por rosto ou produto;
- detecção automática de área livre para texto;
- geração automática de novas copies;
- seleção ponderada de templates;
- bloqueio de repetição consecutiva;
- logos ou emojis Unicode no ASS;
- animação de PNGs/logos externos.

Ícones ou imagens estáticas, caso sejam adicionados posteriormente, devem preferencialmente ser sobrepostos pelo FFmpeg como PNG transparente, sem depender de emoji Unicode no ASS.

## 18. Pendências para fechar a implementação

### 18.1 Crop e preservação do conteúdo

**Resolvida para o cenário atual.** Os vídeos observados são produzidos para
visualização em celular no ecossistema da Shopee e as publicações atuais estão
adequadas em termos de posicionamento. Portanto, preservar o enquadramento
vertical original é a regra principal; crop central permanece apenas como
fallback técnico para uma origem incompatível.

Não faz parte desta versão implementar detecção de rosto, detecção de produto
ou crop inteligente.

### 18.2 Contrato operacional VPS ↔ n8n

#### Solução de armazenamento e entrega definida

O MP4 renderizado ficará temporariamente na VPS e será servido por HTTPS
através de uma rota dedicada no Traefik, usando o domínio HTTPS existente do
n8n. Não se prevê contratar outro storage ou domínio nesta fase. URL ilustrativa:

```text
https://n8n-owco.srv1805131.hstgr.cloud/media/jobs/{job_id}/output.mp4
```

O path `/media/jobs/` ainda não existe e poderá mudar na implementação. A Meta
deve conseguir baixar o arquivo sem sessão, cookie ou cabeçalho privado. Se
houver controle de acesso, usar um token opaco e imprevisível na própria URL,
limitado ao artefato e com validade temporária. Não expor diretórios arbitrários
nem permitir que `job_id` escape da pasta de artefatos.

#### Evidência da VPS consultada em 2026-09-16

- Traefik estava ativo, escutando nas portas 80/443 e configurado para
  redirecionar HTTP para HTTPS e emitir certificados Let's Encrypt.
- O domínio HTTPS existente do n8n respondeu `HTTP 200` numa consulta feita da
  própria VPS, com validação TLS bem-sucedida.
- O disco raiz tinha aproximadamente `68 GB` livres no momento da consulta.
- Não foi encontrada rota/serviço para servir MP4s de jobs. A rota de mídia
  precisa ser implementada e testada de fora da VPS. Esses dados são uma
  fotografia do estado observado, não uma garantia permanente.

#### Decisões restantes do contrato

- n8n envia `video_url` da Shopee; o serviço da VPS baixa o original. Validar
  acesso aos hosts/CDNs e impor limite de tamanho.
- O ASS de produção ficará no Google Drive. O n8n deverá lê-lo usando a
  integração/credencial autorizada e encaminhar seu conteúdo ou binário ao
  renderizador; definir o identificador do arquivo e como versionar alterações.
- Acionar o render por serviço HTTP interno autenticado, com processamento
  assíncrono: iniciar job com `job_id`, consultar status e obter resultado.
  Não abrir uma sessão SSH por item nem manter chamada síncrona durante FFmpeg.
- Definir autenticação n8n→serviço, diretórios e nomenclatura dos jobs.
- Definir limites de duração, tamanho, concorrência e timeout por fase.
- Definir códigos de erro, idempotência do `job_id` e limpeza do ASS/MP4.
- Política de retry definida: tentativa inicial + exatamente um retry. Após
  duas falhas, seguir com o `video_url` original, sem overlay; erro de render
  não bloqueia por si só a publicação.
- Manter a URL acessível até o container Instagram terminar de processar o
  vídeo; depois apagar por limpeza explícita ou TTL.
- Servir o MP4 direto com `Content-Type: video/mp4`; testar `GET`, `HEAD`,
  resposta completa e, se necessário, `Range`/`206 Partial Content`.

### 18.6 Pré-render diário e seleção de candidatos

**Definições fechadas:** primeiro post às 10:00 BRT; job independente às
09:00 BRT; fonte dos itens `offers.daily_dispatch_plan` do dia; limpeza às
00:00 BRT; chave de busca do artefato `item_id`; preço vem do refresh diário.
Mudanças intradia de preço ou dados do item não serão revalidadas para o
artefato/publicação; aceita-se o estado materializado no plano para o dia. A
regra de seleção/publicação permanece inalterada.

Na consulta versionada do workflow, cada execução seleciona um candidato do
plano do dia para o perfil `feminino`, exige mídia válida com `video_url` e
exclui somente planos com publicação Instagram confirmada associada ao plano.
A ordem é `daily_sequence`; a consulta usa `FOR UPDATE ... SKIP LOCKED` e não
filtra nem ordena por `planned_hour` (esse campo é auditoria). Assim, a
seleção é feita a cada execução, não é um mapa fixo candidato→horário. O
pré-render deve fornecer artefatos para os itens do plano do dia que tenham
mídia resolvida, sem alterar a consulta de publicação nem presumir que somente
os seis primeiros serão usados. O processo das 09:00 não depende de
encadeamento com refresh/resolver: consulta o plano; se não houver itens para
processar, encerra com sucesso sem renderizações.

Pendências que ainda exigem definição ou especificação técnica:

1. **Manifesto/índice de artefatos:** escolher entre manifesto/API do serviço
   VPS ou outra opção já existente para resolver `item_id`→status, URL,
   `template_id`, preço/snapshot e versão da origem. Não há decisão de criar
   tabela Supabase nesta spec.
2. **Contrato do serviço:** fechar autenticação n8n→VPS, submissão assíncrona,
   consulta de status, idempotência/retry, códigos de erro, limites de payload
   de logs e contrato de retorno. A rota HTTPS de mídia e teste externo seguem
   bloqueantes para produção.
3. **Limites operacionais:** obter por testes os limites seguros de tamanho,
   duração, concorrência, timeout, memória e espaço em disco; não é necessário
   fixá-los por estimativa antes dos testes.
4. **Retenção do MP4:** manter a URL do artefato acessível enquanto o container
   Instagram está sendo processado; o fluxo atual do n8n consulta o status e só
   publica quando recebe `FINISHED`. Depois desse ponto, o arquivo pode ser
   elegível à limpeza diária, desde que não haja outra execução usando o mesmo
   artefato. TTL adicional fica para definir/validar nos testes.
5. **Drive e templates:** o rascunho visual já existe. Falta operacionalizar o
   arquivo de produção no Drive e criar/configurar os 10 templates; o n8n
   sorteará `template_id` por item. O sample `testeFonte.ass` é um showcase
   sequencial, não um template pronto por job.
6. **Preço:** decidido: usar o valor produzido pelo refresh diário e mantido
   no plano do dia; não conferir alterações posteriores durante a publicação.

Não são pendências: reavaliar a regra de escolha de candidato, encadear o job
das 09:00 ao refresh/resolver, revalidar os dados após o refresh, alterar o
horário de publicação, adotar chave diferente de `item_id` para localizar o
artefato, ou mudar a confirmação/contabilização de publicação.

#### Ligação entre item publicado e artefato

O fluxo atual registra `item_id` na coluna de mesmo nome em
`offers.publication_events`. Também guarda
`payload.source_dispatch_plan_id`, que identifica o registro de
`offers.daily_dispatch_plan` usado pela publicação e é a chave usada pelo fluxo
para evitar confirmar/publicar novamente o mesmo plano. No evento Instagram,
`dispatch_plan_id` da coluna pode ser nulo; portanto, a referência canônica à
linha do plano está no payload.

O catálogo de artefatos deve seguir essa identificação existente:

- localizar o MP4 por `item_id`, a chave já escolhida para o pré-render;
- devolver/guardar também `source_dispatch_plan_id`, data do plano e
  `template_id` como rastreabilidade e validação de correspondência;
- no consumo, confirmar que o `item_id` do artefato é igual ao selecionado pelo
  claim atual; se houver referência de plano, conferir também que ela bate com
  `source_dispatch_plan_id` do evento/slot.

Assim, `item_id` liga o vídeo ao produto e `source_dispatch_plan_id` mantém a
mesma rastreabilidade por ocorrência diária já usada no ledger, sem criar uma
nova regra de publicação.

#### Smoke test de rota e FFmpeg na VPS

Foi criado `scripts/ops/test_instagram_reel_render_route.sh` para executar na
VPS depois que a rota HTTPS estiver montada para uma `media-root`. O teste
recebe um vídeo HTTPS e um arquivo ASS, verifica FFmpeg/libass e ffprobe,
renderiza MP4 1080x1920 no diretório temporário servido pela rota, testa `HEAD`
e `GET` com `Content-Type: video/mp4`, compara os bytes servidos com o resultado
local e remove apenas o diretório temporário criado pelo próprio teste. Com
`--keep-artifacts`, mantém o MP4 para inspeção.

Este smoke test comprova execução FFmpeg e entrega HTTP do arquivo de teste;
não instala/configura a rota, não chama Instagram Graph API, não publica e não
substitui testes dos limites de carga/concor­rência ou dos dez templates.

**Estado:** armazenamento/entrega, origem do ASS e fallback funcional definidos;
implementação da rota e validação externa são bloqueantes. Credencial/arquivo
Drive, limites e detalhes do contrato também devem ser definidos antes da
produção.

### 18.3 Registro do template

O `template_id` deve ser incluído no payload do evento de publicação, junto com
`artifact_url`, dimensões, duração e status da renderização. A renderização
concluída não equivale a publicação confirmada.

O renderizador deve devolver ao n8n o resultado de cada tentativa e erro
sanitizado. O n8n deve incluir no `payload` do `offers.publication_events`
existente, no mínimo:

```json
{
  "template_id": 4,
  "ass_asset_version": "sha256-ou-versao-do-arquivo-do-drive",
  "render_status": "failed_fallback_original",
  "render_attempts": 2,
  "render_error_code": "FFMPEG_RENDER_FAILED",
  "render_error_log": "trecho sanitizado e limitado do log de erro",
  "overlay_applied": false,
  "published_video_source": "shopee_original"
}
```

Em sucesso, registrar `render_status: "succeeded"`, `overlay_applied: true`,
`published_video_source: "rendered_artifact"`, `artifact_url` e metadados de
saída. Em fallback, manter também os erros das duas tentativas, com tamanho
limitado e sem tokens, URLs assinadas de entrada, cabeçalhos, caminhos internos
ou outros segredos. Não criar tabela/evento paralelo nem mudar os critérios
atuais de `delivery_status`: a confirmação continua refletindo o resultado da
publicação Instagram pelo fluxo existente.

**Estado:** definição funcional concluída; falta apenas implementar e validar o
registro no fluxo existente.

### 18.4 Configuração declarativa dos templates

Os estilos, posições, tamanhos, cores e animações estão definidos no
`testeFonte.ass`, mas ainda precisam ser convertidos em uma configuração
versionada que o gerador consiga carregar por `template_id`. Também falta
definir a validação de que existem exatamente dez templates habilitados.

**Estado:** pendência de implementação, não de decisão visual.

### 18.5 Execução e qualidade do render

Ainda falta fechar e validar:

- parâmetros finais de FFmpeg, incluindo áudio, `pix_fmt`, FPS e `-shortest`;
- escape seguro de preço, copy e caminhos no ASS/comando;
- disponibilidade e licença das fontes na VPS;
- limites de tamanho, duração e concorrência;
- teste dos 37 vídeos reais publicados no período analisado;
- tolerância de duração e validação do MP4 final.

**Estado:** pendência técnica para implementação e testes.

## 19. Princípio de implementação

A regra central é:

> **n8n escolhe e orquestra; a VPS executa; o ASS define o design; o gerador calcula o tempo; FFmpeg normaliza e renderiza.**

Isso mantém o workflow simples e permite alterar copy, cores, posições e animações sem redesenhar o fluxo de automação.
