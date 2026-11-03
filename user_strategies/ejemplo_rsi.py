"""Ejemplo real de plugin de usuario: RSI contra tendencia de fondo.

Archivo de muestra: se carga solo y aparece en el panel como
"RSI 30/70 con filtro EMA 200". Copialo como plantilla para tus ideas.
"""
import numpy as np

from bt.sdk import BaseStrategy, atr, ema, rsi, strategy


@strategy(
    id="rsi_ema200",
    label="RSI 30/70 con filtro EMA 200 (ejemplo)",
    desc="Compra cuando el RSI sale de sobrevendido con el precio sobre la EMA 200. "
         "Vende al reves. Tope 2xATR.",
    rules=["Compra si el RSI 14 cruza hacia arriba el 30 y el cierre esta sobre la EMA 200",
           "Vende si el RSI 14 cruza hacia abajo el 70 y el cierre esta bajo la EMA 200",
           "Cierra el largo si el RSI supera 70 (y el corto si baja de 30)",
           "Tope fijo a 2xATR desde la entrada"],
    tfs=["M5", "M15", "M30", "H1", "H4"],
    balance=50.0,
    riesgo="Riesgo 1% del capital corriente",
    order=200,
    params={"rsi_period": 14, "low": 30, "high": 70, "trend": 200, "sl_mult": 2.0},
)
class RsiEma200(BaseStrategy):
    name = "rsi_ema200"
    defaults = {"rsi_period": 14, "low": 30, "high": 70, "trend": 200, "sl_mult": 2.0}

    def prepare(self, df, p):
        c = df["close"].to_numpy(float)
        return {"c": c,
                "r": rsi(c, int(p["rsi_period"])),
                "t": ema(c, int(p["trend"])),
                "atr": atr(df, 14)}

    def entry_signal(self, df, i, ctx, p):
        if i < 1:
            return 0
        r, t, c = ctx["r"], ctx["t"], ctx["c"]
        if np.isnan([r[i], r[i - 1], t[i]]).any():
            return 0
        low, high = float(p["low"]), float(p["high"])
        if r[i - 1] <= low < r[i] and c[i] > t[i]:
            return 1
        if r[i - 1] >= high > r[i] and c[i] < t[i]:
            return -1
        return 0

    def exit_signal(self, df, i, ctx, p, direction):
        r = ctx["r"][i]
        if np.isnan(r):
            return False
        if direction == 1:
            return bool(r > float(p["high"]))
        if direction == -1:
            return bool(r < float(p["low"]))
        return False

    def stop_price(self, df, i, ctx, p, direction, entry_price):
        a = ctx["atr"][i]
        if np.isnan(a) or a <= 0:
            return None, None
        if direction == 1:
            return entry_price - p["sl_mult"] * a, None
        return entry_price + p["sl_mult"] * a, None
