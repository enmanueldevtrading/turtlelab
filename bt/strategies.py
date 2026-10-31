"""Estrategias 100% mecanicas. Solo ven barras 0..i (cerradas). Sin IA, sin futuro."""
import numpy as np
from .indicators import ema, donchian, atr


def _eps(x) -> float:
    return 1e-9 * max(1.0, abs(float(x)))


def _cross_up(fast, slow, i) -> bool:
    if i < 1 or np.isnan([fast[i-1], slow[i-1], fast[i], slow[i]]).any():
        return False
    return bool(fast[i-1] <= slow[i-1] + _eps(slow[i-1]) and fast[i] > slow[i] + _eps(slow[i]))


def _cross_down(fast, slow, i) -> bool:
    if i < 1 or np.isnan([fast[i-1], slow[i-1], fast[i], slow[i]]).any():
        return False
    return bool(fast[i-1] >= slow[i-1] - _eps(slow[i-1]) and fast[i] < slow[i] - _eps(slow[i]))


class BaseStrategy:
    name = "base"
    defaults: dict = {}

    def prepare(self, df, params: dict):
        return {}

    def entry_signal(self, df, i: int, ctx: dict, params: dict) -> int:
        return 0

    def exit_reason(self, df, i, ctx, params: dict, direction: int) -> str:
        return "SALIDA POR SEÑAL"

    def exit_signal(self, df, i: int, ctx: dict, params: dict, direction: int) -> bool:
        return False

    def stop_price(self, df, i: int, ctx: dict, params: dict, direction: int, entry_price: float):
        return None, None  # sl, tp


class EmaCross(BaseStrategy):
    """Cruce EMA fast/slow confirmado al cierre. Sin tope ni objetivo: reversa en cruce contrario."""
    name = "ema_cross"
    defaults = {"fast": 72, "slow": 150}

    def prepare(self, df, p):
        c = df["close"].to_numpy(float)
        return {"close": c, "f": ema(c, p["fast"]), "s": ema(c, p["slow"])}

    def entry_signal(self, df, i, ctx, p):
        if _cross_up(ctx["f"], ctx["s"], i):
            return 1
        if _cross_down(ctx["f"], ctx["s"], i):
            return -1
        return 0

    def exit_signal(self, df, i, ctx, p, direction):
        if direction == 1:
            return _cross_down(ctx["f"], ctx["s"], i)
        if direction == -1:
            return _cross_up(ctx["f"], ctx["s"], i)
        return False


class Ema30_72_150(BaseStrategy):
    """Entrada por cruce EMA30/150, salida por cruce EMA30/72. Sin tope ni objetivo."""
    name = "ema30_72_150"
    defaults = {"entry_fast": 30, "mid": 72, "slow": 150}

    def prepare(self, df, p):
        c = df["close"].to_numpy(float)
        return {"close": c, "e": ema(c, p["entry_fast"]), "m": ema(c, p["mid"]), "s": ema(c, p["slow"])}

    def entry_signal(self, df, i, ctx, p):
        if _cross_up(ctx["e"], ctx["s"], i):
            return 1
        if _cross_down(ctx["e"], ctx["s"], i):
            return -1
        return 0

    def exit_signal(self, df, i, ctx, p, direction):
        if direction == 1:
            return _cross_down(ctx["e"], ctx["m"], i)
        if direction == -1:
            return _cross_up(ctx["e"], ctx["m"], i)
        return False


class Turtle(BaseStrategy):
    """Turtle System 1/2 simplificado: 1 unidad, SL fijo 2N, salida por canal. Sin piramide por defecto."""
    name = "turtle"
    defaults = {"entry": 20, "exit": 10, "atr_period": 20, "sl_mult": 2.0}

    def prepare(self, df, p):
        # shift=1: el canal llega hasta la vela anterior (no espera una vela de mas).
        he, le = donchian(df, p["entry"], shift=1)
        hx, lx = donchian(df, p["exit"], shift=1)
        return {"close": df["close"].to_numpy(float),
                "he": he, "le": le, "hx": hx, "lx": lx, "atr": atr(df, p["atr_period"])}

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


