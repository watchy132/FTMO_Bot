import pytest

from src.bot.strategies import MovingAverageStrategy
from src.bot.backtest import Backtester


def make_upward_prices(length=200, start=100.0, step=0.5):
    return [start + i * step for i in range(length)]


def test_backtester_returns_positive_on_uptrend():
    prices = make_upward_prices(length=300, start=100.0, step=0.5)
    strat = MovingAverageStrategy(short_window=5, long_window=20)
    signals = strat.generate_signals(prices)

    bt = Backtester(initial_capital=10000.0, commission=0.0005, slippage=0.0002)
    result = bt.run(prices, signals, risk_per_trade=0.02, leverage=1.0)

    assert 'total_return' in result
    assert result['total_return'] > 0
    # basic sanity checks
    assert result['max_drawdown'] >= 0
    assert isinstance(result['equity_curve'], list)

    # new metrics
    assert 'sharpe' in result
    assert 'sortino' in result
    assert 'cagr' in result
    assert 'annual_volatility' in result
    assert 'win_rate' in result

    # run with ATR-based sizing and Wilder ATR
    bt2 = Backtester(initial_capital=10000.0, commission=0.0005, slippage=0.0002)
    res2 = bt2.run(prices, signals, risk_per_trade=0.02, leverage=1.0, position_sizing='atr', atr_method='wilder')
    assert res2['total_return'] > 0
    assert res2['atr'] is not None


if __name__ == '__main__':
    pytest.main([__file__])
