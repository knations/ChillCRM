#!/bin/zsh
set -u

cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "CHILLCRM remote monitoring signoff"
echo
echo "This will record who owns monitoring during owner shakedown and week one."
echo
echo "It will not create monitors, change Vercel or Supabase settings, unlock writes,"
echo "switch source of truth, expose secrets, or change CRM records."
echo
echo "Default cadence:"
echo "- Health/protection: after each deployment, during shakedown, and first day/week one"
echo "- Provider logs/errors: during shakedown, first day, and daily during week one"
echo "- Backup status: daily during week one before local read-only retirement"
echo "- Audit/file/export checks: during shakedown, first day, and after any permission change"
echo "- Owner feedback: during owner shakedown and daily during week one"
echo

printf "Monitoring/signoff owner [Kevin Nations]: "
read SIGNOFF_OWNER
if [[ -z "${SIGNOFF_OWNER}" ]]; then
  SIGNOFF_OWNER="Kevin Nations"
fi

echo
echo "Type APPROVE MONITORING to approve the monitoring owner, cadence, and owner feedback loop."
printf "Confirmation: "
read CONFIRMATION

if [[ "${CONFIRMATION}" != "APPROVE MONITORING" ]]; then
  echo "Confirmation did not match. No monitoring signoff will be recorded."
  read -k 1 "?Press any key to close..."
  exit 1
fi

export PYTHONPYCACHEPREFIX="/private/tmp/chillcrm_pycache"

echo
echo "Recording monitoring signoff..."
"${PYTHON_BIN}" scripts/record_remote_monitoring_signoff.py \
  --signoff-owner "${SIGNOFF_OWNER}" \
  --approve-owner \
  --approve-cadence \
  --approve-feedback
SIGNOFF_STATUS=$?

echo
echo "Refreshing monitoring and production readiness..."
"${PYTHON_BIN}" scripts/verify_remote_monitoring_readiness.py
MONITORING_STATUS=$?
"${PYTHON_BIN}" scripts/verify_remote_production_readiness.py
PRODUCTION_STATUS=$?
"${PYTHON_BIN}" scripts/prepare_owner_gate_intake_packet.py
INTAKE_STATUS=$?
"${PYTHON_BIN}" scripts/prepare_remaining_production_gate_packet.py
PACKET_STATUS=$?

echo
echo "Monitoring signoff exit: ${SIGNOFF_STATUS}"
echo "Monitoring readiness exit: ${MONITORING_STATUS}"
echo "Production readiness exit: ${PRODUCTION_STATUS}"
echo "Owner packet exit: ${INTAKE_STATUS}"
echo "Remaining gate packet exit: ${PACKET_STATUS}"
echo "Review reports/remote_monitoring_signoff.md and reports/remote_monitoring_readiness.md."
read -k 1 "?Press any key to close..."

if [[ "${SIGNOFF_STATUS}" -ne 0 || "${MONITORING_STATUS}" -ne 0 || "${PRODUCTION_STATUS}" -ne 0 || "${INTAKE_STATUS}" -ne 0 || "${PACKET_STATUS}" -ne 0 ]]; then
  exit 1
fi