class VwapSession(BaseStrategy):
    """Rompimiento de VWAP anclado a apertura de sesion (Londres/NY) + rango
    de la primera vela M15. Ejecucion en M3. Salida al cerrar dentro de la EMA.
    Sin tope ni objetivo. Solo opera dentro de las ventanas de sesion (UTC)."""
    name = "vwap_session"
    # Sesiones en hora LOCAL de cada bolsa (con horario de verano bien calculado).
    # Formato nuevo: [zona, desde, hasta]. Formato viejo ["07:00","10:00"] = UTC.
    defaults = {"ema": 9, "sessions": [["Europe/London", "08:00", "11:00"],
                                       ["America/New_York", "08:00", "11:00"]]}

    @staticmethod
    def _mins(t: str) -> int:
        h, m = t.split(":")
        return int(h) * 60 + int(m)

    def prepare(self, df, p):
        import pandas as pd
        from zoneinfo import ZoneInfo
        ts = pd.to_datetime(df["timestamp"], utc=True)
        mins_utc = (ts.dt.hour * 60 + ts.dt.minute).to_numpy()
        dates_utc = ts.dt.strftime("%Y-%m-%d").to_numpy()
        sess = np.full(len(df), None, dtype=object)
        for k, w in enumerate(p["sessions"]):
            if len(w) == 3:
                zone, sa, sb = w
                lt = ts.dt.tz_convert(ZoneInfo(zone))
                mins = (lt.dt.hour * 60 + lt.dt.minute).to_numpy()
                dates = lt.dt.strftime("%Y-%m-%d").to_numpy()
            else:
                sa, sb = w
                mins, dates = mins_utc, dates_utc
            a, b = self._mins(sa), self._mins(sb)
            m = (mins >= a) & (mins < b)
            sess[m] = dates[m] + f"_{k}"
        bucket = mins_utc // 15
        h = df["high"].to_numpy(float)
        l = df["low"].to_numpy(float)
        c = df["close"].to_numpy(float)
        tp = (h + l + c) / 3.0
        vol = df["tick_volume"].to_numpy(float) if "tick_volume" in df.columns else np.ones(len(df))
        vol = np.where(vol > 0, vol, 1.0)
        vwap = np.full(len(df), np.nan)
        ref_h = np.full(len(df), np.nan)
        ref_l = np.full(len(df), np.nan)
        trade_ok = np.zeros(len(df), dtype=bool)
        # Rango de referencia: primeras N velas de la sesion (ref_bars>0) o
        # primera vela M15 = primer bucket de 15 min (ref_bars=0).
        # Esas barras NO operan: su rango aun no esta cerrado.
        # (Los buckets de 15 min son iguales en UTC y en hora local: desfases enteros.)
        bucket = mins_utc // 15
        nbr = int(p.get("ref_bars", 0) or 0)
        for key, idx in pd.Series(range(len(df))).groupby(sess):
            ii = idx.to_numpy()
            cum_pv = np.cumsum(tp[ii] * vol[ii])
            cum_v = np.cumsum(vol[ii])
            vwap[ii] = cum_pv / cum_v
            if nbr > 0:
                first = ii[:nbr]
                trade_ok[ii[nbr:]] = True
            else:
                b0 = bucket[ii[0]]
                first = ii[bucket[ii] == b0]
                trade_ok[ii[bucket[ii] != b0]] = True
            ref_h[ii] = h[first].max()
            ref_l[ii] = l[first].min()
        return {"close": c, "vwap": vwap, "ref_h": ref_h, "ref_l": ref_l,
                "trade_ok": trade_ok, "e": ema(c, int(p["ema"]))}

    def _in(self, ctx, i) -> bool:
        return not np.isnan(ctx["vwap"][i])

    def entry_signal(self, df, i, ctx, p):
        # Disparador: cruce VWAP/EMA al cierre. EMA con cierres, VWAP con
        # OHLC. Solo en sesion. Sin rango M15.
        if i < 1 or not self._in(ctx, i) or not self._in(ctx, i - 1):
            return 0
        if _cross_up(ctx["vwap"], ctx["e"], i):
            return 1
        if _cross_down(ctx["vwap"], ctx["e"], i):
            return -1
        return 0

    def exit_signal(self, df, i, ctx, p, direction):
        # Todo solo en sesion: al salir del horario se aplana todo, sin
        # aguantar dias. Fuera de sesion no hay entradas ni salidas con
        # senal: solo el cierre de fin de sesion.
        if i < 1:
            return False
        if not self._in(ctx, i):
            return True  # fin de sesion: aplanar
        c = ctx["close"]
        e = ctx["e"]
        if np.isnan(e[i]) or np.isnan(e[i - 1]):
            return False
        # cierra cuando la vela vuelve a cerrar dentro de la EMA 9
        if direction == 1:
            return bool(c[i - 1] >= e[i - 1] and c[i] < e[i])
        if direction == -1:
            return bool(c[i - 1] <= e[i - 1] and c[i] > e[i])
        return False

    def exit_reason(self, df, i, ctx, p, direction) -> str:
        if not self._in(ctx, i):
            return "FIN DE SESION"
        return "SALIDA POR SEÑAL"


