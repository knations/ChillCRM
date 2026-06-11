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
echo "- set the existing CHILLCRM Zapier webhook secret in the linked chillcrm Vercel project"
echo "- refresh Vercel environment and deployment status reports"
echo
echo "It will not deploy code, unlock writes, create users, switch source of truth, or change CRM records."
echo

echo "Type SET EXISTING ZAPIER SECRET to approve this Vercel environment update."
printf "Confirmation: "
read CONFIRMATION

if [[ "${CONFIRMATION}" != "SET EXISTING ZAPIER SECRET" ]]; then
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

printf "Existing Zapier webhook secret: "
stty -echo
read CHILLCRM_ZAPIER_WEBHOOK_SECRET
stty echo
echo

if [[ -z "${CHILLCRM_ZAPIER_WEBHOOK_SECRET}" ]]; then
  echo "Missing webhook secret. Exiting."
  unset VERCEL_TOKEN
  read -k 1 "?Press any key to close..."
  exit 1
fi

export VERCEL_TOKEN
export CHILLCRM_ZAPIER_WEBHOOK_SECRET
export PYTHONPYCACHEPREFIX="/private/tmp/chillcrm_pycache"

echo
echo "Setting Zapier webhook secret in Vercel..."
"${PYTHON_BIN}" scripts/set_vercel_zapier_webhook_secret.py --execute
SET_STATUS=$?

echo
echo "Refreshing environment and deployment reports..."
"${PYTHON_BIN}" scripts/verify_vercel_environment_readiness.py
ENV_STATUS=$?
"${PYTHON_BIN}" scripts/refresh_vercel_git_deployment_status.py
DEPLOYMENT_STATUS=$?

unset VERCEL_TOKEN
unset CHILLCRM_ZAPIER_WEBHOOK_SECRET

echo
echo "Webhook setup exit: ${SET_STATUS}"
echo "Environment readiness exit: ${ENV_STATUS}"
echo "Deployment status exit: ${DEPLOYMENT_STATUS}"
echo "Review reports/vercel_zapier_webhook_secret_status.md and reports/vercel_git_deployment_status.md."
read -k 1 "?Press any key to close..."

if [[ "${SET_STATUS}" -ne 0 || "${ENV_STATUS}" -ne 0 || "${DEPLOYMENT_STATUS}" -ne 0 ]]; then
  exit 1
fi
