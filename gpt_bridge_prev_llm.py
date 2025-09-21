# gpt_bridge.py — bridge avec normalisation corrigée
import os, time
from typing import Any, Dict, Tuple

BRIDGE_TIMEOUT = int(os.environ.get("BRIDGE_TIMEOUT", "60"))
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

def _now_ms() -> int:
    return int(time.time() * 1000)

def _ok(d: Dict[str, Any]) -> Dict[str, Any]:
    out = {"ok": True, **d}
    out.setdefault("ts", _now_ms())
    return out

# --- Normalisation d'un setup unitaire ---
def _to_float(x):
    if x is None: return None
    if isinstance(x, (int, float)): return float(x)
    if isinstance(x, str):
        try:
            return float(x.strip())
        except:
            return None
    return None

def normalize_setup(s: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    if not isinstance(s, dict):
        return {}, "REJECT: not a dict"

    symbol = s.get("symbol") or s.get("ticker")
    direction = (s.get("direction") or s.get("side") or s.get("action") or "").upper()
    entry = _to_float(s.get("entry") or s.get("entry_price") or s.get("price"))
    sl    = _to_float(s.get("sl") or s.get("stop_loss") or s.get("stop") or s.get("sl_price"))
    tp    = _to_float(s.get("tp") or s.get("take_profit") or s.get("target") or s.get("tp_price"))

    if not symbol:
        return {}, "REJECT: missing symbol"
    if direction not in ("BUY", "SELL"):
        return {}, f"REJECT: bad direction {direction}"
    if entry is None or sl is None or tp is None:
        return {}, "REJECT: missing price levels"

    rrr = None
    if sl and tp and entry:
        try:
            if direction == "BUY":
                rrr = (tp - entry) / (entry - sl) if (entry - sl) > 0 else None
            else:
                rrr = (entry - tp) / (sl - entry) if (sl - entry) > 0 else None
        except ZeroDivisionError:
            rrr = None

    setup = {
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "rrr": rrr,
        "lots": _to_float(s.get("lots") or 0.01),
        "source": s.get("source", "bridge"),
    }
    return setup, ""

def decide(payload: Dict[str, Any], timeout: float|None=None, **kwargs) -> Dict[str, Any]:
    if isinstance(payload, dict) and payload.get("probe") is True:
        return _ok({"status": "OK", "why": "probe-bridge-only"})

    dbg = payload.get("debug_force")
    if dbg in ("buy", "sell"):
        setup, err = normalize_setup({
            "symbol": (payload.get("symbols") or ["?"])[0],
            "direction": dbg,
            "entry": 1.100,
            "sl": 1.098,
            "tp": 1.104,
            "source": "debug_force"
        })
        if err:
            return _ok({"status": "SKIP", "why": err, "decisions": []})
        return _ok({"status": "TAKE", "why": f"debug_force {dbg}", "decisions":[setup]})

    return _ok({"status": "SKIP", "why": "logic non implémentée", "decisions": []})
