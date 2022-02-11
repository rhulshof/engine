import os
import sys
from contextlib import asynccontextmanager
from typing import Generator

from optuna import Trial

from cli.print_utils import print_error
from utils.error_handling import ErrorOutput, OfflineMissingDataError
from modules.output import OutputModule
from modules.setup import ConfigModule, DataModule, SetupModule
from modules.stats.stats import StatsModule
from modules.stats.tradingmodule import TradingModule
from modules.stats.tradingmodule_config import create_trading_module_config


class BacktestRunner:
    def __init__(self, config: ConfigModule, data_module: DataModule, algo_module, df, strategy, stats_config):
        self.data_module = data_module
        self.module = config
        self.stats_config = stats_config
        self.trading_module_config = create_trading_module_config(config)
        self.algo_module = algo_module
        self.df = df
        self.strategy = strategy

    def run_backtest(self):
        pair_dicts, dict_with_signals = self.algo_module.run()
        trading_module = TradingModule(self.trading_module_config, self.strategy)
        stats_module = StatsModule(self.stats_config, dict_with_signals, trading_module, pair_dicts)
        return stats_module.analyze()

    def run_hyperopt_iteration(self, trial: Trial) -> float:
        self.strategy.trial = trial
        stats = self.run_backtest()
        try:
            return self.strategy.loss_function(stats)
        except NotImplementedError:
            print_error("The Loss function isn't implemented in your strategy. For an example loss function, check out"
                        " our documentation at docs.dematrading.ai.")
            sys.exit()

    def run_outputted_backtest(self):
        stats = self.run_backtest()
        OutputModule(self.stats_config).output(stats, self.module.strategy_definition)

    @staticmethod
    def check_local_data(config: ConfigModule) -> None:

        dirpath = f'data/backtesting-data/{str(config.exchange).lower()}'

        try:
            if not os.path.exists(dirpath):
                raise OfflineMissingDataError()

            pairs = config.pairs

            for pair in pairs:
                pair = pair.replace('/', '')
                filename = f'data-{pair}{config.timeframe}.feather'

                if filename not in os.listdir(dirpath):
                    raise OfflineMissingDataError()

        except OfflineMissingDataError:
            ErrorOutput(sys.exc_info(),
                        add_info="You are trying to run an offline backtest on unavailable data. Either connect to the"
                                 "\n\tinternet to download it, or revise your config file to only include pairs you "
                                 "have saved locally.)",
                        stop=True).print_error()


@asynccontextmanager
async def create_backtest_runner(args: object, online: bool) -> Generator[BacktestRunner, None, None]:
    config_module = None
    try:
        config_module = await ConfigModule.create(args, online)
        if not online:
            BacktestRunner.check_local_data(config_module)
        data_module = await DataModule.create(config_module, online)
        setup_module = SetupModule(config_module, data_module)
        algo_module, df, strategy, stats_config = await setup_module.setup()
        backtest_runner = BacktestRunner(config_module, data_module, algo_module, df, strategy, stats_config)

        yield backtest_runner
    finally:
        if config_module is not None:
            await config_module.close()
