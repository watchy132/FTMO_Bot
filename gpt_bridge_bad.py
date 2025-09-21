# gpt_bridge.py — décideur local sans appel HTTP interne
# Compatible avec decide(payload, timeout=..., **kwargs)

from __future__ import annotations
import os, time
from typing import Any, Dict, Optional, List

BRIDGE_TIMEOUT = int(os.environ.get("BRIDGE_TIMEOUT", "60"))
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

def _now_ms() -> int:
    return int(time.time() * 1000)

def _ok(d: Dict[str, Any]) -> Dict[str, Any]:
    out = {"ok": True, **d}
    out.setdefault("ts", _now_ms())
    return out

def decide(payload: Dict[str, Any], timeout: Optional[int] = None, **kwargs) -> Dict[str, Any]:
    """
    Appelée par bridge_server:/decide et/ou directement par runner.py.
    Retourne une réponse avec un champ 'decisions' contenant des setups normalisables.
    """

    # --- Probe rapide ---
    if isinstance(payload, dict) and payload.get("probe") is True:
        return _ok({"decisions": [{"action": "skip", "reason": "probe"}]})

    symbols: List[str] = []
    if isinstance(payload, dict):
        syms = payload.get("symbols")
        if isinstance(syms, list):
            symbols = syms
        elif isinstance(syms, str):
            symbols = [syms]

    dbg = None
    if isinstance(payload, dict):
        dbg = payload.get("debug_force") or os.getenv("DEBUG_FORCE")

    # --- Mode debug_force (tests / harness) ---
    if dbg in ("buy", "sell", "skip"):
        action = dbg
        if action == "skip":
            return _ok({
                "decisions": [
                    {"action": "skip", "reason": "debug_force skip"}
                ]
            })
        else:
            # setup factice minimal mais complet
            setups = [{
                "symbol": symbols[0] if symbols else "EURUSD",
                "ticker": symbols[0] if symbols else "EURUSD",
                "timeframe": "M5",
                "source": "debug_force",
                "direction": action.upper(),
                "side": action,
                "action": action,
                "order_type": "market",
                "type": "market",
                "entry": 1.100,
                "entry_price": 1.100,
                "price": 1.100,
                "sl": 1.098,
                "stop_loss": 1.098,
                "stop": 1.098,
                "tp": 1.104,
                "take_profit": 1.104,
                "target": 1.104,
                "rr": 2.0,
                "rrr": 2.0,
                "risk_r": 1.0,
                "risk_percent": 0.5,
                "lots": 0.01,
                "valid": True,
                "normalized": True,
                "override_filters": True,
                "session": "ANY",
                "session_ok": True,
                "valid_until": _now_ms() + 60000,
                "mock": True
            }]
            return _ok({
                "decisions": [
                    {"action": action, "reason": f"debug_force {action}", "setups": setups}
                ]
            })

    # --- Placeholder si pas de debug_force ---
    return _ok({
        "decisions": [
            {"action": "skip", "reason": "logique GPT non implémentée ici"}
        ]
    })
