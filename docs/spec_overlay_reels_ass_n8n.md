# Spec — Overlay Dinâmico para Reels com ASS + FFmpeg + n8n

**Status:** rascunho inicial para implementação  
**Escopo:** geração do overlay textual/visual de Reels de ofertas, seleção aleatória de template, adaptação à duração do vídeo e normalização de resolução antes da renderização.

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
2. obter a duração e as dimensões reais com `ffprobe`;
3. selecionar aleatoriamente um `template_id` entre 1 e 10;
4. fornecer ao gerador de ASS:
   - duração;
   - preço;
   - `template_id`;
   - dimensões/resolução de entrada, quando necessário;
5. gerar o `.ass` de forma determinística a partir do template sorteado;
6. executar FFmpeg para normalizar o vídeo e renderizar o ASS;
7. devolver o vídeo final.

O n8n **não deve calcular manualmente posições, cores, fontes ou animações**. Essas regras pertencem à definição dos templates.

### 2.2 Gerador de ASS

O gerador é responsável por:

- carregar a definição do template selecionado;
- gerar os estilos `[V4+ Styles]`;
- calcular todos os intervalos de tempo em função da duração real;
- criar os eventos `[Events]` até o último frame do vídeo;
- impedir eventos com `Start >= End`;
- limitar o último evento exatamente ao término do vídeo;
- escrever o arquivo ASS em UTF-8.

### 2.3 FFmpeg

O FFmpeg é responsável por:

- normalizar resolução/aspect ratio do vídeo;
- renderizar o `.ass` usando libass;
- utilizar as fontes necessárias;
- gerar o MP4 final.

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
R$ XX,XX
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

O `template_id` selecionado deve ser registrado junto ao processamento sempre que já existir no fluxo um local apropriado para registrar metadados de execução. Esta spec não cria um novo mecanismo de logging.

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

Para o horário final, a conversão deve evitar encerrar o overlay antes do vídeo real por perda de precisão. A implementação deve trabalhar internamente em milissegundos ou centésimos inteiros e somente formatar para ASS na escrita final.

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

### 8.3 Estratégia padrão: COVER + CROP CENTRAL

A primeira versão deve preencher completamente o canvas vertical, sem barras laterais/superiores.

Regra:

1. escalar preservando proporção até cobrir 1080x1920;
2. cortar somente o excedente;
3. manter o crop centralizado.

Filtro conceitual:

```bash
scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920
```

Isso garante que todas as coordenadas ASS tenham comportamento previsível.

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

Nesta versão não há detecção de rosto/produto para crop inteligente.

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

Na implementação real, o caminho do `.ass` deve ser específico da execução/job para evitar colisão entre processamentos simultâneos.

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

## 12. Fluxo n8n proposto

```text
Receber vídeo
    ↓
ffprobe: duração + largura + altura
    ↓
Sortear template_id (1..10)
    ↓
Preparar dados do job
    ↓
Gerar ASS iterativamente até videoDuration
    ↓
FFmpeg: normalize 1080x1920 + render ASS
    ↓
Validar arquivo final
    ↓
Seguir fluxo atual de publicação
```

## 13. Entradas mínimas

```json
{
  "video_path": "/path/input.mp4",
  "price": "R$ 39,97"
}
```

Dados derivados automaticamente:

```json
{
  "duration_seconds": 51.2,
  "source_width": 1080,
  "source_height": 1920,
  "template_id": 4
}
```

## 14. Saídas mínimas

Por job:

```text
overlay.ass
output.mp4
```

O `.ass` pode ser temporário e removido após o processamento, conforme o padrão de arquivos temporários já usado pelo fluxo.

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

## 16. Critérios de aceite

A implementação será considerada conforme quando:

1. processar corretamente vídeo 1080x1920;
2. processar vídeo de outra resolução e entregar 1080x1920;
3. gerar ASS até a duração exata de vídeos curtos e longos;
4. não criar eventos de duração zero;
5. selecionar qualquer um dos 10 templates por sorteio uniforme;
6. manter o preço durante todo o vídeo;
7. alternar continuamente as fases A/B até o final;
8. manter `QUERO` sempre em maiúsculas;
9. renderizar Smithen e Happy Camper corretamente no ambiente FFmpeg;
10. preservar as cores e animações definidas por template;
11. manter o n8n livre de regras específicas de layout.

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

## 18. Princípio de implementação

A regra central é:

> **n8n escolhe e orquestra; o template define o design; o gerador calcula o tempo; FFmpeg normaliza e renderiza.**

Isso mantém o workflow simples e permite alterar copy, cores, posições e animações sem redesenhar o fluxo de automação.
