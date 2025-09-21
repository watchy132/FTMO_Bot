# filepath: /FTMO_BOT_V2/src/bot/all_in_one.py

# This file contains the main logic for the trading bot, integrating various strategies and functionalities.

class TradingBot:
    def __init__(self, settings=None):
        """Initialize the TradingBot.

        :param settings: Optional settings object (kept for compatibility with tests/projects)
        """
        self.settings = settings
        self.strategies = []
        self.current_strategy = None

    def add_strategy(self, strategy):
        self.strategies.append(strategy)

    def set_strategy(self, strategy_name):
        for strategy in self.strategies:
            if strategy.name == strategy_name:
                self.current_strategy = strategy
                break
        else:
            raise ValueError(f"Strategy {strategy_name} not found.")

    def execute_strategy(self, strategy_or_data=None):
        """Execute a strategy.

        Usage:
        - execute_strategy(strategy_obj) -> executes the provided strategy object and returns its result
        - execute_strategy() -> executes the currently set strategy (self.current_strategy)

        :param strategy_or_data: Optional Strategy instance to execute or data payload (legacy).
        :return: Whatever the strategy.execute(...) returns.
        """
        # If a Strategy object was passed directly, execute it.
        strategy = None
        # Duck-typing check for an object with an execute method
        if strategy_or_data is not None and hasattr(strategy_or_data, 'execute'):
            strategy = strategy_or_data
        else:
            strategy = self.current_strategy

        if strategy is None:
            raise RuntimeError("No strategy set.")

        # Attempt to call execute and return its result. Support both signatures.
        try:
            return strategy.execute()
        except TypeError:
            # If strategy expects data, pass None (or the provided data)
            try:
                return strategy.execute(strategy_or_data)
            except TypeError:
                # As a last resort, call without arguments and return None
                strategy.execute()
                return None

    def start_trading(self, data=None):
        """Backward compatible entry point to start trading."""
        print("TradingBot: start_trading called")
        result = self.execute_strategy(data)
        print("TradingBot: execute_strategy returned:", result)
        return result

if __name__ == "__main__":
    bot = TradingBot()
    # Example of adding strategies and executing one
    # bot.add_strategy(SomeStrategy())
    # bot.set_strategy("SomeStrategy")
    # bot.execute_strategy()