#!/bin/zsh
cd "/Users/kevinsvault/Downloads/ZendDeskSellProject" || exit 1

echo "CHILLCRM Automation Token Secret Setup"
echo
echo "Copy the CHILLCRM_AUTOMATION_TOKEN to your clipboard before continuing."
echo "It validates the token, then tries to save it as the GitHub secret:"
echo "CHILLCRM_AUTOMATION_TOKEN"
echo
echo "The token will not be written to project files, reports, or chat."
echo
echo "Press Return after the token is copied to your clipboard."
read

.venv/bin/python scripts/set_github_actions_secret_from_clipboard.py CHILLCRM_AUTOMATION_TOKEN

echo
echo "Press any key to close..."
read -k 1
