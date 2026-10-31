"""Walk-forward train/val/OOS por fechas (arquitectura lista)."""
import pandas as pd


def split(df: pd.DataFrame, train=0.6, val=0.2):
    n = len(df)
    i1, i2 = int(n * train), int(n * (train + val))
    return df.iloc[:i1].reset_index(drop=True), df.iloc[i1:i2].reset_index(drop=True), df.iloc[i2:].reset_index(drop=True)
