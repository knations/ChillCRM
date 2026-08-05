#!/bin/zsh
set -u

cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "CHILLCRM hosted smoke check"
echo
echo "This will:"
echo "- verify https://chillcrm.app using CHILLCRM app login"
echo "- use your CHILLCRM owner password only for the hosted login test"
echo "- verify https://chillcrm.app without redeploying"
echo "- refresh production readiness reports"
echo
echo "Nothing you type here is written to reports or chat."
echo
printf "CHILLCRM owner password: "
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

export AUTH_BOOTSTRAP_ADMIN_PASSWORD
export EXPECT_DOCUMENT_FILE_ACCESS="true"
export PYTHONPYCACHEPREFIX="/private/tmp/chillcrm_pycache"

echo "Running hosted smoke..."
echo
"${PYTHON_BIN}" scripts/run_newest_hosted_smoke_with_vercel_bypass.py \
  --url https://chillcrm.app \
  --no-vercel-bypass \
  --owner-email kevinnations@gmail.com
SMOKE_STATUS=$?

echo
echo "Refreshing safe production reports..."
"${PYTHON_BIN}" scripts/run_safe_production_gate_checks.py --refresh-only
REFRESH_STATUS=$?

unset AUTH_BOOTSTRAP_ADMIN_PASSWORD
unset EXPECT_DOCUMENT_FILE_ACCESS

echo
echo "Hosted smoke exit: ${SMOKE_STATUS}"
echo "Safe refresh exit: ${REFRESH_STATUS}"
echo "Review reports/vercel_hosted_app_smoke.md and reports/remote_production_readiness.md."
read -k 1 "?Press any key to close..."

if [[ "${SMOKE_STATUS}" -ne 0 || "${REFRESH_STATUS}" -ne 0 ]]; then
  exit 1
fi
