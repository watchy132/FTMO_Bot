# filepath: /FTMO_BOT_V2/src/config/settings.py

API_KEY = "your_api_key_here"
API_SECRET = "your_api_secret_here"
BASE_URL = "https://api.yourtradingplatform.com"
TRADING_PAIR = "BTC/USD"
ORDER_SIZE = 0.01
SLIPPAGE = 0.5
TIMEFRAME = "1m"
MAX_OPEN_TRADES = 5
LOG_LEVEL = "INFO"


class Settings:
	"""Lightweight Settings object used by tests and for compatibility.

	Attributes mirror module-level constants for convenience.
	"""
	def __init__(self):
		self.API_KEY = API_KEY
		self.API_SECRET = API_SECRET
		self.BASE_URL = BASE_URL
		self.TRADING_PAIR = TRADING_PAIR
		self.ORDER_SIZE = ORDER_SIZE
		self.SLIPPAGE = SLIPPAGE
		self.TIMEFRAME = TIMEFRAME
		self.MAX_OPEN_TRADES = MAX_OPEN_TRADES
		self.LOG_LEVEL = LOG_LEVEL