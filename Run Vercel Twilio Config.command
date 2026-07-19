#!/bin/zsh
set -u

cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "CHILLCRM Vercel Twilio Config"
echo
echo "This will set Vercel environment variables for Twilio call recording:"
echo "- APP_BASE_URL"
echo "- CHILLCRM_TWILIO_AUTH_TOKEN"
echo "- CHILLCRM_TWILIO_PHONE_NUMBER"
echo "- CHILLCRM_TWILIO_FORWARD_TO"
echo
echo "It will not deploy code, change CRM records, expose secrets, or configure the Twilio phone-number webhook."
echo

echo "Type SET TWILIO CONFIG to approve this Vercel environment update."
printf "Confirmation: "
read CONFIRMATION

if [[ "${CONFIRMATION}" != "SET TWILIO CONFIG" ]]; then
  echo "Confirmation did not match. No Vercel setting will be changed."
  read -k 1 "?Press any key to close..."
  exit 1
fi

printf "Vercel API token: "
stty -echo
read VERCEL_TOKEN
stty echo
echo

if [[ -z "${VERCEL_TOKEN}" ]]; then
  echo "Missing Vercel token. Exiting."
  read -k 1 "?Press any key to close..."
  exit 1
fi

if [[ "${VERCEL_TOKEN}" != vcp_* && "${VERCEL_TOKEN}" != vck_* ]]; then
  echo
  echo "That does not look like a Vercel API token."
  echo "Use the token from Vercel Account Settings, not the project passcode."
  unset VERCEL_TOKEN
  read -k 1 "?Press any key to close..."
  exit 1
fi

printf "Twilio Auth Token: "
stty -echo
read CHILLCRM_TWILIO_AUTH_TOKEN
stty echo
echo

if [[ -z "${CHILLCRM_TWILIO_AUTH_TOKEN}" ]]; then
  echo "Missing Twilio Auth Token. Exiting."
  unset VERCEL_TOKEN
  read -k 1 "?Press any key to close..."
  exit 1
fi

printf "Twilio CRM phone number [6147146700]: "
read CHILLCRM_TWILIO_PHONE_NUMBER
if [[ -z "${CHILLCRM_TWILIO_PHONE_NUMBER}" ]]; then
  CHILLCRM_TWILIO_PHONE_NUMBER="6147146700"
fi

printf "Forward calls to phone number: "
read CHILLCRM_TWILIO_FORWARD_TO
if [[ -z "${CHILLCRM_TWILIO_FORWARD_TO}" ]]; then
  echo "Missing forward-to number. Exiting."
  unset VERCEL_TOKEN
  unset CHILLCRM_TWILIO_AUTH_TOKEN
  read -k 1 "?Press any key to close..."
  exit 1
fi

export VERCEL_TOKEN
export CHILLCRM_TWILIO_AUTH_TOKEN
export PYTHONPYCACHEPREFIX="/private/tmp/chillcrm_pycache"

echo
echo "Setting Twilio Vercel environment..."
"${PYTHON_BIN}" scripts/set_vercel_twilio_config.py --execute --forward-to "${CHILLCRM_TWILIO_FORWARD_TO}" --twilio-phone-number "${CHILLCRM_TWILIO_PHONE_NUMBER}"
SET_STATUS=$?

unset VERCEL_TOKEN
unset CHILLCRM_TWILIO_AUTH_TOKEN
unset CHILLCRM_TWILIO_PHONE_NUMBER
unset CHILLCRM_TWILIO_FORWARD_TO

echo
echo "Twilio Vercel config exit: ${SET_STATUS}"
echo "Review reports/vercel_twilio_config.md."
read -k 1 "?Press any key to close..."

if [[ "${SET_STATUS}" -ne 0 ]]; then
  exit 1
fi
