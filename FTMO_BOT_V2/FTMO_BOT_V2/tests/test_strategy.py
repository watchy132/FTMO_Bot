import pytest

from src.bot.strategies import MovingAverageStrategy
from src.bot.utils import backtest_signals


def make_upward_prices(length=100, start=100.0, step=0.5):
    return [start + i * step for i in range(length)]


def test_moving_average_crossover_profitable_on_uptrend():
    prices = make_upward_prices(length=200, start=100.0, step=0.5)
    # short window reacts faster
    strat = MovingAverageStrategy(short_window=5, long_window=20)
    signals = strat.generate_signals(prices)

    # Ensure signals has same length
    assert len(signals) == len(prices)

    result = backtest_signals(prices, signals)
    total_return = result["total_return"]
    trades = result["trades"]

    # On a steady uptrend, expect at least one trade and positive return
    assert len(trades) >= 1
    assert total_return > 0


if __name__ == "__main__":
    pytest.main([__file__])
