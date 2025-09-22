import MetaTrader5 as mt5, time

assert mt5.initialize()
symbol = "EURUSD"
mt5.symbol_select(symbol, True)
tick = mt5.symbol_info_tick(symbol)
sl = round(tick.ask - 0.0015, 5)  # ~15 pips
tp = round(tick.ask + 0.0015, 5)

req = dict(
    action=mt5.TRADE_ACTION_DEAL,
    symbol=symbol,
    volume=0.01,
    type=mt5.ORDER_TYPE_BUY,
    price=tick.ask,
    sl=sl,
    tp=tp,
    deviation=20,
    type_filling=mt5.ORDER_FILLING_FOK,
    magic=12345,
    comment="mt5py",
)

res = mt5.order_send(req)
if res.retcode == mt5.TRADE_RETCODE_INVALID_FILLING_MODE:
    req["type_filling"] = mt5.ORDER_FILLING_RETURN
    res = mt5.order_send(req)

print(res)
mt5.shutdown()
