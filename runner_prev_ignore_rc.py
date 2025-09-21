#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import os, sys, json, time, argparse
from typing import Any, Dict, List
from gpt_bridge import decide

TIMEOUT = float(os.getenv("BRIDGE_TIMEOUT", "60"))
PYWIN   = os.getenv("PYWIN_BIN", "/Users/ayoubzahour/pywin")
ROOT    = os.path.dirname(os.path.abspath(__file__))
TRADER_SCRIPT = os.path.join(ROOT, "FTMO_GPT_Trader_S2_FIXED_r3.py")

def _print(x: Any) -> None:
    print(json.dumps(x, ensure_ascii=False, indent=2))

def _first(resp: Dict[str,Any]) -> Dict[str,Any]:
    ds = resp.get("decisions") or []
    return ds[0] if isinstance(ds, list) and ds else {}

def _run_trader(symbol: str, side: str, lots: float, sl: float|None, tp: float|None, dry: bool=False) -> int:
    argv = [PYWIN, "-u", TRADER_SCRIPT,
            "--symbol", symbol, "--side", side,
            "--lots", f"{lots}", "--sl", f"{sl or 0}", "--tp", f"{tp or 0}"]
    print("[EXEC]", " ".join(argv))
    if dry: return 0
    rc = os.spawnv(os.P_WAIT, PYWIN, argv)
    return int(rc)

def parse_args(a: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Runner FTMO bridge->MT5")
    p.add_argument("--symbol", required=True)
    p.add_argument("--minutes", type=int, default=5)
    p.add_argument("--max-trades", type=int, default=1)
    p.add_argument("--lots", type=float, default=0.01)
    p.add_argument("--sl", type=float, default=0.0)
    p.add_argument("--tp", type=float, default=0.0)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--debug-force", choices=["buy","sell","skip"], default=None)
    return p.parse_args(a)

def main(argv: List[str]|None=None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    payload: Dict[str,Any] = {
        "symbols":[args.symbol],
        "window_minutes": int(args.minutes),
        "max_trades": int(args.max_trades),
    }
    dbg = args.debug_force or os.getenv("DEBUG_FORCE")
    if dbg in ("buy","sell","skip"):
        payload["debug_force"] = dbg

    print("[Bridge] payload:"); _print(payload)
    t0 = time.time()
    resp = decide(payload, timeout=TIMEOUT)
    dt = int((time.time()-t0)*1000)
    print(f"[Bridge] response ({dt} ms):"); _print(resp)

    d = _first(resp)
    action = (d.get("action") or "skip").lower()
    reason = d.get("reason")

    # 🔹 Corrigé : chercher sl/tp dans setups
    sl = None
    tp = None
    setups = d.get("setups") or []
    if setups and isinstance(setups, list) and isinstance(setups[0], dict):
        sl = setups[0].get("sl")
        tp = setups[0].get("tp")
    else:
        sl = d.get("sl")
        tp = d.get("tp")

    if action not in ("buy","sell"):
        print(f"[Runner] action={action.upper()} -> aucun ordre. reason={reason}")
        return 0

    print(f"[Runner] PLACE {action.upper()} {args.symbol} lots={args.lots} sl={sl or args.sl} tp={tp or args.tp}")
    rc = _run_trader(args.symbol, action, float(args.lots),
                     float(sl or args.sl or 0.0), float(tp or args.tp or 0.0),
                     bool(args.dry_run))
    print(f"[Runner] trader exit={rc}")
    return rc

if __name__ == "__main__":
    sys.exit(main())
