#!/bin/zsh
set -u

cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "CHILLCRM Vercel Git deployment refresh"
echo
echo "This will:"
echo "- use your Vercel API token only for this run"
echo "- read the latest GitHub-backed production deployment from Vercel"
echo "- refresh deployment status, diagnostics, and safe production reports"
echo
echo "It does not deploy code, change Supabase data, unlock hosted CRM writes, or switch source of truth."
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

export VERCEL_TOKEN
export PYTHONPYCACHEPREFIX="/private/tmp/chillcrm_pycache"

echo
echo "Verifying Vercel Git connection..."
"${PYTHON_BIN}" scripts/verify_vercel_git_connection.py
GIT_STATUS=$?

echo
echo "Refreshing latest Git deployment status..."
"${PYTHON_BIN}" scripts/refresh_vercel_git_deployment_status.py
DEPLOYMENT_STATUS=$?

echo
echo "Refreshing Vercel deployment diagnostics..."
"${PYTHON_BIN}" scripts/inspect_vercel_deployment.py
DIAGNOSTICS_STATUS=$?

echo
echo "Refreshing safe production reports..."
"${PYTHON_BIN}" scripts/run_safe_production_gate_checks.py --refresh-only
REFRESH_STATUS=$?

unset VERCEL_TOKEN

echo
echo "Git connection exit: ${GIT_STATUS}"
echo "Deployment status exit: ${DEPLOYMENT_STATUS}"
echo "Diagnostics exit: ${DIAGNOSTICS_STATUS}"
echo "Safe refresh exit: ${REFRESH_STATUS}"
echo "Review reports/vercel_git_deployment_status.md, reports/vercel_staging_deployment_status.md, and reports/remote_production_readiness.md."
read -k 1 "?Press any key to close..."

if [[ "${GIT_STATUS}" -ne 0 || "${DEPLOYMENT_STATUS}" -ne 0 || "${DIAGNOSTICS_STATUS}" -ne 0 || "${REFRESH_STATUS}" -ne 0 ]]; then
  exit 1
fi
