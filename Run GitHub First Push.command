#!/bin/zsh
set -u

cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "CHILLCRM GitHub first push"
echo
echo "This pushes the clean local main branch to GitHub origin:"
git remote get-url origin 2>/dev/null || true
echo
echo "It will not commit databases, backups, raw exports, reports, .vercel, .venv, or local CRM data."
echo "It will not store the GitHub token in git config, files, shell history, or reports."
echo

echo "Running GitHub readiness check..."
export PYTHONPYCACHEPREFIX="/private/tmp/chillcrm_pycache"
"${PYTHON_BIN}" scripts/verify_github_readiness.py
READY_STATUS=$?

if [[ "${READY_STATUS}" -ne 0 ]]; then
  echo
  echo "GitHub readiness failed. No push will be attempted."
  read -k 1 "?Press any key to close..."
  exit 1
fi

echo
echo "Local commits to push:"
git log --oneline --decorate -5
echo

echo "Type PUSH CHILLCRM to approve pushing main to GitHub."
printf "Confirmation: "
read CONFIRMATION

if [[ "${CONFIRMATION}" != "PUSH CHILLCRM" ]]; then
  echo "Confirmation did not match. No push performed."
  read -k 1 "?Press any key to close..."
  exit 1
fi

printf "GitHub personal access token: "
stty -echo
read GITHUB_TOKEN
stty echo
echo

if [[ -z "${GITHUB_TOKEN}" ]]; then
  echo "Missing GitHub token. Exiting."
  read -k 1 "?Press any key to close..."
  exit 1
fi

AUTH_HEADER="$(printf 'x-access-token:%s' "${GITHUB_TOKEN}" | base64 | tr -d '\n')"

echo
echo "Pushing to GitHub..."
git -c "http.https://github.com/.extraheader=AUTHORIZATION: basic ${AUTH_HEADER}" push -u origin main
PUSH_STATUS=$?

unset GITHUB_TOKEN
unset AUTH_HEADER

echo
echo "GitHub push exit: ${PUSH_STATUS}"
if [[ "${PUSH_STATUS}" -eq 0 ]]; then
  echo "Push completed. Vercel should now receive the main branch from the connected GitHub repo."
else
  echo "Push did not complete. Check token permissions for repository contents read/write."
fi

read -k 1 "?Press any key to close..."
exit "${PUSH_STATUS}"
