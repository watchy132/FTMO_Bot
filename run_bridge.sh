#!/usr/bin/env bash
set -euo pipefail
cd ~/FTMO_Bot
export ADMIN_TOKEN="nouveau-token-ultra-secure"
export OPENAI_API_KEY="${OPENAI_API_KEY:-$(grep -E '^OPENAI_API_KEY=' .env | cut -d= -f2-)}"
mkdir -p /tmp/ftmo_bot
pkill -f uvicorn 2>/dev/null || true
nohup env ADMIN_TOKEN="$ADMIN_TOKEN" OPENAI_API_KEY="$OPENAI_API_KEY" \
  python3 -m uvicorn bridge_server:app --host 127.0.0.1 --port 8765 --log-level info \
  >>/tmp/ftmo_bot/bridge.log 2>&1 &
echo "Bridge démarré."
