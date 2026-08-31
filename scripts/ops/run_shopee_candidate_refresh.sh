#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/automacao_grupo_compras/app}"
PYTHON_BIN="${PYTHON_BIN:-${APP_DIR}/.venv/bin/python}"
PROFILE="${PROFILE:-feminino}"
MARKETPLACE="${MARKETPLACE:-shopee}"
DISCOVERY_LIMIT="${DISCOVERY_LIMIT:-1000}"
SCORING_LIMIT="${SCORING_LIMIT:-1000}"
MAX_API_CALLS="${MAX_API_CALLS:-1000}"
PRODUCTCATID_MATRIX="${PRODUCTCATID_MATRIX:-config/shopee_productcatid_quotas_feminino.csv}"
CONFIRM_REMOTE_WRITE="${CONFIRM_REMOTE_WRITE:-REFRESH_SHOPEE_CANDIDATES}"
OUTPUT_BASE_DIR="${OUTPUT_BASE_DIR:-.data/candidate_refresh}"
LOCK_FILE="${LOCK_FILE:-${APP_DIR}/.data/candidate_refresh/.refresh.lock}"
AUTO_CONFIRM_UNAVAILABLE_ENABLED="${AUTO_CONFIRM_UNAVAILABLE_ENABLED:-true}"
AUTO_CONFIRM_UNAVAILABLE_MIN_NO_NODE_ATTEMPTS="${AUTO_CONFIRM_UNAVAILABLE_MIN_NO_NODE_ATTEMPTS:-2}"
AUTO_CONFIRM_UNAVAILABLE_REASON="${AUTO_CONFIRM_UNAVAILABLE_REASON:-automatic confirmation after repeated no_node refresh responses}"
AUTO_CONFIRM_UNAVAILABLE_CONFIRMATION="${AUTO_CONFIRM_UNAVAILABLE_CONFIRMATION:-AUTO_CONFIRM_CANDIDATE_UNAVAILABLE}"

cd "${APP_DIR}"

if [[ ! -f ".env" ]]; then
  echo "ERRO refresh Shopee: .env ausente em ${APP_DIR}" >&2
  exit 2
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "ERRO refresh Shopee: python nao executavel em ${PYTHON_BIN}" >&2
  exit 2
fi

mkdir -p "$(dirname "${LOCK_FILE}")"
exec 9>"${LOCK_FILE}"

if ! flock -n 9; then
  echo "ERRO refresh Shopee: execucao anterior ainda em andamento" >&2
  exit 75
fi

export PYTHONUNBUFFERED=1
export TZ="${TZ:-America/Sao_Paulo}"

RUN_ID="${RUN_ID:-$(TZ=America/Sao_Paulo date +'%Y-%m-%dT%H-%M-%S%z')-candidate-refresh}"
REFRESH_ATTEMPTS_FILE="${OUTPUT_BASE_DIR}/${PROFILE}/${RUN_ID}/refresh_attempts.csv"

"${PYTHON_BIN}" scripts/shopee/run_candidate_refresh.py \
  --profile "${PROFILE}" \
  --marketplace "${MARKETPLACE}" \
  --productcatid-matrix "${PRODUCTCATID_MATRIX}" \
  --discovery-limit "${DISCOVERY_LIMIT}" \
  --scoring-limit "${SCORING_LIMIT}" \
  --max-api-calls "${MAX_API_CALLS}" \
  --output-base-dir "${OUTPUT_BASE_DIR}" \
  --run-id "${RUN_ID}" \
  --apply \
  --confirm-remote-write "${CONFIRM_REMOTE_WRITE}"

if [[ "${AUTO_CONFIRM_UNAVAILABLE_ENABLED}" == "true" ]]; then
  if [[ ! -f "${REFRESH_ATTEMPTS_FILE}" ]]; then
    echo "ERRO refresh Shopee: refresh_attempts.csv ausente em ${REFRESH_ATTEMPTS_FILE}" >&2
    exit 3
  fi

  "${PYTHON_BIN}" scripts/shopee/auto_confirm_candidate_unavailable.py \
    --profile "${PROFILE}" \
    --marketplace "${MARKETPLACE}" \
    --refresh-attempts-file "${REFRESH_ATTEMPTS_FILE}" \
    --min-no-node-attempts "${AUTO_CONFIRM_UNAVAILABLE_MIN_NO_NODE_ATTEMPTS}" \
    --reason "${AUTO_CONFIRM_UNAVAILABLE_REASON}" \
    --apply \
    --confirm-remote-write "${AUTO_CONFIRM_UNAVAILABLE_CONFIRMATION}"
fi

"${PYTHON_BIN}" -m ofertas_bot.tools.plan_daily_dispatch \
  --profile "${PROFILE}" \
  --marketplace "${MARKETPLACE}" \
  --productcatid-matrix "${PRODUCTCATID_MATRIX}" \
  --apply
