#!/bin/zsh
set -u

cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "CHILLCRM Vercel Zapier webhook setup"
echo
echo "This will:"
echo "- generate a new CHILLCRM Zapier webhook secret for you"
echo "- upsert that secret into the linked chillcrm Vercel project"
echo "- refresh Vercel environment and deployment status reports"
echo
echo "It will not deploy code, unlock writes, create users, expose Supabase secrets, switch source of truth, or change CRM records."
echo

echo "Type SET ZAPIER WEBHOOK to approve this Vercel environment update."
printf "Confirmation: "
read CONFIRMATION

if [[ "${CONFIRMATION}" != "SET ZAPIER WEBHOOK" ]]; then
  echo "Confirmation did not match. No Vercel setting will be changed."
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
export PYTHONPYCACHEPREFIX="/private/tmp/chillcrm_pycache"

echo
echo "Setting Zapier webhook secret in Vercel..."
"${PYTHON_BIN}" scripts/set_vercel_zapier_webhook_secret.py --execute --generate-secret
SET_STATUS=$?

echo
echo "Refreshing environment and deployment reports..."
"${PYTHON_BIN}" scripts/verify_vercel_environment_readiness.py
ENV_STATUS=$?
"${PYTHON_BIN}" scripts/refresh_vercel_git_deployment_status.py
DEPLOYMENT_STATUS=$?

unset VERCEL_TOKEN

echo
echo "Webhook setup exit: ${SET_STATUS}"
echo "Environment readiness exit: ${ENV_STATUS}"
echo "Deployment status exit: ${DEPLOYMENT_STATUS}"
echo "Review reports/vercel_zapier_webhook_secret_status.md and reports/vercel_git_deployment_status.md."
read -k 1 "?Press any key to close..."

if [[ "${SET_STATUS}" -ne 0 || "${ENV_STATUS}" -ne 0 || "${DEPLOYMENT_STATUS}" -ne 0 ]]; then
  exit 1
fi
