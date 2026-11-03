"""Filtro de picos (spikes) para indices sinteticos como PainX / GainX / SFX Vol.

Una vela es SPIKE cuando su movimiento supera K veces el ATR porcentual de la
propia serie. Escala con la volatilidad: no es un umbral de precio fijo.

Motivo (medido sobre 41 pares x 4 temporalidades, 50.000 velas cada uno):
las señales de la familia Tortuga que caen sobre una vela spike dan
R medio 0.177 frente a 0.370 en velas normales, y 0.187 frente a 0.532
en turtle55_20. El pico no es la senal: es ruido que la genera.

Reglas que aplica el motor (ver backtest.py y bot/main.py):
  1. Si la vela cerrada es spike, se CIERRA cualquier posicion abierta.
  2. Si la vela esta en cooldown (spike o las N siguientes), NO se abre nada.
K = 0 desactiva el filtro por completo.
"""
import numpy as np

SPIKE_K = 5.0          # umbral en multiplos de ATR%
SPIKE_COOLDOWN = 3     # velas bloqueadas despues de un spike
SPIKE_ATR_PERIOD = 20


def _atr_pct(high, low, close, period: int) -> np.ndarray:
    """ATR de Wilder en % del precio. NaN durante el calentamiento."""
    h = np.asarray(high, dtype=float)
    l = np.asarray(low, dtype=float)
    c = np.asarray(close, dtype=float)
    n = len(c)
    out = np.full(n, np.nan)
    if n < period or period < 1:
        return out
    pc = np.empty(n)
    pc[0] = c[0]
    pc[1:] = c[:-1]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    prev = tr[:period].mean()
    out[period - 1] = prev
    for i in range(period, n):
        prev = (prev * (period - 1) + tr[i]) / period
        out[i] = prev
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(c > 0, out / c * 100.0, np.nan)
    return out


def detect(high, low, close, k: float = SPIKE_K, period: int = SPIKE_ATR_PERIOD,
           cooldown: int = SPIKE_COOLDOWN) -> np.ndarray:
    """Devuelve dos booleanos por vela: (es_spike, bloqueada_para_entrar)."""
    c = np.asarray(close, dtype=float)
    n = len(c)
    if not k or k <= 0:
        z = np.zeros(n, dtype=bool)
        return z, z.copy()
    a = _atr_pct(high, low, c, period)
    ret = np.zeros(n, dtype=float)
    if n > 1:
        prev = c[:-1]
        with np.errstate(divide="ignore", invalid="ignore"):
            ret[1:] = np.where(prev > 0, (c[1:] - prev) / prev * 100.0, 0.0)
    spike = np.isfinite(a) & (np.abs(ret) > k * a)
    blocked = np.zeros(n, dtype=bool)
    cd = max(0, int(cooldown))
    if cd:
        # una vela bloqueada sigue bloqueada `cd` velas mas
        acc = np.zeros(n, dtype=bool)
        for j in range(cd + 1):
            shifted = np.zeros(n, dtype=bool)
            if j:
                shifted[j:] = spike[:-j]
            acc |= shifted
        blocked = acc
    else:
        blocked = spike.copy()
    return spike, blocked


class SpikeGuard:
    """Deteccion incremental de picos para el motor en vivo.

    Se alimenta vela a vela con velas YA CERRADAS y responde sobre el indice
    de la ultima vela recibida. Sin look-ahead: en i solo conoce 0..i.
    """

    def __init__(self, k: float = SPIKE_K, period: int = SPIKE_ATR_PERIOD,
                 cooldown: int = SPIKE_COOLDOWN):
        self.k = float(k or 0.0)
        self.period = int(period)
        self.cooldown = max(0, int(cooldown))
        self._tr: list[float] = []
        self._blocked_until = -1
        self._index = -1
        self._last_close = 0.0

    @property
    def enabled(self) -> bool:
        return self.k > 0

    def push(self, high: float, low: float, close: float):
        """Registra una vela cerrada. Devuelve (es_spike, bloqueada)."""
        if not self.enabled:
            return False, False
        self._index += 1
        h, l, c = float(high), float(low), float(close)
        pc = self._last_close
        self._last_close = c
        if self._index == 0:
            self._tr.append(max(0.0, h - l))
            return False, False
        tr = max(h - l, abs(h - pc), abs(l - pc))
        self._tr.append(tr)
        if len(self._tr) < self.period:
            return False, False
        a = sum(self._tr[:self.period]) / self.period
        for x in self._tr[self.period:]:
            a = (a * (self.period - 1) + x) / self.period
        if c <= 0 or a <= 0:
            return False, self._index <= self._blocked_until
        ret = (c - pc) / pc * 100.0
        spike = abs(ret) > self.k * a
        if spike:
            self._blocked_until = self._index + self.cooldown
        return bool(spike), self._index <= self._blocked_until
