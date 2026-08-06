#!/bin/zsh
set -euo pipefail

cd "/Users/kevinsvault/Downloads/ZendDeskSellProject"

echo "CHILLCRM Delete Unlinked Calls/Texts"
echo
echo "This deletes only unlinked call/text history rows:"
echo "- 373 unlinked calls expected"
echo "- 99 unlinked text messages expected"
echo "- linked records and documents are excluded"
echo
echo "Paste the production Supabase/Postgres DATABASE_URL."
echo "It will be used only for this run and will not be written to project files."
printf "DATABASE_URL: "
stty -echo
read DATABASE_URL_INPUT
stty echo
echo
echo
echo "Type exactly: DELETE UNLINKED CALLS TEXTS"
printf "Confirmation: "
read CONFIRMATION_INPUT
echo

CHILLCRM_DATABASE_URL="$DATABASE_URL_INPUT" \
.venv/bin/python scripts/delete_unlinked_call_text_history.py \
  --execute \
  --ssl-root-cert "config/supabase-prod-ca-2021.crt" \
  --confirm "$CONFIRMATION_INPUT" \
  --actor "Kevin Nations"

echo
echo "Cleanup finished. Review the newest reports/unlinked_call_text_history_cleanup_*.md file."
echo "Press any key to close..."
read -k 1 _
