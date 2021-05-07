# Libraries
from pathlib import Path
from os import path
import rapidjson
import numpy as np
import sys
sys.path.append('.')
from backtesting.backtesting import BackTesting as backtest
from models.trade import Trade

SPEND_AMOUNT = 100
FEE = 0.00

def test_config():
    assert (path.exists("config.json"))

def test_profit():
    # read test_data.json
    data_path = path.join(Path(__file__).parent, "test_data.json")
    assert (path.exists(data_path))
    with open(data_path, 'r') as data_file:
        data = data_file.read()
    data_dict = rapidjson.loads(data)

    ticks = data_dict.keys()
    trading = False
    total_profit = SPEND_AMOUNT
    for tick in ticks:
        if not trading:
            if data_dict[tick]['buy'] == 1:
                trading = True
                begin_tick = tick
        else:   # trading
            if data_dict[tick]['sell'] == 1:
                trading = False
                end_tick = tick
                profit_ratio_engine, profit_dollar_engine, max_seen_drawdown_engine = trade_profit(data_dict, begin_tick, end_tick)
                profit_ratio_simple, profit_dollar_simple = get_trade_profit(data_dict, begin_tick, end_tick)

                assert (profit_ratio_simple == profit_ratio_engine)
                assert (profit_dollar_simple == profit_dollar_engine)

                total_profit += profit_dollar_simple

    print("PROFIT: " + str(total_profit))





    # market_change = get_market_change(ticks, data_dict)
    # trade = Trade()
    # print(trade)
    # coin_res = backtest.generate_coin_results(closed_trades, market_change)
    # print(coin_res)

def trade_profit(data_dict, begin_time, end_time):
    ticks = data_dict.keys()
    starting_amount = SPEND_AMOUNT
    capital = SPEND_AMOUNT - (SPEND_AMOUNT * FEE)
    currency_amount = capital / data_dict[begin_time]['close']
    lowest_seen_price = np.inf

    for tick in ticks:
        if begin_time <= tick <= end_time:
            ohlcv = data_dict[tick]

            # update stats
            current = ohlcv['close']
            capital_low = currency_amount * ohlcv['low']

            # set profits
            capital = currency_amount * current
            # profit_ratio = capital / starting_amount
            # profit_dollar = capital - starting_amount

            # update max seen drawdown
            if capital_low < lowest_seen_price:
                lowest_seen_price = capital_low
                max_seen_drawdown = capital_low / starting_amount

    capital -= capital * FEE
    profit_ratio = capital / starting_amount
    profit_dollar = capital - starting_amount

    return profit_ratio, profit_dollar, max_seen_drawdown

def get_trade_profit(data_dict, begin_time, end_time):
    begin_price = data_dict[begin_time]['close']
    end_price = data_dict[end_time]['close']
    begin_amount = SPEND_AMOUNT
    capital = SPEND_AMOUNT - (SPEND_AMOUNT * FEE)
    currency_amount = capital / begin_price

    # set profits
    end_capital = (currency_amount * end_price)
    end_capital_with_fee = end_capital - (end_capital * FEE)
    profit_ratio = end_capital_with_fee / begin_amount
    profit_dollar = end_capital_with_fee - begin_amount

    return profit_ratio, profit_dollar

def get_market_change(ticks: list, data_dict: dict) -> dict:
    """
    Calculates the market change for every coin if bought at start and sold at end.

    :param ticks: list with all ticks
    :type ticks: list
    :param pairs: list of traded pairs
    :type pairs: list
    :param data_dict: dict containing OHLCV data per pair
    :type data_dict: dict
    :return: dict with market change per pair
    :rtype: dict
    """
    pairs = ['BTC/USDT']
    market_change = {}
    total_change = 0
    ticks = list(ticks)
    for pair in pairs:
        begin_value = data_dict[ticks[0]]['close']
        end_value = data_dict[ticks[-1]]['close']
        coin_change = end_value / begin_value
        market_change[pair] = coin_change
        total_change += coin_change
    market_change['all'] = total_change / len(pairs)
    return market_change

if __name__ == '__main__':
    test_profit()