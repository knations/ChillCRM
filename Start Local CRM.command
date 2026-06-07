#!/bin/zsh
cd "$(dirname "$0")"
echo "Starting the local CRM..."
echo
python3 crm_app/server.py --host 127.0.0.1 --port 8765 --auto-port --open
