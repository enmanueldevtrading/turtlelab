"""Tortugas (Donchian breakout) — una clase, tres presets en el panel."""
import numpy as np

from ..sdk import BaseStrategy, add_preset, atr, donchian, strategy

TF_ALL = ["M1", "M3", "M5", "M15", "M30", "H1", "H4", "D1"]
RIESGO = "Riesgo 1% del capital corriente"


def _reglas(entrada, salida):
    return [
        f"Compra si el cierre rompe el máximo de las {entrada} velas anteriores",
        f"Vende si el cierre rompe el mínimo de las {entrada} velas anteriores",
        "Tope fijo a 2×ATR desde la entrada (no se mueve)",
        f"Cierra el largo si el cierre cae bajo el mínimo de {salida} (y al revés)",
        "Una posición a la vez, sin pirámide. Riesgo 1% del capital corriente",
    ]


@strategy(
    id="turtle20_10",
    label="Tortuga Sistema 1 (20/10)",
    desc="Entrada ruptura canal 20, salida canal 10. Una entrada, tope fijo 2×ATR.",
    rules=_reglas(20, 10),
    tfs=TF_ALL, balance=50.0, riesgo=RIESGO, order=10,
    params={"entry": 20, "exit": 10},
)
class Turtle(BaseStrategy):
    """Turtle System 1/2 simplificado: 1 unidad, SL fijo 2N, salida por canal."""
    name = "turtle"
    defaults = {"entry": 20, "exit": 10, "atr_period": 20, "sl_mult": 2.0}

    def prepare(self, df, p):
        # shift=1: el canal llega hasta la vela anterior (no espera una vela de mas).
        he, le = donchian(df, p["entry"], shift=1)
        hx, lx = donchian(df, p["exit"], shift=1)
        return {"close": df["close"].to_numpy(float),
                "he": he, "le": le, "hx": hx, "lx": lx,
                "atr": atr(df, p["atr_period"])}

    def entry_signal(self, df, i, ctx, p):
        c = ctx["close"][i]
        if np.isnan([ctx["he"][i], ctx["le"][i]]).any():
            return 0
        if c > ctx["he"][i]:
            return 1
        if c < ctx["le"][i]:
            return -1
        return 0

    def exit_signal(self, df, i, ctx, p, direction):
        c = ctx["close"][i]
        if direction == 1 and not np.isnan(ctx["lx"][i]):
            return bool(c < ctx["lx"][i])
        if direction == -1 and not np.isnan(ctx["hx"][i]):
            return bool(c > ctx["hx"][i])
        return False

    def stop_price(self, df, i, ctx, p, direction, entry_price):
        a = ctx["atr"][i]
        if np.isnan(a) or a <= 0:
            return None, None
        if direction == 1:
            return entry_price - p["sl_mult"] * a, None
        return entry_price + p["sl_mult"] * a, None


# Mismo motor, otra salida: se publica como preset, sin duplicar codigo.
add_preset(Turtle, "turtle20_20", params={"entry": 20, "exit": 20},
           label="Tortuga Sistema 1 salida 20 (20/20)",
           desc="Entrada ruptura canal 20, salida canal 20. Tope fijo 2×ATR.",
           rules=_reglas(20, 20), tfs=TF_ALL, balance=50.0, riesgo=RIESGO, order=20)

add_preset(Turtle, "turtle55_20", params={"entry": 55, "exit": 20},
           label="Tortuga Sistema 2 (55/20)",
           desc="Entrada ruptura canal 55, salida canal 20. Tope fijo 2×ATR.",
           rules=_reglas(55, 20), tfs=TF_ALL, balance=50.0, riesgo=RIESGO, order=30)
