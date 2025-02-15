from datetime import datetime
from pathlib import Path
import pandas as pd

from plotly import graph_objects as go

def equity_plot(capital_dict):
    Path("data/backtesting-data/plots/equity").mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(list(capital_dict.items()))

    # remove first value since its 0
    df.drop(index=df.index[0],
            axis=0,
            inplace=True)

    # get dates and y range
    dates = [datetime.fromtimestamp(time / 1000) for time in df[0]]
    min_value = int(df[1].min() - 10)
    max_value = int(df[1].max() + 10)

    # create figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=df[1], fill='tozeroy'))  # fill down to xaxis
    fig.update_yaxes(range=[min_value, max_value])
    fig.write_html("data/backtesting-data/plots/equity/equityplot.html", auto_open=False)
