#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/automacao_grupo_compras/app}"
PYTHON_BIN="${PYTHON_BIN:-${APP_DIR}/.venv/bin/python}"
PROFILE="${PROFILE:-feminino}"
MARKETPLACE="${MARKETPLACE:-shopee}"
MEDIA_LIMIT="${MEDIA_LIMIT:-20}"
LOCK_FILE="${LOCK_FILE:-${APP_DIR}/.data/instagram_media/.resolver.lock}"

cd "${APP_DIR}"

if [[ ! -f ".env" ]]; then
  echo "ERRO resolver Instagram: .env ausente em ${APP_DIR}" >&2
  exit 2
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "ERRO resolver Instagram: python nao executavel em ${PYTHON_BIN}" >&2
  exit 2
fi

if ! [[ "${MEDIA_LIMIT}" =~ ^[1-9][0-9]*$ ]]; then
  echo "ERRO resolver Instagram: MEDIA_LIMIT invalido: ${MEDIA_LIMIT}" >&2
  exit 2
fi

mkdir -p "$(dirname "${LOCK_FILE}")"
exec 9>"${LOCK_FILE}"

if ! flock -n 9; then
  echo "ERRO resolver Instagram: execucao anterior ainda em andamento" >&2
  exit 75
fi

export PYTHONUNBUFFERED=1
export TZ="${TZ:-America/Sao_Paulo}"

PLANNED_DATE="${PLANNED_DATE:-$(TZ=America/Sao_Paulo date +'%Y-%m-%d')}"

echo "INFO resolver Instagram: profile=${PROFILE} marketplace=${MARKETPLACE} date=${PLANNED_DATE} limit=${MEDIA_LIMIT}"

exec "${PYTHON_BIN}" -m ofertas_bot.tools.resolve_instagram_media_batch \
  --profile "${PROFILE}" \
  --marketplace "${MARKETPLACE}" \
  --date "${PLANNED_DATE}" \
  --limit "${MEDIA_LIMIT}" \
  --apply \
  --only-missing
