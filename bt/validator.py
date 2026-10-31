"""Validador de datos: orden, duplicados, OHLC, huecos."""
import pandas as pd
from .config import TF_SECONDS


def validate(df: pd.DataFrame, tf: str) -> dict:
    rep = {"rows": len(df), "errors": [], "warnings": []}
    if df.empty:
        rep["errors"].append("vacio")
        return rep
    ts = pd.to_datetime(df["timestamp"], utc=True)
    if not ts.is_monotonic_increasing:
        rep["errors"].append("desordenado")
    if ts.duplicated().any():
        rep["errors"].append(f"duplicados={int(ts.duplicated().sum())}")
    bad_ohlc = ((df["high"] < df[["open", "close"]].max(axis=1) - 1e-9) |
                (df["low"] > df[["open", "close"]].min(axis=1) + 1e-9)).sum()
    if int(bad_ohlc):
        rep["errors"].append(f"ohlc_invalido={int(bad_ohlc)}")
    step = TF_SECONDS.get(tf, 60)
    diffs = ts.diff().dt.total_seconds().dropna()
    gaps = diffs[diffs > step * 2]
    rep["gaps"] = int(len(gaps))
    rep["max_gap_bars"] = float((gaps.max() / step)) if len(gaps) else 0.0
    if len(gaps):
        rep["warnings"].append(f"huecos={len(gaps)} max={rep['max_gap_bars']:.1f}xTF")
    rep["from"] = str(ts.iloc[0])
    rep["to"] = str(ts.iloc[-1])
    rep["ok"] = not rep["errors"]
    return rep
