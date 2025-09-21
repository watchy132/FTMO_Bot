# schemas.py — normalisation large des setups GPT
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

def _to_float(x: Any) -> Optional[float]:
    try:
        if isinstance(x, str):
            x = x.replace(",", "").strip()
        return float(x)
    except Exception:
        return None

def _pick(d: Dict[str, Any], *keys) -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None

def _norm_symbol(d: Dict[str, Any]) -> Optional[str]:
    v = _pick(d, "symbol", "ticker", "pair")
    if not v or not isinstance(v, str):
        return None
    return v.strip().upper()

def _norm_side(d: Dict[str, Any]) -> Optional[str]:
    v = _pick(d, "direction", "side", "action", "order_side")
    if not v or not isinstance(v, str):
        return None
    v = v.strip().lower()
    if v in ("buy", "long", "bull", "up"):
        return "BUY"
    if v in ("sell", "short", "bear", "down"):
        return "SELL"
    return None

def _norm_type(d: Dict[str, Any]) -> str:
    v = _pick(d, "order_type", "type", "orderType")
    if isinstance(v, str) and v.lower() in ("market", "mkt"):
        return "market"
    if isinstance(v, str) and v.lower() in ("limit", "lmt"):
        return "limit"
    # défaut: market
    return "market"

def _norm_prices(d: Dict[str, Any]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    entry = _to_float(_pick(d, "entry", "entry_price", "price"))
    sl    = _to_float(_pick(d, "sl", "stop_loss", "stop", "sl_price"))
    tp    = _to_float(_pick(d, "tp", "take_profit", "tp_price"))
    return entry, sl, tp

def _basic_validate(side: str, entry: float, sl: float, tp: float) -> bool:
    if side == "BUY":
        return sl < entry < tp
    if side == "SELL":
        return tp < entry < sl
    return False

def normalize_setup(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None

    symbol = _norm_symbol(raw)
    side   = _norm_side(raw)
    otype  = _norm_type(raw)
    entry, sl, tp = _norm_prices(raw)

    if not symbol or not side:
        return None

    # Si entry absent en market, accepter et laisser runner calculer avec le prix courant si supporté
    if entry is None:
        # tolérance market: entry sera rempli ailleurs si runner le permet
        pass
    if sl is None or tp is None:
        # tenter fallback en pips si fournis
        sl_pips = _to_float(_pick(raw, "sl_pips", "stop_pips"))
        tp_pips = _to_float(_pick(raw, "tp_pips", "take_pips", "tp_points"))
        if entry is not None and sl is None and sl_pips is not None:
            sl = entry - sl_pips*1e-4 if side == "BUY" else entry + sl_pips*1e-4
        if entry is not None and tp is None and tp_pips is not None:
            tp = entry + tp_pips*1e-4 if side == "BUY" else entry - tp_pips*1e-4

    # Si tous prix présents, valider la cohérence
    if entry is not None and sl is not None and tp is not None:
        if not _basic_validate(side, entry, sl, tp):
            return None

    lots = _to_float(_pick(raw, "lots", "volume"))
    risk_r = _to_float(_pick(raw, "risk_r", "riskR", "r"))
    rr = _to_float(_pick(raw, "rr", "rrr"))

    setup = {
        "symbol": symbol,
        "side": side,            # BUY/SELL
        "type": otype,           # market/limit
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "lots": lots,
        "risk_r": risk_r,
        "rr": rr,
        "raw": raw,
    }
    return setup

def normalize_decide_response(d: Dict[str, Any]) -> Dict[str, Any]:
    """Uniformiser la réponse bridge->runner"""
    if not isinstance(d, dict):
        return {"action":"SKIP", "reason":"invalid bridge response", "setups":[]}

    action = d.get("action") or d.get("status") or "SKIP"
    action = str(action).upper()
    reason = d.get("reason") or d.get("why")

    setups_raw = d.get("setups") or []
    setups: List[Dict[str, Any]] = []
    if isinstance(setups_raw, list):
        for s in setups_raw:
            ns = normalize_setup(s)
            if ns:
                setups.append(ns)

    if action == "TAKE" and not setups:
        # Si TAKE mais aucune passe la normalisation, requalifier proprement
        return {"action":"SKIP", "reason":"no valid setups after normalization", "setups":[]}

    return {"action": action, "reason": reason, "setups": setups}
