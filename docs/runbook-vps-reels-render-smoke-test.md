# Smoke test do renderizador de Reels na VPS

Este teste valida somente:

1. FFmpeg com suporte ao filtro `ass`/libass;
2. leitura do vídeo Shopee por HTTPS;
3. renderização do ASS para MP4 `1080x1920`;
4. entrega do MP4 pela rota HTTPS da VPS.

Ele não chama a API do Instagram, não cria container e não publica.

## Pré-requisitos na VPS

Executar em Ubuntu/bash, com um usuário dedicado ao serviço:

```bash
command -v curl
command -v ffmpeg
command -v ffprobe
ffmpeg -hide_banner -filters | grep -E '[[:space:]]ass[[:space:]]'
```

O último comando deve encontrar o filtro `ass`. Se não encontrar, o pacote de
FFmpeg da VPS não possui libass disponível para este uso e o teste deve parar.

Também são necessários:

- uma pasta exclusiva para artefatos temporários, por exemplo
  `/opt/automacao_grupo_compras/media/jobs`;
- uma rota HTTPS que sirva exatamente essa pasta, sem exigir sessão, cookie ou
  cabeçalho privado;
- `Content-Type: video/mp4` para arquivos `.mp4`;
- permissão de leitura para o proxy web e permissão de escrita para o usuário
  que executa o renderizador;
- uma URL HTTPS real de vídeo Shopee para o teste;
- uma cópia do ASS na VPS. Para o primeiro smoke test, usar o arquivo
  `testeFonte.ass` fornecido pelo usuário; ele é uma referência/showcase, não
  ainda o contrato final dos dez templates.
- as fontes `Smithen Script.ttf` e `Happy-Camper-Regular.ttf` instaladas e
  reconhecidas pelo Fontconfig; sem elas o teste deve falhar, não usar fallback.

## Preparação da mídia e da rota

Não apontar o teste para `/`, para a raiz do n8n ou para um diretório que
contenha credenciais. A pasta deve ser exclusiva do renderizador:

```bash
sudo install -d -o renderizador -g renderizador -m 0750 \
  /opt/automacao_grupo_compras/media/jobs
```

O proxy deve mapear, conceitualmente:

```text
https://DOMINIO/media/jobs/<job-dir>/output.mp4
        -> /opt/automacao_grupo_compras/media/jobs/<job-dir>/output.mp4
```

O nome real do domínio e a configuração Traefik ainda precisam ser confirmados
na VPS. Não executar o smoke test antes de verificar esse mapeamento com um
arquivo de texto inofensivo ou com o próprio artefato de teste.

## Transferência do script e ASS

Executar no Windows PowerShell, sem versionar o ASS:

```powershell
scp .\scripts\ops\test_instagram_reel_render_route.sh usuario@VPS:/tmp/
scp C:\Users\arthu\Downloads\testeFonte.ass usuario@VPS:/tmp/testeFonte.ass
```

Na VPS:

```bash
chmod 0750 /tmp/test_instagram_reel_render_route.sh
chmod 0640 /tmp/testeFonte.ass
```

O arquivo ASS pode ser colocado em outro caminho privado, desde que o usuário
do renderizador consiga lê-lo. Não colocar o ASS dentro da pasta pública de
MP4s.

## Execução

Substituir `URL_DE_VIDEO_SHOPEE` pelo `video_url` real de um item de teste e
`DOMINIO` pelo domínio HTTPS da rota. A URL base deve apontar para a mesma
`media-root` preparada acima:

```bash
/tmp/test_instagram_reel_render_route.sh \
  --input-url 'URL_DE_VIDEO_SHOPEE' \
  --ass-file /tmp/testeFonte.ass \
  --media-root /opt/automacao_grupo_compras/media/jobs \
  --public-base-url 'https://DOMINIO/media/jobs'
```

O resultado esperado é semelhante a:

```text
1/6 Validando filtro ASS e ferramentas...
2/6 Baixando video de teste...
3/6 Lendo propriedades da origem...
4/6 Renderizando MP4 com FFmpeg + ASS...
5/6 Testando HEAD na rota HTTPS...
6/6 Baixando artefato pela rota HTTPS e validando...
OK: FFmpeg renderizou ... -> 1080x1920; rota HTTPS serviu MP4 valido (... bytes).
```

O script remove o diretório `render-smoke-*` criado por ele. Para inspeção
manual, acrescentar `--keep-artifacts`; nesse caso, apagar depois somente o
diretório retornado pelo próprio script:

```bash
find /opt/automacao_grupo_compras/media/jobs \
  -maxdepth 1 -type d -name 'render-smoke-*' -print
```

Não usar `rm -rf` com um caminho não conferido. A remoção deve ficar limitada ao
diretório de teste identificado.

## Execução validada em 2026-09-20

Foi usado o item `23098338263` do `daily_dispatch_plan` do dia. A origem tinha
`480x848`; o resultado foi `1080x1920`, com FFmpeg/libass. A rota
`https://n8n-owco.srv1805131.hstgr.cloud/media/jobs/` respondeu corretamente a
`HEAD` e `GET`, com `Content-Type: video/mp4` e arquivo de `12.241.808` bytes.
O artefato temporário foi removido ao final e os containers do n8n e Traefik
continuaram saudáveis.

Em seguida, o item `58264680596`, com origem `720x1280` (proporção vertical
9:16), foi renderizado com as fontes corretas instaladas na VPS. O resultado
ficou dentro do canvas; a causa do corte observado no primeiro teste era o
fallback das fontes para `DejaVu Sans`.

Artefatos mantidos para inspeção visual:

- item `23098338263` corrigido:
  `https://n8n-owco.srv1805131.hstgr.cloud/media/jobs/render-smoke-22DJphBN/output.mp4`;
- item `58264680596` em proporção 9:16:
  `https://n8n-owco.srv1805131.hstgr.cloud/media/jobs/render-smoke-okwAXoao/output.mp4`.

O artefato `render-smoke-mBH7L2or` não deve ser usado como referência: foi
gerado antes da instalação das fontes e usou fallback.

## Critérios de aprovação

- `ffmpeg -filters` mostra `ass`;
- o download da origem termina com arquivo não vazio;
- `ffprobe` lê largura, altura e duração da origem;
- FFmpeg termina com código zero;
- o MP4 renderizado tem vídeo `1080x1920` e é legível por `ffprobe`;
- `HEAD` retorna `200` e `Content-Type: video/mp4`;
- `GET` retorna `200`, bytes não vazios e o mesmo conteúdo produzido localmente;
- o diretório de teste é removível sem afetar outros jobs.

## O que este teste ainda não prova

Ele não valida autenticação n8n→VPS, submissão assíncrona, manifesto
`item_id`→artefato, retry, limpeza de produção, concorrência, limite de
memória, limite de disco, os dez templates ou confirmação do Instagram.
Esses são testes seguintes, depois que a rota e o render básico estiverem
aprovados.
