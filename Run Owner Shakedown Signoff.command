#!/bin/zsh
set -u

cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "CHILLCRM owner shakedown signoff"
echo
echo "This records owner acceptance of the staged hosted CRM after the prerequisite gates are green."
echo
echo "It will not unlock writes, change provider settings, switch source of truth, expose secrets, or change CRM records."
echo "The script will refuse to pass if hosted smoke, Supabase backup proof, write-audit rehearsal, or monitoring readiness are still open."
echo

printf "Signoff owner [Kevin Nations]: "
read SIGNOFF_OWNER
if [[ -z "${SIGNOFF_OWNER}" ]]; then
  SIGNOFF_OWNER="Kevin Nations"
fi

printf "Short non-secret note [Owner shakedown accepted for cutover review.]: "
read SIGNOFF_NOTE
if [[ -z "${SIGNOFF_NOTE}" ]]; then
  SIGNOFF_NOTE="Owner shakedown accepted for cutover review."
fi

echo
echo "Type APPROVE SHAKEDOWN to record owner shakedown signoff, if prerequisites are green."
printf "Confirmation: "
read CONFIRMATION

if [[ "${CONFIRMATION}" != "APPROVE SHAKEDOWN" ]]; then
  echo "Confirmation did not match. No shakedown signoff will be recorded."
  read -k 1 "?Press any key to close..."
  exit 1
fi

export PYTHONPYCACHEPREFIX="/private/tmp/chillcrm_pycache"

echo
echo "Recording owner shakedown signoff..."
"${PYTHON_BIN}" scripts/record_owner_shakedown_signoff.py \
  --signoff-owner "${SIGNOFF_OWNER}" \
  --approve \
  --notes "${SIGNOFF_NOTE}"
SHAKEDOWN_STATUS=$?

echo
echo "Refreshing source-of-truth preflight and production readiness..."
"${PYTHON_BIN}" scripts/verify_source_of_truth_cutover_preflight.py
PREFLIGHT_STATUS=$?
"${PYTHON_BIN}" scripts/verify_remote_production_readiness.py
PRODUCTION_STATUS=$?
"${PYTHON_BIN}" scripts/prepare_remaining_production_gate_packet.py
PACKET_STATUS=$?

echo
echo "Shakedown signoff exit: ${SHAKEDOWN_STATUS}"
echo "Cutover preflight exit: ${PREFLIGHT_STATUS}"
echo "Production readiness exit: ${PRODUCTION_STATUS}"
echo "Remaining gate packet exit: ${PACKET_STATUS}"
echo "Review reports/owner_shakedown_signoff.md and reports/source_of_truth_cutover_preflight.md."
read -k 1 "?Press any key to close..."

if [[ "${SHAKEDOWN_STATUS}" -ne 0 || "${PREFLIGHT_STATUS}" -ne 0 || "${PRODUCTION_STATUS}" -ne 0 || "${PACKET_STATUS}" -ne 0 ]]; then
  exit 1
fi
