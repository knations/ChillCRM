#!/bin/zsh
cd "/Users/kevinsvault/Downloads/ZendDeskSellProject" || exit 1

echo "CHILLCRM Delete Duplicate Automation Tasks"
echo
echo "This deletes only the approved accidental duplicate task IDs: 29 and 30."
echo "It preserves the original Aaron and Liana tasks and does not touch other CRM data."
echo
echo "It uses the production Supabase/Postgres DATABASE_URL from macOS Keychain."
echo "If it is not saved yet, paste it once here and future maintenance runs will reuse it."
echo "Recommended format:"
echo "postgresql://postgres.ckjbnummsxqcyeahzynz:YOUR-PASSWORD@aws-1-us-east-2.pooler.supabase.com:5432/postgres"
echo
echo "The URL will not be written to project files, shell history, reports, or chat."
echo

KEYCHAIN_SERVICE="CHILLCRM_DATABASE_URL"
KEYCHAIN_ACCOUNT="$(whoami)"
DATABASE_URL="$(security find-generic-password -a "$KEYCHAIN_ACCOUNT" -s "$KEYCHAIN_SERVICE" -w 2>/dev/null)"

if [[ -z "$DATABASE_URL" ]]; then
  read -s "DATABASE_URL?DATABASE_URL: "
  echo
  if [[ -z "$DATABASE_URL" ]]; then
    echo "No database URL entered. Nothing changed."
    echo
    echo "Press any key to close..."
    read -k 1
    exit 1
  fi
  security add-generic-password -a "$KEYCHAIN_ACCOUNT" -s "$KEYCHAIN_SERVICE" -w "$DATABASE_URL" -U >/dev/null
  echo "Saved database URL to macOS Keychain for future maintenance runs."
else
  echo "Using database URL from macOS Keychain."
fi

export DATABASE_URL

echo
echo "Type exactly: DELETE DUPLICATE TASKS 29 30"
read "CONFIRMATION?Confirmation: "

.venv/bin/python scripts/delete_duplicate_automation_tasks.py \
  --execute \
  --ssl-root-cert "config/supabase-prod-ca-2021.crt" \
  --confirm "$CONFIRMATION"

echo
echo "Press any key to close..."
read -k 1
