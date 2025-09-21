# File: /FTMO_BOT_V2/src/bot/trading.py

class Trading:
    def __init__(self, api_client):
        self.api_client = api_client

    def place_order(self, symbol, quantity, order_type='market'):
        """
        Places an order in the market.

        :param symbol: The trading pair symbol (e.g., 'BTC/USD').
        :param quantity: The amount to trade.
        :param order_type: The type of order ('market' or 'limit').
        :return: Response from the API after placing the order.
        """
        order_data = {
            'symbol': symbol,
            'quantity': quantity,
            'order_type': order_type
        }
        response = self.api_client.place_order(order_data)
        return response

    def manage_trade(self, trade_id):
        """
        Manages an existing trade.

        :param trade_id: The ID of the trade to manage.
        :return: Trade details or status.
        """
        trade_details = self.api_client.get_trade_details(trade_id)
        return trade_details

    def close_trade(self, trade_id):
        """
        Closes an existing trade.

        :param trade_id: The ID of the trade to close.
        :return: Response from the API after closing the trade.
        """
        response = self.api_client.close_trade(trade_id)
        return response

    def get_open_trades(self):
        """
        Retrieves all open trades.

        :return: List of open trades.
        """
        open_trades = self.api_client.get_open_trades()
        return open_trades