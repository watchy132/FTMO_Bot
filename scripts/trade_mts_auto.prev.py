
# -*- coding: utf-8 -*-
import argparse, sys, math, MetaTrader5 as mt5

def lots_from_risk(symbol, entry, sl, risk_amount):
    si = mt5.symbol_info(symbol)
    if si is None: raise RuntimeError(f"Symbol {symbol} not found")
    if not si.visible: mt5.symbol_select(symbol, True)
    tick_val = float(si.trade_tick_value); tick_sz = float(si.trade_tick_size)
    if tick_sz<=0 or tick_val<=0: raise RuntimeError("Invalid tick_size/tick_value")
    sl_dist = abs(entry - sl)
    if sl_dist<=0: raise RuntimeError("SL distance must be > 0")
    risk_per_lot = (sl_dist / tick_sz) * tick_val
    lots = risk_amount / risk_per_lot
    step = float(si.volume_step or 0.01); vmin = float(si.volume_min or 0.01); vmax = float(si.volume_max or 100.0)
    lots = math.floor(lots/step)*step
    lots = max(vmin, min(lots, vmax))
    return round(lots, 2 if step < 0.1 else 1)

def send_order(a):
    if not mt5.initialize(): raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")
    ai = mt5.account_info()
    if ai is None: raise RuntimeError(f"account_info() failed: {mt5.last_error()}")
    tick = mt5.symbol_info_tick(a.symbol)
    mkt_price = tick.ask if a.side=="buy" else tick.bid
    entry = a.entry if a.entry is not None else mkt_price
    risk_amount = float(ai.balance) * (a.risk_pct/100.0)
    lots = a.lots if a.lots else lots_from_risk(a.symbol, entry, a.sl, risk_amount)
    if a.pending:
        typ = mt5.ORDER_TYPE_BUY_LIMIT if a.side=="buy" else mt5.ORDER_TYPE_SELL_LIMIT
        price = float(entry)
        action = mt5.TRADE_ACTION_PENDING
    else:
        typ = mt5.ORDER_TYPE_BUY if a.side=="buy" else mt5.ORDER_TYPE_SELL
        price = mkt_price
        action = mt5.TRADE_ACTION_DEAL
    req = {"action": action, "symbol": a.symbol, "volume": float(lots), "type": typ,
           "price": price, "sl": float(a.sl), "tp": float(a.tp),
           "deviation": 10, "type_filling": mt5.ORDER_FILLING_FOK, "type_time": mt5.ORDER_TIME_GTC,
           "comment": "AUTO_FTMO"}
    res = mt5.order_send(req)
    if res is None: raise RuntimeError(f"order_send() failed: {mt5.last_error()}")
    print(f"OK lots={lots} retcode={res.retcode} comment={res.comment}")
    mt5.shutdown()

def parse():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--side", choices=["buy","sell"], required=True)
    p.add_argument("--sl", type=float, required=True)
    p.add_argument("--tp", type=float, required=True)
    p.add_argument("--pending", action="store_true")
    p.add_argument("--entry", type=float)
    p.add_argument("--risk-pct", dest="risk_pct", type=float, default=0.25)
    p.add_argument("--lots", type=float)
    return p.parse_args()

if __name__=="__main__":
    try: send_order(parse())
    except Exception as e: print(f"ERR {e}"); sys.exit(1)
