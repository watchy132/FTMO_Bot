#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
JSON=logs/ftmo_profile.json
R="${1:-}"; [[ -z "${R}" ]] && { echo "Usage: scripts/set_risk.sh <pct>"; exit 1; }
R="${R%%%}"   # enlève un éventuel %
TMP=$(mktemp)
jq --argjson r "$R" '
  .bot_profile = (.bot_profile // {}) |
  .bot_profile.risk_per_trade_pct = $r
' "$JSON" > "$TMP" && mv "$TMP" "$JSON"
echo "Default risk set to ${R}%"
