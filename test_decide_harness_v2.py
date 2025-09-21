#!/usr/bin/env python3
import json
import requests

BRIDGE_URL = "http://127.0.0.1:8765/decide"

def extract_setups(resp):
    if not isinstance(resp, dict):
        return []
    v = resp.get("setups") or resp.get("decisions")
    if isinstance(v, list):
        return [x for x in v if isinstance(x, dict)]
    if isinstance(v, dict) and len(v) > 0:
        return [v]
    return []

def run_case(i, payload):
    r = requests.post(BRIDGE_URL, json=payload)
    try:
        resp = r.json()
    except Exception:
        print(f"Case {i} invalid JSON: {r.text}")
        return

    setups = extract_setups(resp)
    status = "OK" if setups else "FAIL"
    why = "valid setups" if setups else "no valid setups after normalization"

    print(json.dumps({
        "case": i,
        "status": status,
        "why": why,
        "action": resp.get("action"),
        "setups": setups
    }))

if __name__ == "__main__":
    cases = [
        {"symbols": ["EURUSD"], "debug_force": "buy"},
        {"symbols": ["EURUSD"], "debug_force": "sell"},
        {"symbols": ["EURUSD"], "debug_force": "skip"},
    ]
    for i, payload in enumerate(cases, 1):
        run_case(i, payload)
