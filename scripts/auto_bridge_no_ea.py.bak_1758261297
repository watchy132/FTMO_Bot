#!/usr/bin/env python3
from pathlib import Path
import re, time, json, subprocess as sp, hashlib, sys

ROOT   = Path(__file__).resolve().parents[1]
LOGDIR = ROOT / "logs"
PROFILE = LOGDIR / "ftmo_profile.json"

# Lignes "PLACE ..." du runner
P = re.compile(r"PLACE\s+(BUY|SELL)\s+([A-Z][_A-Z0-9.]+).*?sl[:=]?\s*([0-9.]+).*?tp[:=]?\s*([0-9.]+)(?:.*?entry[:=]?\s*([0-9.]+))?",
               re.I)
P_RISK = re.compile(r"risk[:=]?\s*([0-9.]+)%?", re.I)

def sh(cmd):
    print("->", cmd, flush=True)
    sp.run(cmd, shell=True)

def run_pywin(py_script, args=""):
    cmd = f"scripts/pywin {py_script} {args}".strip()
    print("->", cmd, flush=True)
    sp.run(cmd, shell=True)

def ensure_profile():
    # dump snapshot au démarrage
    run_pywin("scripts/ftmo_probe.py", f"--out {PROFILE}")

def load_profile():
    try:
        return json.loads(PROFILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def latest_log():
    files = sorted(LOGDIR.glob("run_*.log"))
    return files[-1] if files else None

def main():
    LOGDIR.mkdir(exist_ok=True)
    ensure_profile()
    prof = load_profile()
    default_risk = (prof.get("bot_profile") or {}).get("risk_per_trade_pct", 0.25)

    last = None
    f = None
    seen = set()

    while True:
        cur = latest_log()
        if not cur:
            time.sleep(1); continue
        if cur != last:
            if f: f.close()
            f = open(cur, "r", encoding="utf-8", errors="ignore")
            f.seek(0, 2)
            last = cur
            print(f"[bridge] tailing {cur}", flush=True)

        line = f.readline()
        if not line:
            time.sleep(0.2); continue

        if "PLACE" in line:
            print(f"[bridge] seen: {line.strip()}", flush=True)

        h = hashlib.sha1(line.encode("utf-8","ignore")).hexdigest()
        if h in seen: continue
        seen.add(h)

        m = P.search(line)
        if not m: continue
        side, sym, sl, tp, entry = m.groups()
        side = side.lower()

        # risque explicite dans la ligne, sinon profil
        rm = P_RISK.search(line)
        risk = float(rm.group(1)) if rm else float(default_risk)

        args = f"--symbol {sym} --side {side} --sl {sl} --tp {tp} --risk-pct {risk}"
        if entry:
            args += f" --pending limit --entry {entry}"
        run_pywin("scripts/trade_mt5_auto.py", args)

        # rafraîchir le profil toutes les 5 minutes
        if int(time.time()) % 300 == 0:
            ensure_profile()
            prof = load_profile()
            default_risk = (prof.get("bot_profile") or {}).get("risk_per_trade_pct", 0.25)

if __name__ == "__main__":
    main()
