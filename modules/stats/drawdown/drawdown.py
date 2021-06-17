import pandas as pd


def get_max_drawdown_ratio(df: pd.DataFrame):
    """
    @param df: with column["value"]
    """
    cummax = df["value"].cummax()
    df["drawdown_ratio"] = 1 + (df["value"] - cummax) / cummax
    return df["drawdown_ratio"].min()
