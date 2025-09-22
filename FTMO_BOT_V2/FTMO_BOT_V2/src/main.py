# filepath: /FTMO_BOT_V2/src/main.py

from bot.all_in_one import TradingBot
from bot.strategies import MovingAverageStrategy


def main():
    print("Starting FTMO_BOT_V2...")
    bot = TradingBot()
    # Add a default strategy so the bot has something to run.
    # Best combo from grid report (auto-selected): short=3, long=40
    ma = MovingAverageStrategy(short_window=3, long_window=40)
    bot.add_strategy(ma)
    bot.set_strategy("Moving Average Strategy")
    print("Registered default strategy: Moving Average Strategy")
    bot.start_trading()
    print("Bot start requested.")


if __name__ == "__main__":
    main()
