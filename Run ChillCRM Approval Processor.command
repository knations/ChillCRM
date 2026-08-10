#!/bin/zsh
cd "/Users/kevinsvault/Downloads/ZendDeskSellProject" || exit 1

echo "CHILLCRM Approval Processor"
echo
echo "This will read the current local approval snapshot and post only rows marked APPROVE."
echo "It will ask for CHILLCRM_AUTOMATION_TOKEN privately."
echo "The token will not be written to files, shell history, reports, or chat."
echo

python3 scripts/process_sheet_approval_rows_once.py \
  --input reports/current_approval_queue_snapshot.json \
  --report reports/current_approval_processor_result.json \
  --base-url https://chillcrm.app

echo
echo "Press any key to close..."
read -k 1
