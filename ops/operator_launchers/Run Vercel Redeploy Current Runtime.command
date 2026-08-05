#!/bin/zsh
set -u

cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "CHILLCRM Vercel redeploy current runtime"
echo
echo "This will:"
echo "- use your Vercel API token only for this run"
echo "- redeploy the current local hosted runtime to the linked chillcrm Vercel project"
echo "- preserve existing Vercel environment variables"
echo "- refresh deployment diagnostics and status reports"
echo
echo "It will not unlock writes, create users, switch source of truth, or change CRM records."
echo

echo "Type REDEPLOY CURRENT RUNTIME to approve this Vercel redeploy."
printf "Confirmation: "
read CONFIRMATION
CONFIRMATION="$(printf '%s' "${CONFIRMATION}" | tr -s '[:space:]' ' ' | sed 's/^ //; s/ $//' | tr '[:lower:]' '[:upper:]')"

if [[ "${CONFIRMATION}" != "REDEPLOY CURRENT RUNTIME" ]]; then
  echo "Confirmation did not match. No provider action will run."
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

export VERCEL_TOKEN
export CHILLCRM_SKIP_ENV_UPSERT="1"
export CHILLCRM_VERCEL_INLINE_FILES="1"
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
echo "Refreshing Vercel deployment diagnostics..."
"${PYTHON_BIN}" scripts/inspect_vercel_deployment.py
DIAGNOSTICS_STATUS=$?

echo
echo "Refreshing Vercel Git deployment status..."
"${PYTHON_BIN}" scripts/refresh_vercel_git_deployment_status.py
DEPLOYMENT_STATUS=$?

unset VERCEL_TOKEN
unset CHILLCRM_SKIP_ENV_UPSERT
unset CHILLCRM_VERCEL_INLINE_FILES

echo
echo "Redeploy preflight exit: ${PREFLIGHT_STATUS}"
echo "Deploy exit: ${DEPLOY_STATUS}"
echo "Diagnostics exit: ${DIAGNOSTICS_STATUS}"
echo "Deployment status exit: ${DEPLOYMENT_STATUS}"
echo "Review reports/vercel_staging_deployment_status.md and reports/vercel_deployment_diagnostics.md."
read -k 1 "?Press any key to close..."

if [[ "${PREFLIGHT_STATUS}" -ne 0 || "${DEPLOY_STATUS}" -ne 0 || "${DIAGNOSTICS_STATUS}" -ne 0 || "${DEPLOYMENT_STATUS}" -ne 0 ]]; then
  exit 1
fi
