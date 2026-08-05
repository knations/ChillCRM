#!/bin/zsh
set -u

cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "CHILLCRM hosted write-audit rehearsal"
echo
echo "This is the controlled staging write test."
echo
echo "It will:"
echo "- use your Vercel API token only for this run"
echo "- temporarily deploy hosted staging with REMOTE_WRITE_LOCK off"
echo "- sign in with the CHILLCRM owner account"
echo "- create one staging-only probe person"
echo "- verify the actor-aware audit row"
echo "- immediately redeploy with REMOTE_WRITE_LOCK on"
echo "- verify writes are blocked again and refresh hosted smoke/readiness reports"
echo
echo "It will not switch source of truth or store secrets."
echo "Do not run this until the Supabase backup/PITR evidence gate is recorded."
echo

echo "Type APPROVE WRITE AUDIT to approve the temporary staging write rehearsal."
printf "Approval: "
read APPROVAL

if [[ "${APPROVAL}" != "APPROVE WRITE AUDIT" ]]; then
  echo "Approval did not match. No hosted write rehearsal will run."
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

printf "CHILLCRM owner password: "
stty -echo
read AUTH_BOOTSTRAP_ADMIN_PASSWORD
stty echo
echo

if [[ -z "${AUTH_BOOTSTRAP_ADMIN_PASSWORD}" ]]; then
  echo "Missing owner password. Exiting."
  unset VERCEL_TOKEN
  read -k 1 "?Press any key to close..."
  exit 1
fi

if [[ "${AUTH_BOOTSTRAP_ADMIN_PASSWORD}" == "${VERCEL_TOKEN}" ]]; then
  echo "The owner password matched the Vercel token, which usually means the token was pasted twice."
  echo "No provider action will run. Please launch this again and enter the owner password at the second prompt."
  unset VERCEL_TOKEN
  unset AUTH_BOOTSTRAP_ADMIN_PASSWORD
  read -k 1 "?Press any key to close..."
  exit 1
fi

echo
echo "Type RUN AUDIT to begin the temporary unlock, probe write, audit check, and relock."
printf "Final confirmation: "
read FINAL_CONFIRMATION

if [[ "${FINAL_CONFIRMATION}" != "RUN AUDIT" ]]; then
  echo "Confirmation did not match. No hosted write rehearsal will run."
  unset VERCEL_TOKEN
  unset AUTH_BOOTSTRAP_ADMIN_PASSWORD
  read -k 1 "?Press any key to close..."
  exit 1
fi

export VERCEL_TOKEN
export AUTH_BOOTSTRAP_ADMIN_PASSWORD
export AUTH_BOOTSTRAP_ADMIN_EMAIL="kevinnations@gmail.com"
export PYTHONPYCACHEPREFIX="/private/tmp/chillcrm_pycache"

echo
echo "Running the guarded write-audit rehearsal..."
"${PYTHON_BIN}" scripts/execute_hosted_write_audit_rehearsal.py \
  --owner-approved \
  --execute \
  --owner-email "kevinnations@gmail.com"
AUDIT_STATUS=$?

unset VERCEL_TOKEN
unset AUTH_BOOTSTRAP_ADMIN_PASSWORD
unset AUTH_BOOTSTRAP_ADMIN_EMAIL

echo
echo "Hosted write-audit exit: ${AUDIT_STATUS}"
echo "Review reports/hosted_write_audit_execution.md and reports/hosted_write_unlock_audit_rehearsal.md."
read -k 1 "?Press any key to close..."

if [[ "${AUDIT_STATUS}" -ne 0 ]]; then
  exit 1
fi