class VwapM15(VwapSession):
    """Variante A: ruptura del rango de las 2 primeras velas M15, en M15."""
    name = "vwap_m15"
    defaults = {"ema": 9, "ref_bars": 2,
                "sessions": [["Europe/London", "08:00", "11:00"],
                             ["America/New_York", "08:00", "11:00"]]}

    def entry_signal(self, df, i, ctx, p):
        if i < 1 or not self._in(ctx, i) or not ctx["trade_ok"][i]:
            return 0
        if np.isnan([ctx["ref_h"][i], ctx["ref_l"][i]]).any():
            return 0
        close = ctx["close"][i]
        if close > ctx["ref_h"][i]:
            return 1
        if close < ctx["ref_l"][i]:
            return -1
        return 0


class VwapRR(VwapSession):
    """Variante B: misma entrada M3, tope en la apertura de la vela senal
    y objetivo de 2R. Mantiene el aplanado de fin de sesion."""
    name = "vwap_rr12"
    defaults = {"ema": 9, "need_sl": True,
                "sessions": [["Europe/London", "08:00", "11:00"],
                             ["America/New_York", "08:00", "11:00"]]}

    def stop_price(self, df, i, ctx, p, direction, entry_price):
        op = float(df["open"].to_numpy(float)[i])
        if direction == 1:
            if op >= entry_price:
                return None, None  # sin recorrido: no se abre
            return op, entry_price + 2.0 * (entry_price - op)
        else:
            if op <= entry_price:
                return None, None
            return op, entry_price - 2.0 * (op - entry_price)

    def exit_signal(self, df, i, ctx, p, direction):
        # Solo el aplanado de fin de sesion; el objetivo lo cierra el motor.
        if i < 1:
            return False
        return not self._in(ctx, i)


STRATEGIES = {
    "ema_cross": EmaCross,
    "ema72_150": EmaCross,      # alias: defaults fast=72 slow=150
    "ema30_72_150": Ema30_72_150,
    "ema30_75_150": Ema30_72_150,  # alias: mid=75 via ALIASES
    "turtle": Turtle,
    "turtle20_10": Turtle,      # alias con defaults
    "turtle20_20": Turtle,
    "turtle55_20": Turtle,
    "vwap_session": VwapSession,
    "vwap_m15": VwapM15,
    "vwap_rr12": VwapRR,
}

ALIASES = {
    "ema72_150": {"fast": 72, "slow": 150},
    "ema30_75_150": {"entry_fast": 30, "mid": 75, "slow": 150},
    "turtle20_10": {"entry": 20, "exit": 10},
    "turtle20_20": {"entry": 20, "exit": 20},
    "turtle55_20": {"entry": 55, "exit": 20},
}

