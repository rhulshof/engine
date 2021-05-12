from dataclasses import dataclass

from pandas import DataFrame

from backtesting.results import MainResults, CoinInsights, OpenTradeResult
from modules.pairs_data import PairsData


@dataclass
class TradingStats:
    main_results: MainResults
    coin_res: list[CoinInsights]
    open_trade_res: list[OpenTradeResult]
    frame_with_signals: PairsData
    buypoints: dict
    sellpoints: dict
    df: DataFrame
