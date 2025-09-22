def some_utility_function():
    # This is a placeholder for a utility function.
    pass


def another_utility_function(param):
    # This is a placeholder for another utility function.
    return param


def backtest_signals(prices, signals):
    """Simple backtest: long-only strategy using discrete signals.

    - `prices`: list of floats (price series)
    - `signals`: list of 0/1 values same length as prices; signal=1 means in position

    Execution assumptions:
    - We take position changes at the close price of the current bar.
    - When signal goes from 0 to 1, we buy at that price.
    - When signal goes from 1 to 0, we sell at that price.
    - If the signal remains 1 at the end, we close at the last price.

    Returns: dict with keys: total_return (percent), trades (list of trade pnl values)
    """
    if not prices or not signals or len(prices) != len(signals):
        raise ValueError("prices and signals must be non-empty and the same length")

    in_position = False
    entry_price = None
    trades = []

    for p, s in zip(prices, signals):
        if not in_position and s == 1:
            in_position = True
            entry_price = p
        elif in_position and s == 0:
            # close trade
            pnl = (p - entry_price) / entry_price
            trades.append(pnl)
            in_position = False
            entry_price = None

    # close any open position at the last price
    if in_position and entry_price is not None:
        last_price = prices[-1]
        pnl = (last_price - entry_price) / entry_price
        trades.append(pnl)

    # total return as compounded returns across trades assuming full allocation per trade
    total = 1.0
    for t in trades:
        total *= 1 + t

    return {"total_return": (total - 1.0), "trades": trades}
