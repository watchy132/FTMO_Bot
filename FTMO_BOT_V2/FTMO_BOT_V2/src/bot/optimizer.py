import csv
import itertools
from typing import List, Tuple

try:
    import matplotlib.pyplot as plt
    import numpy as np
except Exception:
    plt = None
    np = None

from src.bot.strategies import MovingAverageStrategy
from src.bot.backtest import Backtester


def grid_search_ma(
    prices: List[float],
    short_windows: List[int],
    long_windows: List[int],
    initial_capital: float = 10000.0,
    commission: float = 0.0,
    slippage: float = 0.0,
    risk_per_trade: float = 0.01,
    leverage: float = 1.0,
    position_sizing: str = "fixed",
) -> List[Tuple[int, int, dict]]:
    """
    Run grid search over combinations of short and long MA windows.

    Returns a list of tuples: (short, long, backtest_result)
    """
    results = []
    bt = Backtester(initial_capital=initial_capital, commission=commission, slippage=slippage)
    for short, long in itertools.product(short_windows, long_windows):
        if short >= long:
            continue
        strat = MovingAverageStrategy(short_window=short, long_window=long)
        signals = strat.generate_signals(prices)
        res = bt.run(prices, signals, risk_per_trade=risk_per_trade, leverage=leverage, position_sizing=position_sizing)
        results.append((short, long, res))
    return results


def save_results_csv(results: List[Tuple[int, int, dict]], filename: str = "grid_results.csv"):
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["short", "long", "total_return", "sharpe", "sortino", "cagr", "max_drawdown"])
        for short, long, res in results:
            writer.writerow(
                [
                    short,
                    long,
                    res.get("total_return"),
                    res.get("sharpe"),
                    res.get("sortino"),
                    res.get("cagr"),
                    res.get("max_drawdown"),
                ]
            )


def plot_heatmap(results: List[Tuple[int, int, dict]], filename: str = "heatmap.png"):
    """Plot heatmap of total_return over grid. Requires numpy & matplotlib."""
    if plt is None or np is None:
        raise RuntimeError("matplotlib and numpy are required for plotting")

    shorts = sorted(set(r[0] for r in results))
    longs = sorted(set(r[1] for r in results))
    grid = np.full((len(shorts), len(longs)), np.nan)
    short_index = {s: i for i, s in enumerate(shorts)}
    long_index = {l: j for j, l in enumerate(longs)}

    for short, long, res in results:
        grid[short_index[short], long_index[long]] = res.get("total_return", float("nan"))

    fig, ax = plt.subplots()
    c = ax.imshow(grid, aspect="auto", origin="lower", cmap="RdYlGn")
    ax.set_xticks(range(len(longs)))
    ax.set_xticklabels(longs)
    ax.set_yticks(range(len(shorts)))
    ax.set_yticklabels(shorts)
    ax.set_xlabel("Long window")
    ax.set_ylabel("Short window")
    fig.colorbar(c, ax=ax, label="Total return")
    fig.tight_layout()
    fig.savefig(filename)


def get_top_results(
    results: List[Tuple[int, int, dict]], top_n: int = 10, sort_key: str = "sharpe"
) -> List[Tuple[int, int, dict]]:
    """Return top_n results sorted by sort_key (descending)."""
    # flatten and sort
    flat = []
    for short, long, res in results:
        metric = res.get(sort_key)
        # fallback to total_return when metric is None
        if metric is None:
            metric = res.get("total_return", float("-inf"))
        flat.append((short, long, res, metric))

    flat_sorted = sorted(flat, key=lambda x: (x[3] if x[3] is not None else float("-inf")), reverse=True)
    top = [(s, l, r) for s, l, r, m in flat_sorted[:top_n]]
    return top


def save_top_csv(top_results: List[Tuple[int, int, dict]], filename: str = "top_results.csv"):
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "short", "long", "sharpe", "cagr", "total_return", "max_drawdown"])
        for i, (short, long, res) in enumerate(top_results, start=1):
            writer.writerow(
                [i, short, long, res.get("sharpe"), res.get("cagr"), res.get("total_return"), res.get("max_drawdown")]
            )


