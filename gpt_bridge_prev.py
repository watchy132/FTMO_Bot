from __future__ import annotations
import time
from typing import Any, Dict, Optional

def _now_ms() -> int:
    return int(time.time() * 1000)

def _ok(d: Dict[str, Any]) -> Dict[str, Any]:
    d.setdefault("ok", True)
    d.setdefault("ts", _now_ms())
    return d

def _decision(symbol: str, side: str) -> Dict[str, Any]:
    """
    Crée une décision de trade avec tous les champs attendus par normalize_setup.
    """
    side = side.lower()
    if side == "buy":
        entry, sl, tp = 1.100, 1.098, 1.104
    else:
        entry, sl, tp = 1.100, 1.102, 1.096
    return {
        "symbol": symbol,
        "ticker": symbol,
        "direction": side.upper(),
        "side": side.upper(),
        "action": side,
        "order_type": "market",
        "type": "market",
        "entry": entry,
        "entry_price": entry,
        "price": entry,
        "sl": sl,
        "stop_loss": sl,
        "tp": tp,
        "take_profit": tp,
        "rrr": 2.0,
        "risk_r": 1.0,
        "reason": f"debug_force {side}"
    }

def decide(payload: Dict[str, Any], timeout: Optional[int] = None, **kwargs) -> Dict[str, Any]:
    """
    Fonction appelée par bridge_server:/decide.
    Retourne des setups normalisés prêts pour runner/test_harness.
    """
    # Cas test
    if isinstance(payload, dict) and payload.get("probe") is True:
        return _ok({"decisions": [{"action": "skip", "reason": "probe-bridge-only"}]})

    symbols = payload.get("symbols") if isinstance(payload, dict) else []
    if not symbols:
        symbols = ["EURUSD"]

    dbg = (payload.get("debug_force") or "").strip().lower() if isinstance(payload, dict) else ""
    if dbg in ("buy", "sell"):
        return _ok({"decisions": [_decision(symbols[0], dbg)]})

    # Si pas de debug_force → skip par défaut
    return _ok({"decisions": [{"action": "skip", "reason": "no strategy active"}]})
