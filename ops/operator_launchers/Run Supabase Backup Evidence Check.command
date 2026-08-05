#!/bin/zsh
set -u

cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "CHILLCRM Supabase backup evidence check"
echo
echo "This will:"
echo "- record Supabase backup/PITR evidence using either dashboard facts or a private Management API token"
echo "- tie that evidence to the already-verified local rollback package and storage manifest"
echo "- refresh the production readiness reports"
echo
echo "It will not restore Supabase, unlock writes, change CRM records, switch source of truth, or store secrets."
echo

echo "Choose an evidence path:"
echo "1) Supabase Dashboard facts, no secret token"
echo "2) Supabase Management API token, hidden prompt"
echo
printf "Choice [1/2]: "
read CHOICE

export PYTHONPYCACHEPREFIX="/private/tmp/chillcrm_pycache"

if [[ "${CHOICE}" == "2" ]]; then
  echo
  echo "Use a Supabase Management API access token, not the service-role key, database password, or connection string."
  printf "Supabase Management API token: "
  stty -echo
  read SUPABASE_ACCESS_TOKEN
  stty echo
  echo

  if [[ -z "${SUPABASE_ACCESS_TOKEN}" ]]; then
    echo "Missing Supabase Management API token. Exiting."
    read -k 1 "?Press any key to close..."
    exit 1
  fi

  echo
  echo "Type APPROVE to use the current verified local rollback package plus the 203-file storage manifest as rollback proof."
  printf "Rollback proof approval: "
  read ROLLBACK_APPROVAL

  if [[ "${ROLLBACK_APPROVAL}" != "APPROVE" ]]; then
    echo "Approval did not match. No evidence report will be changed."
    unset SUPABASE_ACCESS_TOKEN
    read -k 1 "?Press any key to close..."
    exit 1
  fi

  export SUPABASE_ACCESS_TOKEN
  echo
  echo "Checking Supabase backup visibility..."
  "${PYTHON_BIN}" scripts/verify_supabase_backup_readiness.py \
    --restore-proof \
    --use-current-local-rollback-package \
    --restore-proof-owner "Kevin Nations" \
    --restore-notes "Owner approved the current local rollback package plus Supabase storage manifest as rollback proof."
  BACKUP_STATUS=$?
  unset SUPABASE_ACCESS_TOKEN
else
  echo
  echo "Open Supabase Dashboard > CHILLCRM project > Database > Backups."
  echo "Do not paste service-role keys, database passwords, JWTs, or connection strings here."
  echo

  printf "Do you see backups, restore controls, or a PITR path? Type YES: "
  read BACKUP_VISIBLE
  if [[ "${BACKUP_VISIBLE}" != "YES" ]]; then
    echo "Backup visibility was not confirmed. Exiting without changing the evidence report."
    read -k 1 "?Press any key to close..."
    exit 1
  fi

  printf "Latest backup timestamp shown, if any: "
  read LATEST_BACKUP_AT

  printf "Completed backup count shown, if any: "
  read COMPLETED_BACKUPS

  if [[ -n "${COMPLETED_BACKUPS}" && ! "${COMPLETED_BACKUPS}" =~ '^[0-9]+$' ]]; then
    echo "Completed backup count must be a number or blank. Exiting."
    read -k 1 "?Press any key to close..."
    exit 1
  fi

  printf "PITR enabled? Type yes, no, or unknown: "
  read PITR_ENABLED
  PITR_ENABLED="$(echo "${PITR_ENABLED}" | tr '[:upper:]' '[:lower:]')"
  if [[ "${PITR_ENABLED}" != "yes" && "${PITR_ENABLED}" != "no" && "${PITR_ENABLED}" != "unknown" ]]; then
    echo "PITR answer must be yes, no, or unknown. Exiting."
    read -k 1 "?Press any key to close..."
    exit 1
  fi

  printf "PITR recovery window shown, if any: "
  read PITR_WINDOW

  if [[ -z "${LATEST_BACKUP_AT}" && -z "${COMPLETED_BACKUPS}" && "${PITR_ENABLED}" != "yes" && -z "${PITR_WINDOW}" ]]; then
    echo "I need a latest backup timestamp, backup count, enabled PITR status, or PITR window. Exiting."
    read -k 1 "?Press any key to close..."
    exit 1
  fi

  echo
  echo "Type APPROVE to use the current verified local rollback package plus the 203-file storage manifest as rollback proof."
  printf "Rollback proof approval: "
  read ROLLBACK_APPROVAL
  if [[ "${ROLLBACK_APPROVAL}" != "APPROVE" ]]; then
    echo "Approval did not match. No evidence report will be changed."
    read -k 1 "?Press any key to close..."
    exit 1
  fi

  echo
  echo "Type CONFIRM to record that no live Supabase restore was run from this evidence check."
  printf "No-live-restore confirmation: "
  read NO_LIVE_RESTORE
  if [[ "${NO_LIVE_RESTORE}" != "CONFIRM" ]]; then
    echo "Confirmation did not match. No evidence report will be changed."
    read -k 1 "?Press any key to close..."
    exit 1
  fi

  BACKUP_ARGS=(
    --dashboard-backup-visible
    --dashboard-pitr-enabled "${PITR_ENABLED}"
    --dashboard-evidence-owner "Kevin Nations"
    --dashboard-notes "Owner confirmed Supabase Dashboard backup visibility; no live Supabase restore was run from this check."
    --restore-proof
    --use-current-local-rollback-package
    --restore-proof-owner "Kevin Nations"
    --restore-notes "Owner approved the current local rollback package plus Supabase storage manifest as rollback proof; no live Supabase restore was run."
  )

  if [[ -n "${LATEST_BACKUP_AT}" ]]; then
    BACKUP_ARGS+=(--dashboard-latest-backup-at "${LATEST_BACKUP_AT}")
  fi

  if [[ -n "${COMPLETED_BACKUPS}" ]]; then
    BACKUP_ARGS+=(--dashboard-completed-backups "${COMPLETED_BACKUPS}")
  fi

  if [[ -n "${PITR_WINDOW}" ]]; then
    BACKUP_ARGS+=(--dashboard-pitr-window "${PITR_WINDOW}")
  fi

  echo
  echo "Recording dashboard backup evidence..."
  "${PYTHON_BIN}" scripts/verify_supabase_backup_readiness.py "${BACKUP_ARGS[@]}"
  BACKUP_STATUS=$?
fi

echo
echo "Refreshing production readiness reports..."
"${PYTHON_BIN}" scripts/run_safe_production_gate_checks.py --refresh-only
REFRESH_STATUS=$?

echo
echo "Backup evidence exit: ${BACKUP_STATUS}"
echo "Readiness refresh exit: ${REFRESH_STATUS}"
echo "Review reports/supabase_backup_readiness.md and reports/remote_production_readiness.md."
read -k 1 "?Press any key to close..."

if [[ "${BACKUP_STATUS}" -ne 0 || "${REFRESH_STATUS}" -ne 0 ]]; then
  exit 1
fi
