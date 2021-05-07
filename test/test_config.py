# Libraries
from pathlib import Path
from os import path
import rapidjson
import numpy as np

SPEND_AMOUNT = 100
FEE = 0.0025

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

    return profit_ratio, profit_dollar,

if __name__ == '__main__':
    test_profit()