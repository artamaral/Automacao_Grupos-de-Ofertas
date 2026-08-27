#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/automacao_grupo_compras/app}"
PYTHON_BIN="${PYTHON_BIN:-${APP_DIR}/.venv/bin/python}"
PROFILE="${PROFILE:-feminino}"
export TZ="${TZ:-America/Sao_Paulo}"

cd "${APP_DIR}"
/bin/bash "${APP_DIR}/scripts/ops/run_shopee_candidate_refresh.sh"
"${PYTHON_BIN}" -m ofertas_bot.tools.generate_shopee_tracking_links \
  --profile "${PROFILE}" --apply \
  --confirm-remote-write GENERATE_SHOPEE_TRACKING_LINKS
