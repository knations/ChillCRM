#!/bin/zsh
cd "/Users/kevinsvault/Downloads/ZendDeskSellProject" || exit 1

echo "CHILLCRM Verify Duplicate Automation Tasks"
echo
echo "This checks whether duplicate task IDs 29 and 30 still exist."
echo "It does not delete or change any CRM data."
echo "It uses the production Supabase/Postgres DATABASE_URL from macOS Keychain."
echo "If it is not saved yet, paste it once here and future maintenance runs will reuse it."
echo

KEYCHAIN_SERVICE="CHILLCRM_DATABASE_URL"
KEYCHAIN_ACCOUNT="$(whoami)"
DATABASE_URL="$(security find-generic-password -a "$KEYCHAIN_ACCOUNT" -s "$KEYCHAIN_SERVICE" -w 2>/dev/null)"

if [[ -z "$DATABASE_URL" ]]; then
  read -s "DATABASE_URL?DATABASE_URL: "
  echo
  if [[ -z "$DATABASE_URL" ]]; then
    echo "No database URL entered. Nothing checked."
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

.venv/bin/python scripts/delete_duplicate_automation_tasks.py \
  --ssl-root-cert "config/supabase-prod-ca-2021.crt"

echo
echo "If the output says missing task IDs 29 and 30, that means the duplicates are already gone."
echo "Press any key to close..."
read -k 1
