#!/bin/bash
set -euo pipefail
PROJECT_DIR="$HOME/FTMO_Bot"
PYWIN="/Users/ayoubzahour/pywin"
WINE_BIN="${WINE_BIN:-/Applications/Wine Stable.app/Contents/Resources/wine/bin/wine}"
WINEPREFIX="$HOME/.wine-mt5"
MT5_EXE="$WINEPREFIX/drive_c/Program Files/MetaTrader 5/terminal64.exe"
BRIDGE_HOST="127.0.0.1"
BRIDGE_PORT="8765"
HEALTH_URL="http://$BRIDGE_HOST:$BRIDGE_PORT/health"
LOG_DIR="/tmp/ftmo_bot"
BRIDGE_LOG="$LOG_DIR/bridge.log"
RUNNER_LOG="$LOG_DIR/runner.log"
MT5_LOG="$LOG_DIR/mt5.log"
SYMBOL="${SYMBOL:-EURUSD}"
MINUTES="${MINUTES:-5}"
MAX_TRADES="${MAX_TRADES:-1}"
LOTS="${LOTS:-0.01}"
DRY="${DRY:-false}"

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR"

info(){ printf '[INFO] %s\n' "$*"; }
err(){ printf '[ERR ] %s\n' "$*" >&2; }
require_cmd(){ command -v "$1" >/dev/null 2>&1 || { err "commande introuvable: $1"; exit 1; }; }

require_cmd curl
require_cmd lsof
[ -x "$PYWIN" ] || { err "PYWIN non exécutable: $PYWIN"; exit 1; }
[ -x "$WINE_BIN" ] || { err "WINE_BIN non exécutable: $WINE_BIN"; exit 1; }
[ -f "$MT5_EXE" ] || { err "MT5 introuvable: $MT5_EXE"; exit 1; }

if lsof -iTCP:"$BRIDGE_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  info "Port $BRIDGE_PORT occupé → kill"
  lsof -ti tcp:"$BRIDGE_PORT" | xargs -I{} kill -9 {} || true
  sleep 1
fi

info "Démarrage MT5"
WINEPREFIX="$WINEPREFIX" "$WINE_BIN" "$MT5_EXE" >>"$MT5_LOG" 2>&1 &
MT5_PID=$!
info "MT5 PID=$MT5_PID"
sleep 3

info "Démarrage bridge_server.py"
nohup python3 -u bridge_server.py >>"$BRIDGE_LOG" 2>&1 &
BRIDGE_PID=$!
info "BRIDGE PID=$BRIDGE_PID"

info "Attente santé bridge ($HEALTH_URL)"
for i in {1..30}; do
  if curl -sSf "$HEALTH_URL" >/dev/null 2>&1; then
    info "Bridge OK"
    break
  fi
  sleep 1
  [ "$i" -eq 30 ] && { err "Bridge KO"; exit 1; }
done

RUNNER_ARGS=(--symbol "$SYMBOL" --minutes "$MINUTES" --max-trades "$MAX_TRADES" --lots "$LOTS")
[ "$DRY" = "true" ] && RUNNER_ARGS+=(--dry-run)

info "Lancement runner.py ${RUNNER_ARGS[*]}"
nohup "$PYWIN" -u runner.py "${RUNNER_ARGS[@]}" >>"$RUNNER_LOG" 2>&1 &
RUNNER_PID=$!
info "RUNNER PID=$RUNNER_PID"

info "Logs:"
echo "  MT5    → $MT5_LOG"
echo "  Bridge → $BRIDGE_LOG"
echo "  Runner → $RUNNER_LOG"
