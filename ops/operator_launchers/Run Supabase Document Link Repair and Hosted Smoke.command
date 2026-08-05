#!/bin/zsh
set -u

cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "CHILLCRM Supabase document link repair and hosted smoke"
echo
echo "This will:"
echo "- use your Supabase database password only for this run"
echo "- restore hosted document-file metadata links from the storage manifest"
echo "- use your Vercel API token only to run the hosted smoke check"
echo "- use your CHILLCRM owner password only for the hosted login test"
echo "- refresh production readiness reports"
echo
echo "It does not upload files, unlock hosted CRM writes, change CRM records, or switch source of truth."
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

printf "Vercel API token: "
stty -echo
read VERCEL_TOKEN
stty echo
echo

if [[ -z "${VERCEL_TOKEN}" ]]; then
  echo "Missing Vercel token. Exiting."
  unset SUPABASE_DB_PASSWORD
  read -k 1 "?Press any key to close..."
  exit 1
fi

if [[ "${VERCEL_TOKEN}" != vcp_* && "${VERCEL_TOKEN}" != vck_* ]]; then
  echo
  echo "That does not look like a Vercel API token."
  echo "Use the token from Vercel Account Settings, not the project passcode."
  unset SUPABASE_DB_PASSWORD
  unset VERCEL_TOKEN
  read -k 1 "?Press any key to close..."
  exit 1
fi

printf "CHILLCRM owner password: "
stty -echo
read AUTH_BOOTSTRAP_ADMIN_PASSWORD
stty echo
echo
echo

if [[ -z "${AUTH_BOOTSTRAP_ADMIN_PASSWORD}" ]]; then
  echo "Missing owner password. Exiting."
  unset SUPABASE_DB_PASSWORD
  unset VERCEL_TOKEN
  read -k 1 "?Press any key to close..."
  exit 1
fi

if [[ "${AUTH_BOOTSTRAP_ADMIN_PASSWORD}" == "${VERCEL_TOKEN}" ]]; then
  echo "The owner password matched the Vercel token, which usually means the token was pasted twice."
  echo "No provider action will run. Please launch this again and enter the owner password at the third prompt."
  unset SUPABASE_DB_PASSWORD
  unset VERCEL_TOKEN
  unset AUTH_BOOTSTRAP_ADMIN_PASSWORD
  read -k 1 "?Press any key to close..."
  exit 1
fi

echo
echo "Type REPAIR to restore document-file links and run hosted smoke."
printf "Confirmation: "
read CONFIRMATION

if [[ "${CONFIRMATION}" != "REPAIR" ]]; then
  echo "Confirmation did not match. No provider action will run."
  unset SUPABASE_DB_PASSWORD
  unset VERCEL_TOKEN
  unset AUTH_BOOTSTRAP_ADMIN_PASSWORD
  read -k 1 "?Press any key to close..."
  exit 1
fi

export SUPABASE_DB_PASSWORD
ENCODED_PASSWORD="$("${PYTHON_BIN}" -c 'import os, urllib.parse; print(urllib.parse.quote(os.environ["SUPABASE_DB_PASSWORD"], safe=""))')"
unset SUPABASE_DB_PASSWORD

export CHILLCRM_DATABASE_URL="postgresql://postgres.ckjbnummsxqcyeahzynz:${ENCODED_PASSWORD}@aws-1-us-east-2.pooler.supabase.com:5432/postgres"
unset ENCODED_PASSWORD
export CHILLCRM_SSLROOTCERT="config/supabase-prod-ca-2021.crt"
export VERCEL_TOKEN
export AUTH_BOOTSTRAP_ADMIN_PASSWORD
export EXPECT_DOCUMENT_FILE_ACCESS="true"
export PYTHONPYCACHEPREFIX="/private/tmp/chillcrm_pycache"

echo
echo "Repairing document-file links..."
"${PYTHON_BIN}" scripts/repair_supabase_document_file_links.py
REPAIR_STATUS=$?

echo
echo "Running hosted smoke..."
"${PYTHON_BIN}" scripts/run_newest_hosted_smoke_with_vercel_bypass.py \
  --owner-email kevinnations@gmail.com
SMOKE_STATUS=$?

echo
echo "Refreshing Vercel deployment diagnostics..."
"${PYTHON_BIN}" scripts/inspect_vercel_deployment.py
DIAGNOSTICS_STATUS=$?

echo
echo "Refreshing safe production reports..."
"${PYTHON_BIN}" scripts/run_safe_production_gate_checks.py --refresh-only
REFRESH_STATUS=$?

unset CHILLCRM_DATABASE_URL
unset CHILLCRM_SSLROOTCERT
unset VERCEL_TOKEN
unset AUTH_BOOTSTRAP_ADMIN_PASSWORD
unset EXPECT_DOCUMENT_FILE_ACCESS

echo
echo "Document link repair exit: ${REPAIR_STATUS}"
echo "Hosted smoke exit: ${SMOKE_STATUS}"
echo "Diagnostics exit: ${DIAGNOSTICS_STATUS}"
echo "Safe refresh exit: ${REFRESH_STATUS}"
echo "Review reports/supabase_document_file_link_repair.md, reports/vercel_hosted_app_smoke.md, and reports/remote_production_readiness.md."
read -k 1 "?Press any key to close..."

if [[ "${REPAIR_STATUS}" -ne 0 || "${SMOKE_STATUS}" -ne 0 || "${DIAGNOSTICS_STATUS}" -ne 0 || "${REFRESH_STATUS}" -ne 0 ]]; then
  exit 1
fi
