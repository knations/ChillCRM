#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "CHILLCRM owner recovery disable wave"
echo
echo "This will:"
echo "- use your Vercel token only for this run"
echo "- use your owner password only for the hosted smoke test"
echo "- disable the temporary owner password recovery switch"
echo "- redeploy CHILLCRM to Vercel"
echo "- refresh production readiness reports"
echo
echo "Nothing you type here is written to reports or chat."
echo

printf "Vercel token: "
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
  echo "That does not look like the expected Vercel token format. Vercel tokens commonly start with vcp_ or vck_."
  echo "If this is not the token you intended, close this window and run the launcher again."
  echo
fi

echo "Vercel token received. Next: enter your CHILLCRM owner password."
echo
printf "Owner password: "
stty -echo
read AUTH_BOOTSTRAP_ADMIN_PASSWORD
stty echo
echo
echo

if [[ -z "${AUTH_BOOTSTRAP_ADMIN_PASSWORD}" ]]; then
  echo "Missing owner password. Exiting."
  read -k 1 "?Press any key to close..."
  exit 1
fi

if [[ "${AUTH_BOOTSTRAP_ADMIN_PASSWORD}" == "${VERCEL_TOKEN}" ]]; then
  echo "The owner password matched the Vercel token, which usually means the token was pasted twice."
  echo "No provider action will run. Please launch this again and enter the owner password at the second prompt."
  read -k 1 "?Press any key to close..."
  exit 1
fi

echo "Owner password received. Starting the production wave..."
echo
export VERCEL_TOKEN
export AUTH_BOOTSTRAP_ADMIN_PASSWORD
export PYTHONPYCACHEPREFIX="/private/tmp/chillcrm_pycache"

"${PYTHON_BIN}" scripts/run_owner_confirmed_production_wave.py \
  --owner-confirmed-access \
  --execute-owner-recovery-wave

echo
echo "Refreshing final safe reports..."
"${PYTHON_BIN}" scripts/run_safe_production_gate_checks.py --refresh-only

unset VERCEL_TOKEN
unset AUTH_BOOTSTRAP_ADMIN_PASSWORD

echo
echo "Done. Review reports/owner_recovery_disable_run.md and reports/remote_production_readiness.md."
read -k 1 "?Press any key to close..."
