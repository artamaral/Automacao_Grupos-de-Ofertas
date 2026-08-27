#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/automacao_grupo_compras/app}"
PYTHON_BIN="${PYTHON_BIN:-${APP_DIR}/.venv/bin/python}"
export TZ="${TZ:-America/Sao_Paulo}"

cd "${APP_DIR}"
"${PYTHON_BIN}" -m ofertas_bot.tools.sync_shopee_conversion_report \
  --apply --confirm-remote-write SYNC_SHOPEE_CONVERSION_REPORT
