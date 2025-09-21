#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8765}"
ADMIN="${ADMIN_TOKEN:-}"

j() { curl -sS -X "$1" "http://$HOST:$PORT$2" "${@:3}" | python3 -m json.tool; }
code() { curl -s -o /dev/null -w "%{http_code}\n" -X "$1" "http://$HOST:$PORT$2" "${@:3}"; }

echo "== health =="
j GET /health >/dev/null && echo "OK"

echo "== decide (message.content) =="
DATA1='{"choices":[{"message":{"content":"```json\n[{\"symbol\":\"EURUSD\",\"direction\":\"BUY\",\"entry\":1.172,\"sl\":1.17,\"tp\":1.175}]\n```"}}]}'
[[ "$(code POST /decide -H 'Content-Type: application/json' --data "$DATA1")" == "200" ]] && echo "OK"

echo "== decide (tool_calls.arguments) =="
DATA2='{"choices":[{"message":{"tool_calls":[{"function":{"arguments":"{\"setups\":[{\"symbol\":\"EURUSD\",\"direction\":\"BUY\",\"entry\":1.172,\"sl\":1.17,\"tp\":1.175}]}"}}]}}]}'
[[ "$(code POST /decide -H 'Content-Type: application/json' --data "$DATA2")" == "200" ]] && echo "OK"

if [[ -n "$ADMIN" ]]; then
  echo "== reload_engine auth =="
  [[ "$(code POST /reload_engine -H "X-Admin-Token: wrong")" == "401" ]] && echo "401 OK (wrong token)"
  [[ "$(code POST /reload_engine -H "X-Admin-Token: $ADMIN")" == "200" ]] && echo "200 OK (good token)"
  GC="$(code GET /reload_engine)"; [[ "$GC" == "405" || "$GC" == "429" ]] && echo "GET blocked ($GC)"
else
  echo "NOTE: ADMIN_TOKEN non défini — tests /reload_engine sautés."
fi

echo "== done =="
