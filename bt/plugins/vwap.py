"""VWAP anclado a sesion (Londres / Nueva York)."""
import numpy as np

from ..sdk import (BaseStrategy, add_preset, cross_down, cross_up, ema,
                  register_class, strategy)

SESIONES = [["Europe/London", "08:00", "11:00"],
            ["America/New_York", "08:00", "11:00"]]


@strategy(
    label="VWAP sesiones NY/Londres",
    desc="VWAP anclado a apertura de Londres y NY. Entrada por cruce VWAP/EMA 9 al cierre. Sin tope ni objetivo.",
    rules=["Solo opera en horario Londres 08:00–11:00 (hora Londres) y NY 08:00–11:00 (hora NY)",
           "EMA con cierres, VWAP con precio tipico. Sin rango M15",
           "Compra si el VWAP cruza arriba la EMA 9 al cierre",
           "Vende si la cruza abajo",
           "Cierra (solo en sesion) cuando el precio vuelve a cerrar dentro de la EMA 9",
           "Al terminar la sesion se cierra todo: plano, sin aguantar dias"],
    tfs=["M15", "M3"], balance=50.0, riesgo="Lote mínimo del par (sin tope)", order=60,
    params={"ema": 9},
)
class VwapSession(BaseStrategy):
    """Ruptura de VWAP anclado a apertura de sesion. Salida dentro de la EMA."""
    name = "vwap_session"
    # Sesiones en hora LOCAL de cada bolsa (con horario de verano bien calculado).
    # Formato nuevo: [zona, desde, hasta]. Formato viejo ["07:00","10:00"] = UTC.
    defaults = {"ema": 9, "sessions": SESIONES}

    @staticmethod
    def _mins(t):
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
        h = df["high"].to_numpy(float)
        lo = df["low"].to_numpy(float)
        c = df["close"].to_numpy(float)
        tp = (h + lo + c) / 3.0
        vol = df["tick_volume"].to_numpy(float) if "tick_volume" in df.columns else np.ones(len(df))
        vol = np.where(vol > 0, vol, 1.0)
        vwap = np.full(len(df), np.nan)
        ref_h = np.full(len(df), np.nan)
        ref_l = np.full(len(df), np.nan)
        trade_ok = np.zeros(len(df), dtype=bool)
        # Rango de referencia: primeras N velas de la sesion (ref_bars>0) o
        # primera vela M15 = primer bucket de 15 min (ref_bars=0).
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
            ref_l[ii] = lo[first].min()
        return {"close": c, "vwap": vwap, "ref_h": ref_h, "ref_l": ref_l,
                "trade_ok": trade_ok, "e": ema(c, int(p["ema"]))}

    def _in(self, ctx, i) -> bool:
        return not np.isnan(ctx["vwap"][i])

    def entry_signal(self, df, i, ctx, p):
        # Disparador: cruce VWAP/EMA al cierre. Solo en sesion. Sin rango M15.
        if i < 1 or not self._in(ctx, i) or not self._in(ctx, i - 1):
            return 0
        if cross_up(ctx["vwap"], ctx["e"], i):
            return 1
        if cross_down(ctx["vwap"], ctx["e"], i):
            return -1
        return 0

    def exit_signal(self, df, i, ctx, p, direction):
        if i < 1:
            return False
        if not self._in(ctx, i):
            return True  # fin de sesion: aplanar
        c = ctx["close"]
        e = ctx["e"]
        if np.isnan(e[i]) or np.isnan(e[i - 1]):
            return False
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
    defaults = {"ema": 9, "ref_bars": 2, "sessions": SESIONES}

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


@strategy(
    label="VWAP riesgo 1:2",
    desc="Variante B en M3: misma entrada VWAP. Tope en la apertura de la vela senal y objetivo 2R.",
    rules=["Misma entrada VWAP M3 y mismas sesiones",
           "Tope en la apertura de la vela de la senal",
           "Objetivo = 2 veces el riesgo. Sin esa distancia no se abre",
           "Al terminar la sesion se cierra todo"],
    tfs=["M3"], balance=10.0, riesgo="Tope en apertura, objetivo 2R", order=70,
    params={"ema": 9, "need_sl": True},
)
class VwapRR(VwapSession):
    """Variante B: misma entrada M3, tope en la apertura de la vela senal y 2R."""
    name = "vwap_rr12"
    defaults = {"ema": 9, "need_sl": True, "sessions": SESIONES}

    def stop_price(self, df, i, ctx, p, direction, entry_price):
        op = float(df["open"].to_numpy(float)[i])
        if direction == 1:
            if op >= entry_price:
                return None, None  # sin recorrido: no se abre
            return op, entry_price + 2.0 * (entry_price - op)
        if op <= entry_price:
            return None, None
        return op, entry_price - 2.0 * (op - entry_price)

    def exit_signal(self, df, i, ctx, p, direction):
        # Solo el aplanado de fin de sesion; el objetivo lo cierra el motor.
        if i < 1:
            return False
        return not self._in(ctx, i)


# Compatibilidad: la clave corta "vwap" del panel antiguo.
add_preset(VwapSession, "vwap", params={"ema": 9}, hidden=True)
# El motor conoce la variante M15 aunque el panel no la publica por defecto.
register_class(VwapM15)
