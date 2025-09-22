#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, gpt_bridge

payload = {
    "setups": [
        {
            "symbol": "EURUSD",
            "direction": "buy",
            "entry": 1.09,
            "sl": 1.088,
            "tp": 1.094,
        }
    ]
}

clean, report = gpt_bridge.decide(payload)
print(json.dumps({"ok": True, "n": len(clean), "report": report}, ensure_ascii=False))
