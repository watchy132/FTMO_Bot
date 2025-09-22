import MetaTrader5 as mt5

mt5.initialize()
for p in mt5.positions_get() or []:
    is_buy = p.type == mt5.POSITION_TYPE_BUY
    typ = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
    tick = mt5.symbol_info_tick(p.symbol)
    price = tick.bid if typ == mt5.ORDER_TYPE_SELL else tick.ask
    r = mt5.order_send(
        {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": p.symbol,
            "volume": p.volume,
            "type": typ,
            "position": p.ticket,
            "price": price,
            "deviation": 100,
        }
    )
    print(
        "close",
        p.ticket,
        "retcode",
        getattr(r, "retcode", None),
        getattr(r, "comment", None),
    )
print("pos_after", mt5.positions_total())
