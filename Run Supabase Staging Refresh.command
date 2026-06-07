#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "CHILLCRM Supabase staging refresh"
echo
echo "This will:"
echo "- use your Supabase database password only for this run"
echo "- reload the remote Supabase staging crm schema from local CHILLCRM"
echo "- refresh data parity and production-readiness reports"
echo
echo "This does not unlock hosted writes or make Supabase the source of truth."
echo "Nothing you type here is written to reports or chat."
echo

printf "Supabase database password: "
stty -echo
read SUPABASE_DB_PASSWORD
stty echo
echo

if [[ -z "${SUPABASE_DB_PASSWORD}" ]]; then
  echo "Missing Supabase database password. Exiting."
  read -k 1 "?Press any key to close..."
  exit 1
fi

echo
echo "Type REFRESH to reload Supabase staging from local CHILLCRM."
printf "Confirmation: "
read CONFIRMATION

if [[ "${CONFIRMATION}" != "REFRESH" ]]; then
  echo "Confirmation did not match. No provider action will run."
  unset SUPABASE_DB_PASSWORD
  read -k 1 "?Press any key to close..."
  exit 1
fi

export SUPABASE_DB_PASSWORD
ENCODED_PASSWORD="$("${PYTHON_BIN}" -c 'import os, urllib.parse; print(urllib.parse.quote(os.environ["SUPABASE_DB_PASSWORD"], safe=""))')"
unset SUPABASE_DB_PASSWORD

export CHILLCRM_DATABASE_URL="postgresql://postgres.ckjbnummsxqcyeahzynz:${ENCODED_PASSWORD}@aws-1-us-east-2.pooler.supabase.com:5432/postgres"
unset ENCODED_PASSWORD
export PYTHONPYCACHEPREFIX="/private/tmp/chillcrm_pycache"

echo
echo "Refreshing Supabase staging..."
echo

"${PYTHON_BIN}" scripts/run_supabase_staging_refresh.py --execute

echo
echo "Refreshing final safe reports..."
"${PYTHON_BIN}" scripts/run_safe_production_gate_checks.py --refresh-only

unset CHILLCRM_DATABASE_URL

echo
echo "Done. Review reports/supabase_staging_refresh_run.md and reports/remote_production_readiness.md."
read -k 1 "?Press any key to close..."
