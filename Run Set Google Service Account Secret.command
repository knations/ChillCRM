#!/bin/zsh
cd "/Users/kevinsvault/Downloads/ZendDeskSellProject" || exit 1

echo "CHILLCRM Google Service Account Secret Setup"
echo
echo "Copy the full Google service account JSON to your clipboard before continuing."
echo "It validates the JSON, then tries to save it as the GitHub secret:"
echo "GOOGLE_SERVICE_ACCOUNT_JSON"
echo
echo "The JSON will not be written to project files, reports, or chat."
echo
echo "Press Return after the JSON is copied to your clipboard."
read

.venv/bin/python scripts/set_github_actions_secret_from_clipboard.py GOOGLE_SERVICE_ACCOUNT_JSON

echo
echo "Press any key to close..."
read -k 1
