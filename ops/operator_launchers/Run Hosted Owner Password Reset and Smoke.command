#!/bin/zsh
set -u

cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "CHILLCRM hosted owner password reset and smoke"
echo
echo "This will:"
echo "- use your Supabase database password only for this run"
echo "- set a new CHILLCRM owner password for kevinnations@gmail.com on hosted Supabase"
echo "- keep owner/admin roles active for that account"
echo "- run the newest hosted smoke check with the new password"
echo "- refresh production readiness reports"
echo
echo "It does not unlock hosted CRM writes or make hosted Supabase the source of truth."
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

printf "New CHILLCRM owner password: "
stty -echo
read CHILLCRM_APP_USER_PASSWORD
stty echo
echo

printf "Confirm new CHILLCRM owner password: "
stty -echo
read CHILLCRM_APP_USER_PASSWORD_CONFIRM
stty echo
echo
echo

if [[ -z "${CHILLCRM_APP_USER_PASSWORD}" ]]; then
  echo "Missing new owner password. Exiting."
  unset SUPABASE_DB_PASSWORD
  read -k 1 "?Press any key to close..."
  exit 1
fi

if [[ "${CHILLCRM_APP_USER_PASSWORD}" != "${CHILLCRM_APP_USER_PASSWORD_CONFIRM}" ]]; then
  echo "Passwords did not match. Exiting."
  unset SUPABASE_DB_PASSWORD
  unset CHILLCRM_APP_USER_PASSWORD
  unset CHILLCRM_APP_USER_PASSWORD_CONFIRM
  read -k 1 "?Press any key to close..."
  exit 1
fi

if [[ "${#CHILLCRM_APP_USER_PASSWORD}" -lt 12 ]]; then
  echo "Use at least 12 characters. Exiting."
  unset SUPABASE_DB_PASSWORD
  unset CHILLCRM_APP_USER_PASSWORD
  unset CHILLCRM_APP_USER_PASSWORD_CONFIRM
  read -k 1 "?Press any key to close..."
  exit 1
fi

printf "Verified Vercel API token: "
stty -echo
read VERCEL_TOKEN
stty echo
echo

if [[ -z "${VERCEL_TOKEN}" ]]; then
  echo "Missing Vercel token. Exiting."
  unset SUPABASE_DB_PASSWORD
  unset CHILLCRM_APP_USER_PASSWORD
  unset CHILLCRM_APP_USER_PASSWORD_CONFIRM
  read -k 1 "?Press any key to close..."
  exit 1
fi

if [[ "${VERCEL_TOKEN}" != vcp_* && "${VERCEL_TOKEN}" != vck_* ]]; then
  echo "That does not look like a Vercel API token. Exiting."
  unset SUPABASE_DB_PASSWORD
  unset CHILLCRM_APP_USER_PASSWORD
  unset CHILLCRM_APP_USER_PASSWORD_CONFIRM
  unset VERCEL_TOKEN
  read -k 1 "?Press any key to close..."
  exit 1
fi

echo
echo "Type RESET to set the hosted owner password and run smoke."
printf "Confirmation: "
read CONFIRMATION

if [[ "${CONFIRMATION}" != "RESET" ]]; then
  echo "Confirmation did not match. No hosted password change will run."
  unset SUPABASE_DB_PASSWORD
  unset CHILLCRM_APP_USER_PASSWORD
  unset CHILLCRM_APP_USER_PASSWORD_CONFIRM
  unset VERCEL_TOKEN
  read -k 1 "?Press any key to close..."
  exit 1
fi

export SUPABASE_DB_PASSWORD
ENCODED_PASSWORD="$("${PYTHON_BIN}" -c 'import os, urllib.parse; print(urllib.parse.quote(os.environ["SUPABASE_DB_PASSWORD"], safe=""))')"
unset SUPABASE_DB_PASSWORD
export DATABASE_URL="postgresql://postgres.ckjbnummsxqcyeahzynz:${ENCODED_PASSWORD}@aws-1-us-east-2.pooler.supabase.com:5432/postgres"
unset ENCODED_PASSWORD
export CHILLCRM_SSLROOTCERT="config/supabase-prod-ca-2021.crt"
export CHILLCRM_APP_USER_PASSWORD
export VERCEL_TOKEN
export AUTH_BOOTSTRAP_ADMIN_PASSWORD="${CHILLCRM_APP_USER_PASSWORD}"
export EXPECT_DOCUMENT_FILE_ACCESS="true"
export PYTHONPYCACHEPREFIX="/private/tmp/chillcrm_pycache"
unset CHILLCRM_APP_USER_PASSWORD_CONFIRM

echo
echo "Resetting hosted owner password..."
"${PYTHON_BIN}" scripts/reset_app_user_password.py \
  --hosted \
  --email kevinnations@gmail.com \
  --display-name "Kevin Nations" \
  --owner
RESET_STATUS=$?

echo
echo "Running hosted smoke with the new owner password..."
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

unset DATABASE_URL
unset CHILLCRM_SSLROOTCERT
unset CHILLCRM_APP_USER_PASSWORD
unset AUTH_BOOTSTRAP_ADMIN_PASSWORD
unset VERCEL_TOKEN
unset EXPECT_DOCUMENT_FILE_ACCESS

echo
echo "Password reset exit: ${RESET_STATUS}"
echo "Hosted smoke exit: ${SMOKE_STATUS}"
echo "Diagnostics exit: ${DIAGNOSTICS_STATUS}"
echo "Safe refresh exit: ${REFRESH_STATUS}"
echo "Review reports/vercel_hosted_app_smoke.md and reports/remote_production_readiness.md."
read -k 1 "?Press any key to close..."

if [[ "${RESET_STATUS}" -ne 0 || "${SMOKE_STATUS}" -ne 0 || "${DIAGNOSTICS_STATUS}" -ne 0 || "${REFRESH_STATUS}" -ne 0 ]]; then
  exit 1
fi
