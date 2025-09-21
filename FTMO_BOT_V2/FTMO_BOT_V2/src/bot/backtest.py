from typing import List, Dict, Optional
import math
import statistics
try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None


class Backtester:
    """Simple backtester supporting commission, slippage, position sizing and leverage.

    Usage:
      bt = Backtester(initial_capital=10000, commission=0.0005, slippage=0.0005)
      result = bt.run(prices, signals, risk_per_trade=0.01, leverage=1.0)

    Returns a dict with equity_curve, trades, total_return, max_drawdown
    """

    def __init__(self, initial_capital=10000.0, commission=0.0, slippage=0.0):
        self.initial_capital = float(initial_capital)
        self.commission = float(commission)
        self.slippage = float(slippage)

    def run(self,
        prices: List[float],
        signals: List[int],
        risk_per_trade: float = 0.01,
        leverage: float = 1.0,
        position_sizing: str = 'fixed',
        highs: Optional[List[float]] = None,
        lows: Optional[List[float]] = None,
        period: int = 14,
        annualization: int = 252,
        atr_method: str = 'sma'
        ) -> Dict:
        if not prices or not signals or len(prices) != len(signals):
            raise ValueError("prices and signals must be non-empty and the same length")

        equity = self.initial_capital
        equity_curve = []
        position = 0  # 0 flat, 1 long
        entry_price = None
        entry_units = 0.0
        trades = []

        peak = equity
        drawdowns = []

        # precompute ATR if requested
        atr = None
        if position_sizing == 'atr':
            # compute TR series and ATR using highs/lows/closes if provided
            tr = []
            for j in range(len(prices)):
                high = highs[j] if highs is not None else prices[j]
                low = lows[j] if lows is not None else prices[j]
                prev = prices[j - 1] if j > 0 else prices[j]
                tr_val = max(high - low, abs(high - prev), abs(low - prev))
                tr.append(tr_val)
            atr = [None] * len(tr)
            if atr_method == 'sma':
                # simple moving average ATR
                cum = 0.0
                for j, t in enumerate(tr):
                    cum += t
                    if j >= period:
                        cum -= tr[j - period]
                    if j >= period - 1:
                        atr[j] = cum / period
                    else:
                        atr[j] = None
            elif atr_method == 'wilder':
                # Wilder's EMA-style ATR
                # initialize first ATR as simple average of first 'period' TRs when available
                prev_atr = None
                for j, t in enumerate(tr):
                    if j < period - 1:
                        atr[j] = None
                        continue
                    if j == period - 1:
                        # simple average for first ATR
                        first_atr = sum(tr[0:period]) / period
                        atr[j] = first_atr
                        prev_atr = first_atr
                    else:
                        # Wilder smoothing: ATR = (prev_atr*(period-1) + TR) / period
                        prev_atr = (prev_atr * (period - 1) + t) / period
                        atr[j] = prev_atr
            else:
                raise ValueError(f"Unknown atr_method: {atr_method}")

        for i, (p, s) in enumerate(zip(prices, signals)):
            # entry
            if position == 0 and s == 1:
                # determine units using either fixed risk fraction or ATR-based sizing
                if position_sizing == 'fixed' or atr is None or atr[i] is None:
                    # allocate risk_per_trade fraction of equity (simplified)
                    budget = equity * risk_per_trade * leverage
                    entry_units = budget / p if p > 0 else 0.0
                else:
                    # ATR-based: use risk_per_trade fraction of equity divided by ATR to size position
                    current_atr = atr[i]
                    # units = (risk_per_trade * equity * leverage) / (atr * price) conservatively
                    if current_atr <= 0:
                        entry_units = 0.0
                    else:
                        entry_units = (risk_per_trade * equity * leverage) / (current_atr * p)
                entry_price = p * (1 + self.slippage)
                # commission on buy
                commission_cost = entry_units * entry_price * self.commission
                equity -= commission_cost
                position = 1
                trades.append({'type': 'entry', 'index': i, 'price': entry_price, 'units': entry_units, 'commission': commission_cost})

            # exit
            elif position == 1 and s == 0:
                exit_price = p * (1 - self.slippage)
                pnl = (exit_price - entry_price) * entry_units * leverage
                commission_cost = entry_units * exit_price * self.commission
                equity += pnl
                equity -= commission_cost
                trades.append({'type': 'exit', 'index': i, 'price': exit_price, 'units': entry_units, 'pnl': pnl, 'commission': commission_cost})
                # reset
                position = 0
                entry_price = None
                entry_units = 0.0

            equity_curve.append(equity)
            if equity > peak:
                peak = equity
            drawdowns.append((peak - equity) / peak if peak > 0 else 0.0)

        # close any open position at last price
        if position == 1 and entry_price is not None:
            last_price = prices[-1] * (1 - self.slippage)
            pnl = (last_price - entry_price) * entry_units * leverage
            commission_cost = entry_units * last_price * self.commission
            equity += pnl
            equity -= commission_cost
            trades.append({'type': 'exit', 'index': len(prices) - 1, 'price': last_price, 'units': entry_units, 'pnl': pnl, 'commission': commission_cost})
            equity_curve[-1] = equity
            if equity > peak:
                peak = equity
            drawdowns.append((peak - equity) / peak if peak > 0 else 0.0)

        total_return = (equity - self.initial_capital) / self.initial_capital
        max_drawdown = max(drawdowns) if drawdowns else 0.0

        # compute returns series from equity curve
        returns = []
        for k in range(1, len(equity_curve)):
            prev = equity_curve[k - 1]
            cur = equity_curve[k]
            if prev != 0:
                returns.append((cur - prev) / prev)

        # annualize factor
        def annualize(mean_ret, ann_factor):
            return mean_ret * ann_factor

        # Sharpe: use mean(return)/std(return) * sqrt(annualization)
        sharpe = None
        sortino = None
        if returns:
            mean_r = statistics.mean(returns)
            std_r = statistics.pstdev(returns) if len(returns) > 1 else 0.0
            if std_r > 0:
                sharpe = (mean_r / std_r) * math.sqrt(annualization)
            # downside deviation for Sortino
            neg_returns = [r for r in returns if r < 0]
            if neg_returns:
                dd = statistics.pstdev(neg_returns)
                if dd > 0:
                    sortino = (mean_r / dd) * math.sqrt(annualization)

        # additional metrics
        cagr = None
        ann_vol = None
        win_rate = None
        n_periods = len(prices)
        if n_periods > 0:
            years = n_periods / annualization
            if years > 0:
                ending = equity
                starting = self.initial_capital
                try:
                    cagr = (ending / starting) ** (1.0 / years) - 1.0
                except Exception:
                    cagr = None
        if returns:
            ann_vol = statistics.pstdev(returns) * math.sqrt(annualization) if len(returns) > 1 else 0.0

        # compute win rate from trades (exits contain 'pnl')
        exit_pnls = [t['pnl'] for t in trades if t.get('type') == 'exit' and 'pnl' in t]
        if exit_pnls:
            wins = sum(1 for p in exit_pnls if p > 0)
            win_rate = wins / len(exit_pnls)

        result = {
            'equity_curve': equity_curve,
            'trades': trades,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'returns': returns,
            'sharpe': sharpe,
            'sortino': sortino,
            'atr': atr,
            'cagr': cagr,
            'annual_volatility': ann_vol,
            'win_rate': win_rate,
        }

        return result

    def plot_equity(self, equity_curve: List[float], filename: str = 'equity.png'):
        """Save a plot of the equity curve to `filename`. Requires matplotlib."""
        if plt is None:
            raise RuntimeError("matplotlib is not available")
        fig, ax = plt.subplots()
        ax.plot(equity_curve, label='Equity')
        ax.set_xlabel('Period')
        ax.set_ylabel('Equity')
        ax.legend()
        fig.tight_layout()
        fig.savefig(filename)
