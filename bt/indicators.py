"""Indicadores deterministas sobre closes de velas CERRADAS."""
import numpy as np
import pandas as pd


def ema(values, period: int):
    """EMA con semilla SMA (igual que bot/indicators.py). Devuelve array con NaN al inicio."""
    v = np.asarray(values, dtype=float)
    out = np.full(len(v), np.nan)
    if len(v) < period or period < 1:
        return out
    sma = v[:period].mean()
    out[period - 1] = sma
    k = 2.0 / (period + 1)
    prev = sma
    for i in range(period, len(v)):
        prev = v[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def sma(values, period: int):
    return pd.Series(values, dtype=float).rolling(period).mean().to_numpy()


def atr(df: pd.DataFrame, period: int = 20):
    h = df["high"].to_numpy(float); l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    pc = np.roll(c, 1); pc[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    out = np.full(len(df), np.nan)
    if len(df) >= period:
        out[period - 1] = tr[:period].mean()
        for i in range(period, len(df)):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period  # Wilder
    return out


def rsi(closes, period: int = 14):
    c = np.asarray(closes, dtype=float)
    out = np.full(len(c), np.nan)
    if len(c) <= period:
        return out
    d = np.diff(c)
    g = np.where(d > 0, d, 0.0); lo = np.where(d < 0, -d, 0.0)
    ag = g[:period].mean(); al = lo[:period].mean()
    out[period] = 100 - 100 / (1 + ag / al) if al else 100.0
    for i in range(period + 1, len(c)):
        ag = (ag * (period - 1) + g[i - 1]) / period
        al = (al * (period - 1) + lo[i - 1]) / period
        out[i] = 100 - 100 / (1 + ag / al) if al else 100.0
    return out


def donchian(df: pd.DataFrame, period: int, shift: int = 2):
    """Canal Donchian. shift=1 excluye solo la vela evaluada (usa
    [i-period, i-1]); shift=2 excluye tambien la anterior."""
    import pandas as pd
    h = pd.Series(df["high"].to_numpy(float))
    l = pd.Series(df["low"].to_numpy(float))
    hi = h.shift(shift).rolling(period, min_periods=period).max().to_numpy()
    lo = l.shift(shift).rolling(period, min_periods=period).min().to_numpy()
    return hi, lo
