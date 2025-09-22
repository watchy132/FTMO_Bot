# filepath: /FTMO_BOT_V2/tests/test_bot.py

import unittest
from src.bot.all_in_one import TradingBot  # Adjust the import based on the actual class/function names
from src.bot.strategies import StrategyA, StrategyB  # Example strategies
from src.config.settings import Settings  # Example settings import


class TestTradingBot(unittest.TestCase):

    def setUp(self):
        self.bot = TradingBot(settings=Settings())
        self.strategy_a = StrategyA()
        self.strategy_b = StrategyB()

    def test_initialization(self):
        self.assertIsNotNone(self.bot)
        self.assertEqual(self.bot.current_strategy, None)

    def test_add_strategy(self):
        self.bot.add_strategy(self.strategy_a)
        self.assertIn(self.strategy_a, self.bot.strategies)

    def test_execute_strategy(self):
        self.bot.add_strategy(self.strategy_a)
        result = self.bot.execute_strategy(self.strategy_a)
        self.assertTrue(result)  # Assuming the strategy returns a boolean

    def test_strategy_failure(self):
        self.bot.add_strategy(self.strategy_b)
        result = self.bot.execute_strategy(self.strategy_b)
        self.assertFalse(result)  # Assuming the strategy returns a boolean


if __name__ == "__main__":
    unittest.main()
