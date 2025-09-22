from __future__ import annotations
import time
from typing import Any, Dict, Optional


def _now_ms() -> int:
    return int(time.time() * 1000)


def _ok(d: Dict[str, Any]) -> Dict[str, Any]:
    d.setdefault("ok", True)
    d.setdefault("ts", _now_ms())
    return d


def _decision(side: str) -> Dict[str, Any]:
    side = side.lower()
    if side == "buy":
        sl, tp = 1.0980, 1.1040
    else:
        sl, tp = 1.1020, 1.0960
    return {"action": side, "reason": f"debug_force {side}", "sl": sl, "tp": tp}


def decide(payload: Dict[str, Any], timeout: Optional[int] = None, **kwargs) -> Dict[str, Any]:
    if isinstance(payload, dict) and payload.get("probe") is True:
        return _ok({"decisions": [{"action": "ok", "reason": "probe-bridge-only"}]})

    dbg = (payload.get("debug_force") or "").strip().lower() if isinstance(payload, dict) else ""
    if dbg in ("buy", "sell"):
        return _ok({"decisions": [_decision(dbg)]})

    return _ok({"decisions": [{"action": "skip", "reason": "no strategy active"}]})
