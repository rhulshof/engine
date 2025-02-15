# Libraries
import asyncio
import os
import sys
from os import path
from typing import Optional

import numpy as np
import pandas as pd
import rapidjson
from pandas import DataFrame

from cli.print_utils import print_info, print_error, print_warning
# Files
from modules.setup.config import ConfigModule
from modules.stats.drawdown.drawdown import get_max_drawdown_ratio
from utils.utils import get_ohlcv_indicators, parse_timeframe

# ======================================================================
# DataModule is responsible for downloading OHLCV data, preparing it
# and activating backtesting methods
#
# © 2021 DemaTrading.ai
# ======================================================================

milliseconds = 1000
minute = 60 * milliseconds
hour = 60 * minute
day = 24 * hour


class DataModule:

    def __init__(self):
        self.config = None
        self.exchange = None

    @staticmethod
    async def create(config: ConfigModule):
        print_info('Starting DemaTrading.ai data-module...')
        data_module = DataModule()
        data_module.config = config
        data_module.exchange = config.exchange
        await data_module.load_markets()
        return data_module

    async def load_btc_marketchange(self):
        print_info("Fetching market change of BTC/USDT...")
        begin_data = await self.exchange.fetch_ohlcv(symbol='BTC/USDT', timeframe=self.config.timeframe,
                                                     since=self.config.backtesting_from, limit=1)
        end_timestamp = int(np.floor(self.config.backtesting_to / self.config.timeframe_ms) * self.config.timeframe_ms) - self.config.timeframe_ms
        end_data = await self.exchange.fetch_ohlcv(symbol='BTC/USDT', timeframe=self.config.timeframe, since=end_timestamp,
                                                   limit=1)

        begin_close_value = begin_data[0][4]
        end_close_value = end_data[0][4]
        return end_close_value / begin_close_value

    async def load_btc_drawdown(self, df: dict):
        print_info("Fetching market drawdown of BTC/USDT...")

        if 'BTC/USDT' in df.keys():
            bitcoin_df = df.get('BTC/USDT')
        else:
            pair, bitcoin_df = await self.get_pair_data('BTC/USDT', self.config.timeframe)
        bitcoin_values = bitcoin_df[['close']].rename(columns={'close': 'value'})

        bitcoin_drawdown = get_max_drawdown_ratio(bitcoin_values)
        return bitcoin_drawdown

    async def load_historical_data(self, pairs, check_backtesting_period=True) -> dict:
        dataframes = await asyncio.gather(*[self.get_pair_data(pair, self.config.timeframe) if not isinstance(pair, tuple)
                                            else self.get_pair_data(pair[0], pair[1]) for pair in pairs])   # if tuple then additional pair and timeframe comes specified with it

        history_data = {key: value for [key, value] in dataframes}

        self.warn_if_missing_ticks(history_data)
        if check_backtesting_period and not is_same_backtesting_period(history_data):
            raise Exception("[ERROR] Dataframes don't have equal backtesting periods.")
        return history_data

    async def get_pair_data(self, pair, timeframe):
        self.config.timeframe = timeframe
        self.config.timeframe_ms = parse_timeframe(timeframe)

        if self.is_datafolder_exist(pair):
            print_info("Reading datafile for %s." % pair)
            try:
                df = await self.read_data_from_datafile(pair)
            except rapidjson.JSONDecodeError:
                print_info("Unable to read datafile for %s, starting download..." % pair)
                df = await self.download_data_for_pair(pair, self.config.backtesting_from, self.config.backtesting_to)
        else:
            print_info("Did not find datafile for %s, starting download..." % pair)
            df = await self.download_data_for_pair(pair, self.config.backtesting_from, self.config.backtesting_to)
        return pair, df

    async def load_markets(self) -> None:
        await self.exchange.load_markets()

    async def download_data_for_pair(self, pair: str, data_from: int, data_to: int, save: bool = True) -> DataFrame:
        start_date = data_from
        fetch_ohlcv_limit = 1000

        if save:
            print_info("Downloading %s's data" % pair)

        slice_request_payloads = []
        while start_date < data_to:
            # Request ticks for given pair (maximum = 1000)
            remaining_ticks = (data_to - start_date) / self.config.timeframe_ms
            asked_ticks = min(remaining_ticks, fetch_ohlcv_limit)
            slice_request_payloads.append([asked_ticks, start_date])
            start_date += np.around(asked_ticks * self.config.timeframe_ms)

        results = await asyncio.gather(*[self.exchange.fetch_ohlcv(symbol=pair,
                                                                   timeframe=self.config.timeframe,
                                                                   since=int(start_date),
                                                                   limit=int(asked_ticks)) for [asked_ticks, start_date]
                                         in slice_request_payloads])

        index = [candle[0] for results in results for candle in results]  # timestamps
        ohlcv_data = [candle for results in results for candle in results]

        # Create pandas DataFrame and adds pair info
        df = DataFrame(ohlcv_data, index=index, columns=get_ohlcv_indicators()[:-3])
        df['pair'] = pair
        df['buy'], df['sell'] = 0, 0  # default values

        # Create missing NaN data
        df = self.fill_missing_ticks(df, pair, data_from, data_to)

        if save:
            print_info("[%s] %s candles downloaded." % (pair, len(index)))
            self.save_dataframe(pair, df)

        return df

    def is_datafolder_exist(self, pair: str) -> bool:
        # Check if datafolder exists
        filename = self.generate_datafile_name(pair)
        exchange_path = os.path.join("data/backtesting-data", self.config.exchange_name)
        if not path.exists(exchange_path):
            self.create_directory(exchange_path)

        # Checks if datafile exists
        dir_path = os.path.join(exchange_path, filename)
        return path.exists(dir_path)

    @staticmethod
    def create_directory(directory: str) -> None:
        try:
            os.makedirs(directory)
        except OSError:
            print_error("Creation of the directory %s failed" % directory)
        else:
            print_info("Successfully created the directory %s " % directory)

    async def read_data_from_datafile(self, pair: str) -> Optional[DataFrame]:
        filename = self.generate_datafile_name(pair)
        filepath = os.path.join("data/backtesting-data/", self.config.exchange_name, filename)
        try:
            df = pd.read_feather(filepath, columns=get_ohlcv_indicators() + ["index"])
            df.set_index("index", inplace=True)

        except FileNotFoundError:
            print_error("Backtesting datafile was not found.")
            return None
        except EnvironmentError:
            print_error(f"Something went wrong loading datafile {sys.exc_info()[0]}")
            return None
        except rapidjson.JSONDecodeError:
            os.remove(filepath)
            raise

        # Find correct last tick timestamp
        n_downloaded_candles = (self.config.backtesting_to - self.config.backtesting_from) / self.config.timeframe_ms
        timesteps_forward = int(n_downloaded_candles) * self.config.timeframe_ms
        final_timestamp = self.config.backtesting_from + (
                timesteps_forward - self.config.timeframe_ms)  # last tick is excluded


        # Return correct backtesting period
        df = await self.check_backtesting_period(pair, df, final_timestamp)

        begin_index = df.index.get_loc(self.config.backtesting_from)
        end_index = df.index.get_loc(final_timestamp)
        self.save_dataframe(pair, df)

        df = df[begin_index:end_index + 1]
        return df

    async def check_backtesting_period(self, pair: str, df: DataFrame, final_timestamp: int) -> DataFrame:
        """
        :param pair: Certain coin pair in "AAA/BBB" format
        :type pair: string
        :param df: Dataframe containing backtest information
        :type df: DataFrame
        :param final_timestamp: Timestamp to which the dataframe has gathered info
        :type final_timestamp: int
        :return: Dataframe with possibly additional info
        :rtype: DataFrame
        """

        # Get backtesting period
        index_list = df.index.values
        df_begin = index_list[0]
        df_end = index_list[-1]
        extra_candles = 0
        notify = True  # Used for printing message once (improved readability)

        # Check if previous data needs to be downloaded
        if self.config.backtesting_from < df_begin:
            print_info("Incomplete datafile. Downloading extra candle(s)...")
            notify = False
            prev_df = await self.download_data_for_pair(pair, self.config.backtesting_from, df_begin, save=False)
            df = pd.concat([prev_df, df])
            extra_candles += len(prev_df.index)

        # Check if new data needs to be downloaded
        if final_timestamp > df_end:
            if notify:
                print_info("Incomplete datafile. Downloading extra candle(s)...")
            new_df = await self.download_data_for_pair(pair, df_end + self.config.timeframe_ms,
                                                       self.config.backtesting_to,
                                                       save=False, start=False)
            df = pd.concat([df, new_df])
            extra_candles += len(new_df.index)

        # Check if new candles were downloaded
        if extra_candles > 0:
            print_info("[%s] %s extra candle(s) downloaded." % (pair, extra_candles))

        return df

    def save_dataframe(self, pair: str, df: DataFrame) -> None:
        filename = self.generate_datafile_name(pair)
        filepath = os.path.join("data/backtesting-data/", self.config.exchange_name, filename)

        # Convert pandas dataframe to json
        df.reset_index().to_feather(filepath)

    def generate_datafile_name(self, pair: str) -> str:
        coin, base = pair.split('/')
        return "data-{}{}{}.feather".format(coin, base, self.config.timeframe)

    def remove_backtesting_file(self, pair: str) -> None:
        filename = self.generate_datafile_name(pair)
        filepath = os.path.join("data/backtesting-data/", self.config.exchange, filename)
        os.remove(filepath)

    def warn_if_missing_ticks(self, history_data: dict) -> None:

        for pair, data in history_data.items():
            n_missing = data['close'].isnull().sum()

            if n_missing > 0:
                print_warning(f"Pair '{pair}' is missing {n_missing} ticks (rows)")

    def fill_missing_ticks(self, df, pair, data_from, data_to):
        """
        Replace missing ticks by NaN
        :param df: Downloaded data
        :type df: DataFrame
        :return: Complete df of the whole daterange
        :rtype: DataFrame
        """
        daterange = np.arange(data_from,
                              data_to,
                              self.config.timeframe_ms)

        # print_warning(f"Pair '{pair}' did not exist at start-time")
        nandf = pd.DataFrame(np.nan, index=daterange, columns=df.keys())
        nandf["time"] = daterange
        nandf["pair"] = pair

        nandf.update(df)
        return nandf


def is_same_backtesting_period(history_data) -> bool:
    df_lengths = [len(df.index.values) for df in history_data.values()]
    return all(length == df_lengths[0] for length in df_lengths)
