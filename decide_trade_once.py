from typing import List, Dict, Any
import os
MIN_RRR      = float(os.getenv("MIN_RRR",      "1.30"))   # ratio reward/risk minimal
RISK_PCT     = float(os.getenv("RISK_PCT",     "0.005"))  # 0.5% du capital par trade
ACCOUNT_EQUITY = float(os.getenv("ACCOUNT_BALANCE", "10000"))

def _rrr(s: Dict[str, Any]) -> float:
    d = str(s["direction"]).upper()
    e, sl, tp = float(s["entry"]), float(s["sl"]), float(s["tp"])
    risk   = (e - sl) if d == "BUY"  else (sl - e)
    reward = (tp - e) if d == "BUY"  else (e - tp)
    return reward / risk if risk > 0 else 0.0

def _size(entry: float, sl: float) -> float:
    stop_pts = abs(entry - sl)
    if stop_pts <= 0: return 0.0
    risk_amount = ACCOUNT_EQUITY * RISK_PCT
    # Taille “unités” en DEV: on suppose 1 unité bouge de 1 par point de prix
    # (suffisant pour la démo; adapter plus tard par symbole si besoin)
    return risk_amount / stop_pts

def decide(setups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not setups:
        return [{"action": "skip", "reason": "no_setups", "setups": []}]

    s = setups[0]
    rrr = float(s.get("rrr", _rrr(s)))
    if rrr < MIN_RRR:
        return [{"action": "skip", "reason": f"quality_fail:rrr<{MIN_RRR}", "setups": []}]

    entry, sl, tp = float(s["entry"]), float(s["sl"]), float(s["tp"])
    sz = _size(entry, sl)
    if sz <= 0:
        return [{"action": "skip", "reason": "sizing_error", "setups": []}]

    stop_pts   = abs(entry - sl)
    reward_pts = abs(tp - entry)
    risk_amt   = ACCOUNT_EQUITY * RISK_PCT

    return [{
        "action": "open",
        "reason": "engine_ok",
        "symbol": s["symbol"],
        "direction": str(s["direction"]).upper(),
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "size": round(sz, 5),
        "meta": {
            "rrr": rrr,
            "risk_pct": RISK_PCT,
            "risk_amount": round(risk_amt, 2),
            "stop_pts": stop_pts,
            "reward_pts": reward_pts,
        },
    }]
