#!/bin/zsh
cd "/Users/kevinsvault/Downloads/ZendDeskSellProject" || exit 1

echo "CHILLCRM Clean Task Source Blocks"
echo
echo "This removes pasted Source links from visible task text."
echo "The source data is preserved in task metadata, not deleted."
echo "Paste the production Supabase/Postgres DATABASE_URL."
echo "It will be used only for this run and will not be written to files."
echo

read -s "DATABASE_URL?DATABASE_URL: "
echo
export DATABASE_URL

echo
echo "Type exactly: CLEAN TASK SOURCE BLOCKS"
read "CONFIRMATION?Confirmation: "

python3 scripts/clean_task_source_blocks.py \
  --execute \
  --confirm "$CONFIRMATION"

echo
echo "Press any key to close..."
read -k 1
