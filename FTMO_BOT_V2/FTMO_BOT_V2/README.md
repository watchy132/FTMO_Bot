# CI: replace OWNER/REPO with your GitHub repository to enable the badge
[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)

# FTMO_BOT_V2

## Overview
FTMO_BOT_V2 is a trading bot designed to automate trading strategies in financial markets. This project integrates various functionalities to provide a comprehensive trading solution.

## Directory Structure
```
FTMO_BOT_V2
├── src
│   ├── bot
│   │   ├── __init__.py
│   │   ├── all_in_one.py
│   │   ├── strategies.py
│   │   ├── trading.py
│   │   └── utils.py
│   ├── config
│   │   └── settings.py
│   └── main.py
├── tests
│   ├── __init__.py
│   └── test_bot.py
├── scripts
│   └── run_bot.sh
├── .env.example
├── requirements.txt
├── pyproject.toml
├── setup.cfg
└── README.md
```

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```
   cd FTMO_BOT_V2
   ```
3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Configuration
- Copy the `.env.example` file to `.env` and fill in the necessary environment variables.
- Modify `src/config/settings.py` to adjust any configuration settings as needed.

## Usage
To run the bot, execute the following command:
```
bash scripts/run_bot.sh
```

## Backtesting and metrics
The project includes a lightweight backtester with support for ATR-based position sizing and performance metrics (Sharpe, Sortino).

Quick example (from project root):
```
source .venv/bin/activate
python - <<'PY'
from src.bot.strategies import MovingAverageStrategy
from src.bot.backtest import Backtester
prices = [100 + i*0.5 for i in range(300)]
strat = MovingAverageStrategy(5,20)
signals = strat.generate_signals(prices)
bt = Backtester(initial_capital=10000, commission=0.0005, slippage=0.0002)
res = bt.run(prices, signals, risk_per_trade=0.02, leverage=1.0, position_sizing='atr')
print('Total return:', res['total_return'])
print('Sharpe:', res['sharpe'])
print('Sortino:', res['sortino'])
print('Max drawdown:', res['max_drawdown'])
PY
```

Notes:
- `position_sizing='fixed'` (default) or `'atr'` (uses ATR to size position).
- If you have OHLC data, pass `highs` and `lows` to `Backtester.run(...)` for a more accurate ATR.
- Sharpe/Sortino are computed on equity-curve step returns and annualized by default (252 periods/year).

## Testing
To run the tests, use the following command:
```
pytest tests/
```

## Contributing
Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.