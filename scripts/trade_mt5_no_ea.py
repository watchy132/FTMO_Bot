
import sys, argparse, time
import MetaTrader5 as mt5

def connect():
    if not mt5.initialize():
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")
    info = mt5.account_info()
    if not info: raise SystemExit(f"MT5 not authorized: {mt5.last_error()}")
    return info

def ensure_symbol(sym):
    if not mt5.symbol_select(sym, True):
        raise SystemExit(f"symbol_select fail {sym}: {mt5.last_error()}")

def lot_round(sym, lots):
    si = mt5.symbol_info(sym)
    step = getattr(si, "volume_step", 0.01) or 0.01
    return round(max(si.volume_min, min(si.volume_max, lots))/step)*step

def order_type(side, pending=None):
    from MetaTrader5 import ORDER_TYPE_BUY, ORDER_TYPE_SELL, \
        ORDER_TYPE_BUY_LIMIT, ORDER_TYPE_SELL_LIMIT, ORDER_TYPE_BUY_STOP, ORDER_TYPE_SELL_STOP
    if pending is None:
        return ORDER_TYPE_BUY if side=="buy" else ORDER_TYPE_SELL
    if pending=="limit":
        return ORDER_TYPE_BUY_LIMIT if side=="buy" else ORDER_TYPE_SELL_LIMIT
    if pending=="stop":
        return ORDER_TYPE_BUY_STOP if side=="buy" else ORDER_TYPE_SELL_STOP
    raise ValueError("pending must be limit/stop/None")

def place(symbol, side, lots, sl=None, tp=None, entry=None, pending=None, comment="NO_EA"):
    ensure_symbol(symbol)
    lots = float(lots); lots = lot_round(symbol, lots)
    etype = order_type(side, pending)
    price = None
    if pending:
        if entry is None: raise SystemExit("pending order requires --entry")
        price = float(entry)
    else:
        tick = mt5.symbol_info_tick(symbol)
        price = (tick.ask if side=="buy" else tick.bid)

    req = {
        "action": mt5.TRADE_ACTION_DEAL if pending is None else mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "type": etype,
        "volume": lots,
        "price": float(price),
        "deviation": 10,
        "type_filling": mt5.ORDER_FILLING_FOK,
        "comment": comment,
    }
    if sl: req["sl"] = float(sl)
    if tp: req["tp"] = float(tp)

    if pending is not None:
        req["type_time"] = mt5.ORDER_TIME_GTC

    r = mt5.order_send(req)
    if r is None: raise SystemExit(f"order_send None: {mt5.last_error()}")
    if r.retcode != mt5.TRADE_RETCODE_DONE:
        raise SystemExit(f"order failed retcode={r.retcode} {r.comment} {r.request}")
    return r

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--side", choices=["buy","sell"], required=True)
    ap.add_argument("--lots", type=float, required=True)
    ap.add_argument("--sl", type=float)
    ap.add_argument("--tp", type=float)
    ap.add_argument("--entry", type=float, help="prix d'entrée (si pending)")
    ap.add_argument("--pending", choices=["limit","stop"])
    a = ap.parse_args()

    info = connect()
    print(f"[NO_EA] account={info.login} balance={info.balance}")
    res = place(a.symbol, a.side, a.lots, a.sl, a.tp, a.entry, a.pending, comment="NO_EA")
    print(f"[NO_EA] sent: order={res.order} deal={res.deal} retcode={res.retcode}")
    mt5.shutdown()

if __name__ == "__main__":
    main()
