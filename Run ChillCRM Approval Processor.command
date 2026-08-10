#!/bin/zsh
cd "/Users/kevinsvault/Downloads/ZendDeskSellProject" || exit 1

echo "CHILLCRM Approval Processor"
echo
echo "This will read the current local approval snapshot and post only rows marked APPROVE."
echo "It uses CHILLCRM_AUTOMATION_TOKEN from macOS Keychain."
echo "If it is not saved yet, paste it once here and future runs will reuse it."
echo "The token will not be written to project files, shell history, reports, or chat."
echo

KEYCHAIN_SERVICE="CHILLCRM_AUTOMATION_TOKEN"
KEYCHAIN_ACCOUNT="$(whoami)"
CHILLCRM_AUTOMATION_TOKEN="$(security find-generic-password -a "$KEYCHAIN_ACCOUNT" -s "$KEYCHAIN_SERVICE" -w 2>/dev/null)"

if [[ -z "$CHILLCRM_AUTOMATION_TOKEN" ]]; then
  read -s "CHILLCRM_AUTOMATION_TOKEN?CHILLCRM_AUTOMATION_TOKEN: "
  echo
  if [[ -z "$CHILLCRM_AUTOMATION_TOKEN" ]]; then
    echo "No token entered. Nothing processed."
    echo
    echo "Press any key to close..."
    read -k 1
    exit 1
  fi
  security add-generic-password -a "$KEYCHAIN_ACCOUNT" -s "$KEYCHAIN_SERVICE" -w "$CHILLCRM_AUTOMATION_TOKEN" -U >/dev/null
  echo "Saved automation token to macOS Keychain for future runs."
else
  echo "Using automation token from macOS Keychain."
fi

export CHILLCRM_AUTOMATION_TOKEN

python3 scripts/process_sheet_approval_rows_once.py \
  --input reports/current_approval_queue_snapshot.json \
  --report reports/current_approval_processor_result.json \
  --base-url https://chillcrm.app

echo
echo "Press any key to close..."
read -k 1
