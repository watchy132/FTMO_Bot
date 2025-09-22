#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, time, json
from typing import Optional

try:
    import MetaTrader5 as mt5
except Exception as e:
    print(json.dumps({"ok": False, "stage": "import", "error": str(e)}))
    sys.exit(1)

SYMBOL = "EURUSD"
VOLUME = 0.01  # 1k nominal (très petit)
SL_PIPS = 20  # 20 pips
TP_PIPS = 40  # 40 pips
DRY_RUN = True  # Passe à False pour EXECUTER


def pips(symbol: str) -> float:
    # EURUSD: 1 pip = 0.0001 ; XAUUSD: 0.1 ; indices/CFD varient
    info = mt5.symbol_info(symbol)
    if not info:
        return 0.0001
    # 5 digits → 0.0001 ; 3 digits (XAU) → 0.1
    if info.digits == 5:
        return 0.0001
    if info.digits == 3:
        return 0.1
    if info.digits == 2:
        return 0.01
    if info.digits == 1:
        return 0.1
    return 0.0001


def ensure_symbol(sym: str) -> bool:
    si = mt5.symbol_info(sym)
    if not si:
        return False
    if not si.visible:
        if not mt5.symbol_select(sym, True):
            return False
    return True


def main():
    if not mt5.initialize():
        print(
            json.dumps(
                {"ok": False, "stage": "initialize", "last_error": mt5.last_error()}
            )
        )
        return
    try:
        if not ensure_symbol(SYMBOL):
            print(json.dumps({"ok": False, "stage": "symbol_select", "symbol": SYMBOL}))
            return

        tick = mt5.symbol_info_tick(SYMBOL)
        if not tick:
            print(json.dumps({"ok": False, "stage": "tick", "symbol": SYMBOL}))
            return

        pip = pips(SYMBOL)
        price = tick.ask
        sl = price - SL_PIPS * pip
        tp = price + TP_PIPS * pip

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
            "volume": VOLUME,
            "type": mt5.ORDER_TYPE_BUY,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "type_filling": mt5.ORDER_FILLING_FOK,
            "comment": "FTMO_Bot order_test",
        }

        if DRY_RUN:
            print(
                json.dumps(
                    {"ok": True, "stage": "preview", "request": request},
                    ensure_ascii=False,
                )
            )
            return

        result = mt5.order_send(request)
        out = {
            "ok": result is not None and result.retcode == mt5.TRADE_RETCODE_DONE,
            "stage": "send",
            "retcode": getattr(result, "retcode", None),
            "comment": getattr(result, "comment", None),
            "order": getattr(result, "order", None),
            "price": price,
            "sl": sl,
            "tp": tp,
        }
        print(json.dumps(out, ensure_ascii=False))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
