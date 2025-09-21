mklogs(){ mkdir -p "$HOME/FTMO_Bot/logs"; }
br(){ mklogs; tail -n 200 "$HOME/FTMO_Bot/logs/bridge.log"; }
botlog(){ mklogs; tail -n 200 "$HOME/FTMO_Bot/logs/bot.log"; }
killport(){ lsof -i :"${1:-8765}" -t 2>/dev/null | xargs -r kill -9; }
hc(){ curl -sS http://127.0.0.1:8765/health | python3 -m json.tool; }
probe(){ curl -sS -X POST http://127.0.0.1:8765/decide -H 'Content-Type: application/json' -d '{"probe":true}' | python3 -m json.tool; }
hc_wait(){ until curl -sS http://127.0.0.1:8765/health >/dev/null 2>&1; do sleep 0.5; done; echo "bridge:healthy"; }

startbridge(){
  mklogs
  [ -f "$HOME/FTMO_Bot/.venv/bin/activate" ] && . "$HOME/FTMO_Bot/.venv/bin/activate"
  if [ -f "$HOME/FTMO_Bot/.env" ]; then set -a; . "$HOME/FTMO_Bot/.env"; set +a; fi
  nohup python "$HOME/FTMO_Bot/bridge_server.py" >> "$HOME/FTMO_Bot/logs/bridge.log" 2>&1 &
  echo $! > /tmp/bridge.pid
  hc_wait
}
stopbridge(){ pid="$(cat /tmp/bridge.pid 2>/dev/null)"; [ -n "$pid" ] && kill "$pid" 2>/dev/null || true; rm -f /tmp/bridge.pid; }

# Bot en avant-plan, avec .env exporté pour pywin
runbot(){
  cd "$HOME/FTMO_Bot" || return 1
  if [ -f "$HOME/FTMO_Bot/.env" ]; then set -a; . "$HOME/FTMO_Bot/.env"; set +a; fi
  /Users/ayoubzahour/pywin -u runner.py --symbol "${1:-EURUSD}" --minutes "${2:-5}" --max-trades "${3:-1}" --lots "${4:-0.01}"
}

# Bot en arrière-plan via tmux (évite WinError 6)
botbg(){
  cd "$HOME/FTMO_Bot" || return 1
  if [ -f "$HOME/FTMO_Bot/.env" ]; then set -a; . "$HOME/FTMO_Bot/.env"; set +a; fi
  tmux new -s ftmobg -d "cd $HOME/FTMO_Bot && /Users/ayoubzahour/pywin -u runner.py --symbol ${1:-EURUSD} --minutes ${2:-5} --max-trades ${3:-1} --lots ${4:-0.01}"
  echo "tmux session: ftmobg"
}
stopbot(){ tmux kill-session -t ftmobg 2>/dev/null || true; rm -f /tmp/bot.pid; }
