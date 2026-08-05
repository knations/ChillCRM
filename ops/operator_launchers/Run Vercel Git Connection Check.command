#!/bin/zsh
set -u

cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "CHILLCRM Vercel Git connection check"
echo
echo "This verifies whether the Vercel project is connected to a GitHub repository."
echo
echo "It will not push to GitHub, deploy code, change Vercel settings, unlock writes, expose secrets, or change CRM records."
echo

printf "Optional expected GitHub repo, like owner/CHILLCRM. Leave blank if you only want to verify whatever Vercel shows: "
read EXPECTED_REPO

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
  echo "Use a Vercel API token, not the project passcode."
  unset VERCEL_TOKEN
  read -k 1 "?Press any key to close..."
  exit 1
fi

export VERCEL_TOKEN
export PYTHONPYCACHEPREFIX="/private/tmp/chillcrm_pycache"

echo
echo "Checking Vercel Git connection..."
if [[ -n "${EXPECTED_REPO}" ]]; then
  "${PYTHON_BIN}" scripts/verify_vercel_git_connection.py --expected-repo "${EXPECTED_REPO}"
else
  "${PYTHON_BIN}" scripts/verify_vercel_git_connection.py
fi
CHECK_STATUS=$?

unset VERCEL_TOKEN

echo
echo "Vercel Git connection check exit: ${CHECK_STATUS}"
echo "Review reports/vercel_git_connection.md."
read -k 1 "?Press any key to close..."

exit "${CHECK_STATUS}"
