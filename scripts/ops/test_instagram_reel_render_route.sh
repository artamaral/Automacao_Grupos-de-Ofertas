#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Smoke test de FFmpeg + rota HTTPS de artefatos para Reels (executar na VPS).

Uso:
  test_instagram_reel_render_route.sh \
    --input-url URL \
    --ass-file /caminho/overlay.ass \
    --media-root /caminho/servido-pela-rota \
    --public-base-url https://host/media/jobs

O script renderiza um MP4 em subdiretorio temporario da media-root, testa HEAD
e GET pela URL publica e remove apenas esse subdiretorio. Use --keep-artifacts
para manter o MP4 apos os testes.
EOF
}

fail() {
  printf 'ERRO: %s\n' "$*" >&2
  exit 1
}

input_url=''
ass_file=''
media_root=''
public_base_url=''
keep_artifacts=false

while (($#)); do
  case "$1" in
    --input-url)
      (($# >= 2)) || fail 'faltou valor para --input-url'
      input_url=$2
      shift 2
      ;;
    --ass-file)
      (($# >= 2)) || fail 'faltou valor para --ass-file'
      ass_file=$2
      shift 2
      ;;
    --media-root)
      (($# >= 2)) || fail 'faltou valor para --media-root'
      media_root=$2
      shift 2
      ;;
    --public-base-url)
      (($# >= 2)) || fail 'faltou valor para --public-base-url'
      public_base_url=${2%/}
      shift 2
      ;;
    --keep-artifacts)
      keep_artifacts=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "argumento desconhecido: $1"
      ;;
  esac
done

[[ -n "$input_url" ]] || fail '--input-url e obrigatorio'
[[ "$input_url" == https://* ]] || fail '--input-url deve usar HTTPS'
[[ -n "$ass_file" && -f "$ass_file" ]] || fail '--ass-file nao existe ou nao e arquivo'
[[ -n "$media_root" && -d "$media_root" ]] || fail '--media-root deve existir e ser diretorio'
[[ -n "$public_base_url" ]] || fail '--public-base-url e obrigatorio'
[[ "$public_base_url" == https://* ]] || fail '--public-base-url deve usar HTTPS'
[[ "$media_root" != / ]] || fail 'nao e permitido usar / como --media-root'

for command_name in curl ffmpeg ffprobe fc-match mktemp tail; do
  command -v "$command_name" >/dev/null 2>&1 || fail "comando obrigatorio ausente: $command_name"
done

media_root=$(cd -- "$media_root" && pwd -P)
ass_file=$(cd -- "$(dirname -- "$ass_file")" && pwd -P)/$(basename -- "$ass_file")
job_dir=$(mktemp -d "$media_root/render-smoke-XXXXXXXX")
job_dir=$(cd -- "$job_dir" && pwd -P)
chmod 0755 "$job_dir"
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/reels-render-smoke.XXXXXXXX")

cleanup() {
  rm -rf -- "$work_dir"
  if [[ "$keep_artifacts" != true && -n "${job_dir:-}" ]]; then
    case "$job_dir" in
      "$media_root"/render-smoke-*) rm -rf -- "$job_dir" ;;
      *) printf 'AVISO: nao removi caminho fora do diretorio de teste: %s\n' "$job_dir" >&2 ;;
    esac
  fi
}
trap cleanup EXIT

output_file="$job_dir/output.mp4"
artifact_url="$public_base_url/$(basename -- "$job_dir")/output.mp4"
source_file="$work_dir/source.mp4"
ass_copy="$work_dir/overlay.ass"
cp -- "$ass_file" "$ass_copy"

printf '1/6 Validando filtro ASS e ferramentas...\n'
ffmpeg -hide_banner -filters 2>/dev/null | awk '$2 == "ass" { found=1 } END { exit !found }' ||
  fail 'FFmpeg nao anuncia o filtro ass (libass)'
smithen_family=$(fc-match -f '%{family}' 'Smithen' | head -n 1)
happy_camper_family=$(fc-match -f '%{family}' 'Happy Camper' | head -n 1)
[[ "$smithen_family" == 'Smithen' ]] ||
  fail "fonte Smithen nao encontrada; fallback detectado: $smithen_family"
[[ "$happy_camper_family" == 'Happy Camper' ]] ||
  fail "fonte Happy Camper nao encontrada; fallback detectado: $happy_camper_family"

printf '2/6 Baixando video de teste...\n'
curl --fail --silent --show-error --location --proto '=https' \
  --connect-timeout 20 --max-time 180 --output "$source_file" "$input_url" ||
  fail 'nao foi possivel baixar o video de entrada'
[[ -s "$source_file" ]] || fail 'download do video resultou em arquivo vazio'

printf '3/6 Lendo propriedades da origem...\n'
source_dimensions=$(ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height -of csv=s=x:p=0 "$source_file") ||
  fail 'ffprobe nao conseguiu ler o video de origem'
[[ "$source_dimensions" =~ ^[1-9][0-9]*x[1-9][0-9]*$ ]] ||
  fail "dimensoes de origem invalidas: $source_dimensions"

printf '4/6 Renderizando MP4 com FFmpeg + ASS...\n'
filter="scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,ass=${ass_copy}"
ffmpeg -hide_banner -loglevel error -nostdin -y -i "$source_file" \
  -vf "$filter" -map 0:v:0 -map '0:a?' -c:v libx264 -pix_fmt yuv420p \
  -c:a aac -movflags +faststart -shortest "$output_file" \
  >"$work_dir/ffmpeg.log" 2>&1 || {
    tail -n 40 "$work_dir/ffmpeg.log" >&2
    fail 'FFmpeg falhou ao renderizar'
  }
[[ -s "$output_file" ]] || fail 'FFmpeg terminou sem gerar MP4'
chmod 0644 "$output_file"

output_probe=$(ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height -show_entries format=duration \
  -of default=noprint_wrappers=1 "$output_file") || fail 'ffprobe falhou na verificacao da saida'
grep -qx 'width=1080' <<<"$output_probe" || fail 'largura de saida diferente de 1080'
grep -qx 'height=1920' <<<"$output_probe" || fail 'altura de saida diferente de 1920'

printf '5/6 Testando HEAD na rota HTTPS...\n'
head_result=$(curl --fail --silent --show-error --head --location \
  --connect-timeout 15 --max-time 45 \
  --write-out '%{http_code} %{content_type}' \
  --output /dev/null "$artifact_url") || fail 'HEAD falhou na rota publica'
read -r head_status head_type <<<"$head_result"
[[ "$head_status" == 200 ]] || fail "HEAD retornou HTTP $head_status (esperado 200)"
[[ "$head_type" == video/mp4* ]] || fail "HEAD retornou Content-Type inesperado: $head_type"

printf '6/6 Baixando artefato pela rota HTTPS e validando...\n'
downloaded_file="$work_dir/route-copy.mp4"
get_result=$(curl --fail --silent --show-error --location \
  --connect-timeout 15 --max-time 180 --output "$downloaded_file" \
  --write-out '%{http_code} %{content_type} %{size_download}' "$artifact_url") ||
  fail 'GET falhou na rota publica'
read -r get_status get_type get_size <<<"$get_result"
[[ "$get_status" == 200 ]] || fail "GET retornou HTTP $get_status (esperado 200)"
[[ "$get_type" == video/mp4* ]] || fail "GET retornou Content-Type inesperado: $get_type"
[[ "$get_size" =~ ^[1-9][0-9]*$ && -s "$downloaded_file" ]] || fail 'GET nao entregou conteudo'
cmp -s "$output_file" "$downloaded_file" || fail 'bytes servidos pela rota diferem do MP4 renderizado'
ffprobe -v error -select_streams v:0 "$downloaded_file" >/dev/null ||
  fail 'o arquivo baixado pela rota nao e um video legivel pelo ffprobe'

printf 'OK: FFmpeg renderizou %sx%s -> 1080x1920; rota HTTPS serviu MP4 valido (%s bytes).\n' \
  "${source_dimensions%x*}" "${source_dimensions#*x}" "$get_size"
if [[ "$keep_artifacts" == true ]]; then
  printf 'Artefato de teste mantido em: %s\n' "$output_file"
fi
