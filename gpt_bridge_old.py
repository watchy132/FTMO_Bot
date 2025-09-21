# -*- coding: utf-8 -*-
# Bridge robuste : coercion & normalisation d'un "setup" venant du LLM

import json
from typing import Any, Dict, List, Tuple

def _to_float(x):
    if x is None: return None
    if isinstance(x, (int, float)): return float(x)
    if isinstance(x, str):
        try: return float(x.strip())
        except: return None
    return None

def normalize_setup(s: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    if not isinstance(s, dict):
        return {}, "REJECT: not a dict"
    symbol    = s.get("symbol") or s.get("ticker")
    direction = s.get("direction") or s.get("side")
    entry = _to_float(s.get("entry") or s.get("price") or s.get("entry_price"))
    sl    = _to_float(s.get("sl")    or s.get("stop_loss") or s.get("stop"))
    tp    = _to_float(s.get("tp")    or s.get("take_profit") or s.get("target"))
    rrr   = _to_float(s.get("rrr"))
    tf    = s.get("timeframe") or s.get("tf") or "H1"
    conf  = _to_float(s.get("confidence"))

    if direction not in ("BUY", "SELL"):
        return {}, "REJECT: direction"
    if not symbol:
        return {}, "REJECT: symbol"
    if any(v is None for v in (entry, sl, tp)):
        return {}, "REJECT: prices"

    return ({
        "symbol": symbol,
        "timeframe": tf,
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "rrr": rrr,
        "confidence": conf,
        "raw": s
    }, "OK")

def _coerce_decide_response(raw: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    # action
    a = (raw.get("action") or "hold")
    if isinstance(a, str):
        a = a.strip().lower()
        if a in ("none", "skip"): a = "hold"
    else:
        a = "hold"
    out["action"] = a

    # setups
    setup_obj = raw.get("setups", raw.get("setup", []))
    if isinstance(setup_obj, dict):
        setups_list = [setup_obj]
    elif isinstance(setup_obj, list):
        setups_list = [x for x in setup_obj if isinstance(x, dict)]
    else:
        setups_list = []

    norm = [normalize_setup(s) for s in setups_list]
    candidates = [s for s, st in norm if not str(st).startswith("REJECT")]
    out["setups"] = candidates

    # risk
    rv = raw.get("risk", 0.005)
    out["risk"] = rv if isinstance(rv, (int, float)) else 0.005

    out["expires_at"] = raw.get("expires_at")
    return out

# ====== A ADAPTER : remplace cette fonction par ton appel LLM réel ======
def mock_llm_decide(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Exemple : renvoyer 1 setup valide BUY EURUSD
    sym = payload.get("symbol", "EURUSD")
    tf  = payload.get("timeframe", "M5")
    price = float(payload.get("price", 1.1000))
    return {
        "action": "buy",
        "expires_at": None,
        "risk": 0.005,
        "setups": [{
            "symbol": sym, "timeframe": tf, "direction": "BUY",
            "entry": price, "sl": price - 0.0015, "tp": price + 0.003, "rrr": 2.0
        }]
    }
# =======================================================================

def decide(payload_json: str) -> str:
    try:
        payload = json.loads(payload_json)
    except Exception:
        return json.dumps({"action":"hold","setups":[],"risk":0.005,"expires_at":None})

    raw = mock_llm_decide(payload)               # <<< remplace par ton appel modèle réel
    clean = _coerce_decide_response(raw)
    return json.dumps(clean, ensure_ascii=False)

if __name__ == "__main__":
    sample = json.dumps({"symbol":"EURUSD","price":1.10,"timeframe":"M5"})
    print(decide(sample))
