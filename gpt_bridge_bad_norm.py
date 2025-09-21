from __future__ import annotations
import os, time, json, re
from typing import Any, Dict, Optional
import requests

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # change si besoin

def _now_ms() -> int: return int(time.time()*1000)
def _ok(d: Dict[str, Any]) -> Dict[str, Any]: d.setdefault("ok", True); d.setdefault("ts", _now_ms()); return d

def _json_from_text(txt: str) -> Optional[Dict[str, Any]]:
    # cherche le premier bloc JSON
    m = re.search(r"\{.*\}", txt, re.S)
    if not m: return None
    try: return json.loads(m.group(0))
    except Exception: return None

def _llm_decide(symbol: str) -> Dict[str, Any]:
    """Appelle OpenAI et retourne un dict {'action','sl','tp','reason'}"""
    if not OPENAI_API_KEY:
        return {"action":"skip", "reason":"OPENAI_API_KEY manquante"}

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type":"application/json"}
    sys_msg = (
        "Tu es un assistant de trading intraday. "
        "Réponds UNIQUEMENT en JSON avec les clés: action ('buy' ou 'sell'), sl (float), tp (float), reason (string courte). "
        "Ex: {\"action\":\"buy\",\"sl\":1.0980,\"tp\":1.1040,\"reason\":\"breakout M5\"} "
        "Paires typiques: EURUSD ~1.x. SL < entry < TP pour buy, TP < entry < SL pour sell."
    )
    user_msg = f"Donne une décision sur {symbol} M5 maintenant. Propose des niveaux SL et TP plausibles."

    body = {
        "model": OPENAI_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role":"system","content":sys_msg},
            {"role":"user","content":user_msg}
        ]
    }
    try:
        r = requests.post(url, headers=headers, json=body, timeout=20)
        r.raise_for_status()
        txt = r.json()["choices"][0]["message"]["content"]
        data = _json_from_text(txt) or {}
    except Exception as e:
        return {"action":"skip", "reason": f"llm_error: {e}"}

    action = str(data.get("action","")).lower()
    sl = data.get("sl"); tp = data.get("tp"); reason = data.get("reason") or "llm"
    # garde-fous
    if action not in ("buy","sell") or not isinstance(sl,(int,float)) or not isinstance(tp,(int,float)):
        return {"action":"skip", "reason":"llm_output_invalid"}
    # bornes EURUSD simples
    if not (0.8 < float(sl) < 2.0 and 0.8 < float(tp) < 2.0):
        return {"action":"skip", "reason":"levels_out_of_range"}
    return {"action": action, "sl": float(sl), "tp": float(tp), "reason": str(reason)[:120]}

def decide(payload: Dict[str, Any], timeout: Optional[int]=None, **kwargs) -> Dict[str, Any]:
    # health
    if isinstance(payload, dict) and payload.get("probe") is True:
        return _ok({"decisions":[{"action":"ok","reason":"probe-bridge-only"}]})

    # debug-force
    dbg = (payload.get("debug_force") or "").strip().lower() if isinstance(payload, dict) else ""
    if dbg in ("buy","sell"):
        if dbg == "buy": sl, tp = 1.0980, 1.1040
        else:            sl, tp = 1.1020, 1.0960
        return _ok({"decisions":[{"action":dbg,"sl":sl,"tp":tp,"reason":f"debug_force {dbg}"}]})

    # appel LLM
    symbols = payload.get("symbols") or []
    symbol = symbols[0] if isinstance(symbols, list) and symbols else "EURUSD"
    d = _llm_decide(symbol)

    # contrat runner.py
    return _ok({"decisions":[d]})
