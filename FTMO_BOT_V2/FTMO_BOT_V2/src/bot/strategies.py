class Strategy:
    def __init__(self, name):
        self.name = name

    def execute(self, data):
        raise NotImplementedError("This method should be overridden by subclasses")


class MovingAverageStrategy(Strategy):
    def __init__(self, short_window, long_window):
        super().__init__("Moving Average Strategy")
        self.short_window = short_window
        self.long_window = long_window

    def _sma(self, series, window):
        """Compute simple moving average for a list-like of numbers."""
        if window <= 0:
            raise ValueError("window must be > 0")
        sma = []
        cum = 0.0
        for i, v in enumerate(series):
            cum += v
            if i >= window:
                cum -= series[i - window]
            if i >= window - 1:
                sma.append(cum / window)
            else:
                sma.append(None)
        return sma

    def generate_signals(self, prices):
        """
        Generate signals array from price series.

        Signals: 1 -> long, 0 -> flat/neutral
        Signal entry when short_sma crosses above long_sma.
        Exit when short_sma crosses below long_sma.
        """
        if prices is None or len(prices) == 0:
            return []

        short = self._sma(prices, self.short_window)
        long = self._sma(prices, self.long_window)

        signals = [0] * len(prices)
        prev_short = None
        prev_long = None
        position = 0
        for i in range(len(prices)):
            s = short[i]
            l = long[i]
            if s is None or l is None:
                signals[i] = 0
            else:
                # If this is the first point where both SMAs are available,
                # set the initial position according to the current comparison.
                if prev_short is None or prev_long is None:
                    position = 1 if s > l else 0
                else:
                    # cross up
                    if prev_short <= prev_long and s > l:
                        position = 1
                    # cross down
                    elif prev_short >= prev_long and s < l:
                        position = 0
                signals[i] = position
            prev_short = s
            prev_long = l
        return signals

    def execute(self, data):
        """Expect data to be a list-like of prices. Return generated signals."""
        prices = data
        return self.generate_signals(prices)


class RSI_Strategy(Strategy):
    def __init__(self, period):
        super().__init__("RSI Strategy")
        self.period = period

    def execute(self, data):
        # Implement RSI logic here
        pass


class MACD_Strategy(Strategy):
    def __init__(self, short_window, long_window, signal_window):
        super().__init__("MACD Strategy")
        self.short_window = short_window
        self.long_window = long_window
        self.signal_window = signal_window

    def execute(self, data):
        # Implement MACD logic here
        pass


class StrategyA(Strategy):
    def __init__(self):
        super().__init__("StrategyA")

    def execute(self, data=None):
        # Simple deterministic successful execution for tests
        return True


class StrategyB(Strategy):
    def __init__(self):
        super().__init__("StrategyB")

    def execute(self, data=None):
        # Simple deterministic failing execution for tests
        return False