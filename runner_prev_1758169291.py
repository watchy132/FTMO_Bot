#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import os, sys, json, time, argparse
from typing import Any, Dict, List
from gpt_bridge import decide

TIMEOUT = float(os.getenv("BRIDGE_TIMEOUT", "60"))
PYWIN   = os.getenv("PYWIN_BIN", "/Users/ayoubzahour/pywin")
ROOT    = os.path.dirname(os.path.abspath(__file__))
TRADER_SCRIPT = os.path.join(ROOT, "scripts", "FTMO_GPT_Trader_MAIN.py")

def _print(x: Any) -> None:
    print(json.dumps(x, ensure_ascii=False, indent=2))

def _first(resp: Dict[str,Any]) -> Dict[str,Any]:
    ds = resp.get("decisions") or []
    return ds[0] if isinstance(ds, list) and ds else {}

def _run_trader(symbol: str, side: str, lots: float, sl: float|None, tp: float|None, dry: bool=False) -> int:
    # entry calculée depuis setups pour le symbole courant
    try:
        _entry_for_symbol = next((st.get('entry') for st in (setups or [])
            if isinstance(st, dict) and (st.get('symbol') in (None, symbol)) and st.get('entry') is not None), None)
    except Exception:
        _entry_for_symbol = None
    argv = [PYWIN, "-u", TRADER_SCRIPT,
            "--symbol", symbol, "--side", side,
            "--lots", f"{lots}", "--sl", f"{sl or 0}", "--tp", f"{tp or 0}"]
    # ajouter --entry si disponible
    if _entry_for_symbol is not None and '--entry' not in argv:
        argv += ['--entry', str(_entry_for_symbol)]

    # --- ENTRY PATCH (auto) ---
    try:
        _lv = locals()
        _args = argv
        _sym = None
        for _i,_v in enumerate(_args):
            if _v == "--symbol" and _i+1 < len(_args):
                _sym = _args[_i+1]; break
        _setups = _lv.get("setups") or []
        _e = None
        for _s in _setups:
            if not isinstance(_s, dict): continue
            if _sym and _s.get("symbol") and _s.get("symbol") != _sym: continue
            if _s.get("entry") is not None:
                _e = _s["entry"]; break
        if _e is not None and "--entry" not in _args:
            argv += ["--entry", str(_e)]
    except Exception:
        pass
    # --- END ENTRY PATCH ---
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

    # ENTRY_PATCH_AFTER_PLACE
    try:
        _lv = locals()
        _entry = None
        # cas 1: setup courant 's'
        if 's' in _lv and isinstance(_lv['s'], dict):
            _entry = _lv['s'].get('entry')
        # cas 2: chercher dans 'setups' si non trouvé
        if _entry is None:
            for _st in (_lv.get('setups') or []):
                if isinstance(_st, dict) and _st.get('entry') is not None:
                    _entry = _st['entry']; break
        # ajouter --entry à la première liste d'args trouvée
        if _entry is not None:
            for _name in ('argv','cmd','args'):
                _lst = _lv.get(_name)
                if isinstance(_lst, list) and '--entry' not in _lst:
                    _lst += ['--entry', str(_entry)]
                    break
    except Exception:
        pass
    # END_ENTRY_PATCH_AFTER_PLACE
    rc = _run_trader(args.symbol, action, float(args.lots),
                     float(sl or args.sl or 0.0), float(tp or args.tp or 0.0),
                     bool(args.dry_run))
    print(f"[Runner] trader exit={rc}")
    return rc

if __name__ == "__main__":
    sys.exit(main())
