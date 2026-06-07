#!/bin/zsh
set -u

cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "CHILLCRM Vercel APP_BASE_URL cleanup"
echo
echo "This will set APP_BASE_URL=https://chillcrm.app in Vercel for production, preview, and development."
echo
echo "It will not deploy code, unlock writes, create users, switch source of truth, expose secrets, or change CRM records."
echo

echo "Type SET APP BASE URL to approve this Vercel environment cleanup."
printf "Confirmation: "
read CONFIRMATION

if [[ "${CONFIRMATION}" != "SET APP BASE URL" ]]; then
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
echo "Setting APP_BASE_URL..."
"${PYTHON_BIN}" scripts/set_vercel_app_base_url.py --execute
SET_STATUS=$?

echo
echo "Refreshing environment and custom-domain reports..."
"${PYTHON_BIN}" scripts/verify_vercel_environment_readiness.py
ENV_STATUS=$?
"${PYTHON_BIN}" scripts/verify_custom_domain_readiness.py
DOMAIN_STATUS=$?
"${PYTHON_BIN}" scripts/verify_remote_production_readiness.py
PRODUCTION_STATUS=$?

unset VERCEL_TOKEN

echo
echo "APP_BASE_URL cleanup exit: ${SET_STATUS}"
echo "Environment readiness exit: ${ENV_STATUS}"
echo "Custom domain readiness exit: ${DOMAIN_STATUS}"
echo "Production readiness exit: ${PRODUCTION_STATUS}"
echo "Review reports/vercel_app_base_url_cleanup.md and reports/custom_domain_readiness.md."
read -k 1 "?Press any key to close..."

if [[ "${SET_STATUS}" -ne 0 || "${ENV_STATUS}" -ne 0 || "${DOMAIN_STATUS}" -ne 0 || "${PRODUCTION_STATUS}" -ne 0 ]]; then
  exit 1
fi