def walk_forward_evaluate(
    prices: List[float],
    short_windows: List[int],
    long_windows: List[int],
    train_size: int,
    test_size: int,
    step: int = None,
    position_sizing: str = "fixed",
    highs: List[float] = None,
    lows: List[float] = None,
    period: int = 14,
    atr_method: str = "sma",
) -> List[Tuple[int, int, dict]]:
    """
    Perform walk-forward (expanding window) evaluation for each MA combo.

    - train_size: initial training window length
    - test_size: rolling test window length
    - step: how much to move forward each iteration (default = test_size)

    Returns a list of (short, long, aggregated_metrics)
    where aggregated_metrics contains averages across folds (avg_sharpe, avg_cagr, avg_total_return).
    """
    if step is None:
        step = test_size

    combos = [(s, l) for s in short_windows for l in long_windows if s < l]
    # prepare metrics accumulator per combo
    metrics_acc = {combo: {"sharpe": [], "cagr": [], "total_return": [], "max_drawdown": []} for combo in combos}

    start = 0
    end = train_size
    while end + test_size <= len(prices):
        train_prices = prices[start:end]
        test_prices = prices[end : end + test_size]

        # evaluate each combo on this split, train on train_prices but using strategy with full history (we'll simulate by generating signals on concatenated series)
        for s, l in combos:
            # create strategy and signals using concatenated train+test to get proper indicators
            from src.bot.strategies import MovingAverageStrategy
            from src.bot.backtest import Backtester

            combo_prices = train_prices + test_prices
            strat = MovingAverageStrategy(short_window=s, long_window=l)
            signals = strat.generate_signals(combo_prices)

            # only keep test portion of signals (align to test_prices)
            test_signals = signals[len(train_prices) :]

            bt = Backtester(initial_capital=10000)
            # if highs/lows are provided for the full combo_prices, pass the test slice through
            test_highs = None
            test_lows = None
            if highs is not None and lows is not None:
                # ensure lists align lengthwise with prices
                combo_highs = highs[start : end + test_size]
                combo_lows = lows[start : end + test_size]
                test_highs = combo_highs[len(train_prices) :]
                test_lows = combo_lows[len(train_prices) :]

            res = bt.run(
                test_prices,
                test_signals,
                position_sizing=position_sizing,
                highs=test_highs,
                lows=test_lows,
                period=period,
                atr_method=atr_method,
            )

            metrics_acc[(s, l)]["sharpe"].append(res.get("sharpe"))
            metrics_acc[(s, l)]["cagr"].append(res.get("cagr"))
            metrics_acc[(s, l)]["total_return"].append(res.get("total_return"))
            metrics_acc[(s, l)]["max_drawdown"].append(res.get("max_drawdown"))

        # move window
        end += step

    # aggregate metrics
    aggregated = []
    for combo, vals in metrics_acc.items():

        def avg(lst):
            nums = [v for v in lst if v is not None]
            return sum(nums) / len(nums) if nums else None

        s, l = combo
        aggregated_metrics = {
            "avg_sharpe": avg(vals["sharpe"]),
            "avg_cagr": avg(vals["cagr"]),
            "avg_total_return": avg(vals["total_return"]),
            "avg_max_drawdown": avg(vals["max_drawdown"]),
        }
        aggregated.append((s, l, aggregated_metrics))

    return aggregated


def save_walkforward_csv(aggregated_results: List[Tuple[int, int, dict]], filename: str = "walkforward_results.csv"):
    """Save aggregated walk-forward results to CSV."""
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["short", "long", "avg_sharpe", "avg_cagr", "avg_total_return", "avg_max_drawdown"])
        for short, long, metrics in aggregated_results:
            writer.writerow(
                [
                    short,
                    long,
                    metrics.get("avg_sharpe"),
                    metrics.get("avg_cagr"),
                    metrics.get("avg_total_return"),
                    metrics.get("avg_max_drawdown"),
                ]
            )


def save_walkforward_json(aggregated_results: List[Tuple[int, int, dict]], filename: str = "walkforward_results.json"):
    """Save aggregated walk-forward results to JSON."""
    try:
        import json
    except Exception:
        raise

    payload = []
    for short, long, metrics in aggregated_results:
        entry = {"short": short, "long": long}
        entry.update(metrics)
        payload.append(entry)

    with open(filename, "w") as f:
        json.dump(payload, f, indent=2)


def save_top_from_walkforward(
    aggregated_results: List[Tuple[int, int, dict]],
    top_n: int = 10,
    sort_key: str = "avg_sharpe",
    filename: str = "wf_top.csv",
):
    """Select top-N combos from walk-forward aggregated results and save to CSV."""
    flat = []
    for short, long, metrics in aggregated_results:
        val = metrics.get(sort_key)
        if val is None:
            val = metrics.get("avg_total_return", float("-inf"))
        flat.append((short, long, metrics, val))

    flat_sorted = sorted(flat, key=lambda x: (x[3] if x[3] is not None else float("-inf")), reverse=True)
    top = flat_sorted[:top_n]

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "short", "long", sort_key])
        for i, (s, l, metrics, val) in enumerate(top, start=1):
            writer.writerow([i, s, l, val])
