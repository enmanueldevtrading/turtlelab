"""Estrategias de medias exponenciales."""
from ..sdk import BaseStrategy, add_preset, cross_down, cross_up, ema, strategy

TF_ALL = ["M1", "M3", "M5", "M15", "M30", "H1", "H4", "D1"]
SIN_TOPE = "Lote mínimo del par (sin tope)"


@strategy(
    label="EMA 72/150",
    desc="Cruce EMA 72/150 confirmado al cierre. Sin tope ni objetivo: cierra solo en cruce contrario.",
    rules=["Compra si la EMA 72 cruza de abajo hacia arriba la EMA 150 al cierre",
           "Vende si la cruza de arriba hacia abajo",
           "Cierra solo con el cruce contrario. Sin stop ni objetivo"],
    tfs=TF_ALL, balance=10.0, riesgo=SIN_TOPE, order=40,
    params={"fast": 72, "slow": 150},
)
class EmaCross(BaseStrategy):
    """Cruce EMA fast/slow confirmado al cierre. Reversa en cruce contrario."""
    name = "ema_cross"
    defaults = {"fast": 72, "slow": 150}

    def prepare(self, df, p):
        c = df["close"].to_numpy(float)
        return {"close": c, "f": ema(c, p["fast"]), "s": ema(c, p["slow"])}

    def entry_signal(self, df, i, ctx, p):
        if cross_up(ctx["f"], ctx["s"], i):
            return 1
        if cross_down(ctx["f"], ctx["s"], i):
            return -1
        return 0

    def exit_signal(self, df, i, ctx, p, direction):
        if direction == 1:
            return cross_down(ctx["f"], ctx["s"], i)
        if direction == -1:
            return cross_up(ctx["f"], ctx["s"], i)
        return False


@strategy(
    id="ema30_75_150",
    label="EMA 30/75/150",
    desc="Entrada por cruce EMA 30/150 al cierre, salida cuando la 30 cruza la 75. Sin tope ni objetivo.",
    rules=["Compra si la EMA 30 cruza de abajo hacia arriba la EMA 150 al cierre",
           "Vende si la cruza de arriba hacia abajo",
           "Cierra la compra cuando la EMA 30 cruza hacia abajo la EMA 75 (y al revés)",
           "Todo al cierre de vela. Sin stop ni objetivo"],
    tfs=TF_ALL, balance=10.0, riesgo=SIN_TOPE, order=50,
    params={"entry_fast": 30, "mid": 75, "slow": 150},
)
class Ema30_72_150(BaseStrategy):
    """Entrada por cruce EMA30/150, salida por cruce EMA30/mid."""
    name = "ema30_72_150"
    defaults = {"entry_fast": 30, "mid": 72, "slow": 150}

    def prepare(self, df, p):
        c = df["close"].to_numpy(float)
        return {"close": c, "e": ema(c, p["entry_fast"]),
                "m": ema(c, p["mid"]), "s": ema(c, p["slow"])}

    def entry_signal(self, df, i, ctx, p):
        if cross_up(ctx["e"], ctx["s"], i):
            return 1
        if cross_down(ctx["e"], ctx["s"], i):
            return -1
        return 0

    def exit_signal(self, df, i, ctx, p, direction):
        if direction == 1:
            return cross_down(ctx["e"], ctx["m"], i)
        if direction == -1:
            return cross_up(ctx["e"], ctx["m"], i)
        return False


# Clave clasica del motor, sin panel propio (compatibilidad).
add_preset(EmaCross, "ema72_150", params={"fast": 72, "slow": 150}, hidden=True)