# Registro para el panel: anadir una estrategia = anadir una entrada aqui.
# El panel lee esto solo; no hay que tocar el panel ni el motor.
STRATEGY_META = {
    "turtle20_10": {
        "label": "Tortuga Sistema 1 (20/10)",
        "desc": "Entrada ruptura canal 20, salida canal 10. Una entrada, Tope fijo 2×ATR, salida por canal o tope.",
        "rules": ["Compra si el cierre rompe el máximo de las 20 velas anteriores",
                  "Vende si el cierre rompe el mínimo de las 20 velas anteriores",
                  "Tope fijo a 2×ATR desde la entrada (no se mueve)",
                  "Cierra la compra si el cierre cae bajo el mínimo de 10 (y al revés)",
                  "Una posición a la vez, sin pirámide. Riesgo 1% del capital corriente"],
        "variants": [("turtle20_10", {})],
        "balance": 50.0,
        "riesgo": "Riesgo 1% del capital corriente",
        "tfs": ["M1", "M3", "M5", "M15", "M30", "H1", "H4", "D1"],
    },
    "turtle20_20": {
        "label": "Tortuga Sistema 1 salida 20 (20/20)",
        "desc": "Entrada ruptura canal 20, salida canal 20. Una entrada, Tope fijo 2×ATR, salida por canal o tope.",
        "rules": ["Compra si el cierre rompe el máximo de las 20 velas anteriores",
                  "Vende si el cierre rompe el mínimo de las 20 velas anteriores",
                  "Tope fijo a 2×ATR desde la entrada (no se mueve)",
                  "Cierra la compra si el cierre cae bajo el mínimo de 20 (y al revés)",
                  "Una posición a la vez, sin pirámide. Riesgo 1% del capital corriente"],
        "variants": [("turtle20_20", {})],
        "balance": 50.0,
        "riesgo": "Riesgo 1% del capital corriente",
        "tfs": ["M1", "M3", "M5", "M15", "M30", "H1", "H4", "D1"],
    },
    "turtle55_20": {
        "label": "Tortuga Sistema 2 (55/20)",
        "desc": "Entrada ruptura canal 55, salida canal 20. Una entrada, Tope fijo 2×ATR, salida por canal o tope.",
        "rules": ["Compra si el cierre rompe el máximo de las 55 velas anteriores",
                  "Vende si el cierre rompe el mínimo de las 55 velas anteriores",
                  "Tope fijo a 2×ATR desde la entrada (no se mueve)",
                  "Cierra la compra si el cierre cae bajo el mínimo de 20 (y al revés)",
                  "Una posición a la vez, sin pirámide. Riesgo 1% del capital corriente"],
        "variants": [("turtle55_20", {})],
        "balance": 50.0,
        "riesgo": "Riesgo 1% del capital corriente",
        "tfs": ["M1", "M3", "M5", "M15", "M30", "H1", "H4", "D1"],
    },
    "ema72_150": {
        "label": "EMA 72/150",
        "desc": "Cruce EMA 72/150 confirmado al cierre. Sin tope ni objetivo: cierra solo en cruce contrario (reversa).",
        "rules": ["Compra si la EMA 72 cruza de abajo hacia arriba la EMA 150 al cierre",
                  "Vende si la cruza de arriba hacia abajo",
                  "Cierra solo con el cruce contrario. Sin stop ni objetivo"],
        "variants": [("ema_cross", {"fast": 72, "slow": 150})],
        "balance": 10.0,
        "riesgo": "Lote mínimo del par (sin tope)",
        "tfs": ["M1", "M3", "M5", "M15", "M30", "H1", "H4", "D1"],
    },
    "ema30_75_150": {
        "label": "EMA 30/75/150",
        "desc": "Entrada por cruce EMA 30/150 al cierre, salida cuando la 30 cruza la 75. Sin tope ni objetivo. Riesgo solo en Tortugas.",
        "rules": ["Compra si la EMA 30 cruza de abajo hacia arriba la EMA 150 al cierre",
                  "Vende si la cruza de arriba hacia abajo",
                  "Cierra la compra cuando la EMA 30 cruza hacia abajo la EMA 75 (y al revés)",
                  "Todo al cierre de vela. Sin stop ni objetivo"],
        "variants": [("ema30_75_150", {})],
        "balance": 10.0,
        "riesgo": "Lote mínimo del par (sin tope)",
        "tfs": ["M1", "M3", "M5", "M15", "M30", "H1", "H4", "D1"],
    },
    "vwap_rr12": {
        "label": "VWAP riesgo 1:2",
        "desc": "Variante B en M3: misma entrada VWAP. Tope en la apertura de la vela senal y objetivo al doble del riesgo. Aplanado de fin de sesion.",
        "rules": ["Misma entrada VWAP M3 y mismas sesiones",
                  "Tope en la apertura de la vela de la senal",
                  "Objetivo = 2 veces el riesgo. Sin esa distancia no se abre",
                  "Al terminar la sesion se cierra todo"],
        "variants": [("vwap_rr12", {})],
        "balance": 10.0,
        "riesgo": "Tope en apertura, objetivo 2R",
        "tfs": ["M3"],
    },
    "vwap": {
        "label": "VWAP sesiones NY/Londres",
        "desc": "VWAP anclado a apertura de Londres (08:00–11:00 hora Londres) y NY 08:00–11:00 (hora NY). Entrada por cruce VWAP/EMA 9 al cierre. Salida igual. Sin rango M15. Sin tope ni objetivo.",
        "rules": ["Solo opera en horario Londres 08:00–11:00 (hora Londres) y NY 08:00–11:00 (hora NY)",
                  "EMA con cierres, VWAP con precio tipico. Sin rango M15",
                  "Compra si el VWAP cruza arriba la EMA 9 al cierre",
                  "Vende si la cruza abajo",
                  "Cierra (solo en sesion) cuando el precio vuelve a cerrar dentro de la EMA 9. Sin tope ni objetivo",
                  "Al terminar la sesion se cierra todo: plano, sin aguantar dias"],
        "variants": [("vwap_session", {})],
        "balance": 50.0,
        "riesgo": "Lote mínimo del par (sin tope)",
        "tfs": ["M15", "M3"],
    },
}


def get_strategy(key: str):
    if key not in STRATEGIES:
        raise ValueError(f"Estrategia desconocida: {key}. Disponibles: {sorted(STRATEGIES)}")
    strat = STRATEGIES[key]()
    base = dict(strat.defaults)
    base.update(ALIASES.get(key, {}))
    return strat, base
