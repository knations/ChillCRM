#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "CHILLCRM Vercel token access check"
echo
echo "This will:"
echo "- use your Vercel API token only for this check"
echo "- verify access to the linked chillcrm Vercel project"
echo "- verify read access to Vercel environment metadata"
echo
echo "It will not deploy, update environment variables, or store the token."
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
echo "Checking token access..."
echo

"${PYTHON_BIN}" scripts/verify_vercel_token_access.py

unset VERCEL_TOKEN

echo
echo "Done. Review reports/vercel_token_access_check.md."
read -k 1 "?Press any key to close..."
