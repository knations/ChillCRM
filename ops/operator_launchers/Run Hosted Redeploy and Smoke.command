#!/bin/zsh
set -u

cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "CHILLCRM hosted redeploy and smoke"
echo
echo "This will:"
echo "- use your Vercel API token only for this run"
echo "- deploy the current local hosted runtime to Vercel"
echo "- explicitly keep owner recovery disabled"
echo "- use your CHILLCRM owner password only for the https://chillcrm.app smoke login"
echo "- refresh deployment diagnostics and production readiness reports"
echo
echo "It does not change Supabase data, unlock hosted CRM writes, or switch source of truth."
echo "Nothing you type here is written to reports or chat."
echo

printf "Vercel API token: "
stty -echo
read VERCEL_TOKEN
stty echo
echo

if [[ -z "${VERCEL_TOKEN}" ]]; then
  echo "Missing Vercel token. Exiting."
  read -k 1 "?Press any key to close..."
  exit 1
fi

if [[ "${VERCEL_TOKEN}" != vcp_* && "${VERCEL_TOKEN}" != vck_* ]]; then
  echo
  echo "That does not look like a Vercel API token."
  echo "Use the token from Vercel Account Settings, not the project passcode."
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
  unset VERCEL_TOKEN
  read -k 1 "?Press any key to close..."
  exit 1
fi

if [[ "${AUTH_BOOTSTRAP_ADMIN_PASSWORD}" == "${VERCEL_TOKEN}" ]]; then
  echo "The owner password matched the Vercel token, which usually means the token was pasted twice."
  echo "No provider action will run. Please launch this again and enter the owner password at the second prompt."
  unset VERCEL_TOKEN
  unset AUTH_BOOTSTRAP_ADMIN_PASSWORD
  read -k 1 "?Press any key to close..."
  exit 1
fi

echo
echo "Type DEPLOY to deploy the current local hosted runtime and run smoke."
printf "Confirmation: "
read CONFIRMATION

if [[ "${CONFIRMATION}" != "DEPLOY" ]]; then
  echo "Confirmation did not match. No provider action will run."
  unset VERCEL_TOKEN
  unset AUTH_BOOTSTRAP_ADMIN_PASSWORD
  read -k 1 "?Press any key to close..."
  exit 1
fi

export VERCEL_TOKEN
export AUTH_BOOTSTRAP_ADMIN_PASSWORD
export EXPECT_DOCUMENT_FILE_ACCESS="true"
export CHILLCRM_SKIP_ENV_UPSERT="1"
export CHILLCRM_VERCEL_INLINE_FILES="1"
export CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED="false"
export PYTHONPYCACHEPREFIX="/private/tmp/chillcrm_pycache"

echo
echo "Running hosted redeploy preflight..."
"${PYTHON_BIN}" scripts/verify_hosted_redeploy_preflight.py
PREFLIGHT_STATUS=$?

echo
echo "Deploying current local hosted runtime..."
"${PYTHON_BIN}" scripts/deploy_chillcrm_to_vercel.py
DEPLOY_STATUS=$?

echo
echo "Running hosted smoke..."
"${PYTHON_BIN}" scripts/run_newest_hosted_smoke_with_vercel_bypass.py \
  --url https://chillcrm.app \
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

unset VERCEL_TOKEN
unset AUTH_BOOTSTRAP_ADMIN_PASSWORD
unset EXPECT_DOCUMENT_FILE_ACCESS
unset CHILLCRM_SKIP_ENV_UPSERT
unset CHILLCRM_VERCEL_INLINE_FILES
unset CHILLCRM_OWNER_PASSWORD_RECOVERY_ENABLED

echo
echo "Redeploy preflight exit: ${PREFLIGHT_STATUS}"
echo "Deploy exit: ${DEPLOY_STATUS}"
echo "Hosted smoke exit: ${SMOKE_STATUS}"
echo "Diagnostics exit: ${DIAGNOSTICS_STATUS}"
echo "Safe refresh exit: ${REFRESH_STATUS}"
echo "Review reports/vercel_staging_deployment_status.md, reports/vercel_hosted_app_smoke.md, and reports/remote_production_readiness.md."
read -k 1 "?Press any key to close..."

if [[ "${PREFLIGHT_STATUS}" -ne 0 || "${DEPLOY_STATUS}" -ne 0 || "${SMOKE_STATUS}" -ne 0 || "${DIAGNOSTICS_STATUS}" -ne 0 || "${REFRESH_STATUS}" -ne 0 ]]; then
  exit 1
fi
