"""Simulador de ejecucion realista, event-driven por barra, sin look-ahead."""
from dataclasses import dataclass


@dataclass
class ExecConfig:
    initial_balance: float = 50.0
    lot: float = 0.0            # 0 = riesgo %
    risk_pct: float = 1.0
    min_lot: float = 0.01
    max_lot: float = 100.0
    lot_step: float = 0.01
    contract_size: float = 1.0  # unidades por lote (1.0 = PnL por punto de precio)
    spread: float = 0.0         # en precio
    commission: float = 0.0     # por operacion (moneda cuenta)
    slippage: float = 0.0       # en precio, en contra
    max_positions: int = 1
    allow_long: bool = True
    allow_short: bool = True
    entry_mode: str = "close"   # close | next_open
    trailing_mult: float = 0.0  # xATR, 0 = off
    breakeven_mult: float = 0.0 # xATR, 0 = off
    spike_k: float = 0.0        # filtro de picos en x ATR%; 0 = APAGADO (defecto aprobado)
    spike_cooldown: int = 3     # velas bloqueadas tras un pico (solo si k>0)
    spike_close: bool = False   # cerrar la posicion abierta cuando hay pico (solo si k>0)


def quantize(lot, step, min_lot, max_lot):
    """Ajusta el lote al paso del broker (p.ej. 0.01) y a sus limites."""
    if step and step > 0:
        lot = round(lot / step) * step
    return max(min_lot, min(lot, max_lot))


def position_size(balance, risk_pct, lot, sl_dist, min_lot, max_lot, step=0.01,
                  contract_size=1.0):
    if lot and lot > 0:
        return quantize(lot, step, min_lot, max_lot)
    if not sl_dist or sl_dist <= 0:
        return min_lot
    risk_money = balance * risk_pct / 100.0
    cs = contract_size or 1.0
    lots = risk_money / (sl_dist * cs)
    # Si el 1% no llega ni al lote minimo, manda el lote minimo: el stop limita.
    return quantize(lots, step, min_lot, max_lot)


class Portfolio:
    def __init__(self, cfg: ExecConfig):
        self.cfg = cfg
        self.balance = cfg.initial_balance
        self.positions: list = []
        self.trades: list = []
        self.equity_curve: list = []

    def open(self, direction, ts_sig, px_sig, ts_in, px_in, sl, tp, qty, reason,
             atr=None, entry_idx=None):
        if len(self.positions) >= self.cfg.max_positions:
            return None
        # spread + slippage en contra (la mitad del spread por lado)
        fill = px_in + (self.cfg.spread / 2 + self.cfg.slippage) * direction
        sl_dist = abs(fill - sl) if sl else 0.0
        risk_money = sl_dist * qty * self.cfg.contract_size if sl else 0.0
        risk_pct_real = risk_money / self.balance * 100 if self.balance else 0.0
        pos = {"direction": direction, "ts_signal": ts_sig, "px_signal": px_sig,
               "ts_entry": ts_in, "entry": fill, "sl": sl, "tp": tp, "qty": qty,
               "reason": reason, "atr": atr, "be_done": False,
               "entry_idx": entry_idx, "sl_dist": sl_dist,
               "risk_money": risk_money, "risk_pct_real": risk_pct_real,
               "spread_cfg": self.cfg.spread, "commission_cfg": self.cfg.commission,
               "slippage_cfg": self.cfg.slippage,
               "contract_size": self.cfg.contract_size,
               "mfe_price": 0.0, "mae_price": 0.0}
        self.positions.append(pos)
        self.balance -= self.cfg.commission  # comision por lado (apertura)
        return pos

    def _pnl(self, pos, exit_price):
        d = pos["direction"]
        gross = (exit_price - pos["entry"]) * d * pos["qty"] * self.cfg.contract_size
        return gross - self.cfg.commission

    def track_bar(self, pos, bar):
        """Maxima excursion a favor/en contra con el OHLC de la barra abierta."""
        d = pos["direction"]
        if d == 1:
            pos["mfe_price"] = max(pos["mfe_price"], bar["high"] - pos["entry"])
            pos["mae_price"] = min(pos["mae_price"], bar["low"] - pos["entry"])
        else:
            pos["mfe_price"] = max(pos["mfe_price"], pos["entry"] - bar["low"])
            pos["mae_price"] = min(pos["mae_price"], pos["entry"] - bar["high"])

    def close(self, pos, ts_out, px_out, reason, exit_idx=None):
        import pandas as pd
        fill = px_out - (self.cfg.spread / 2 + self.cfg.slippage) * pos["direction"]
        pnl = self._pnl(pos, fill)
        try:
            dur_seg = (pd.to_datetime(ts_out) - pd.to_datetime(pos["ts_entry"])).total_seconds()
        except Exception:
            dur_seg = None
        self.balance += pnl  # _pnl ya descuenta la comision del cierre
        self.positions.remove(pos)
        risk_money = pos.get("risk_money", 0.0) or 0.0
        entry_idx = pos.get("entry_idx")
        self.trades.append({
            "direction": "LARGO" if pos["direction"] == 1 else "CORTO",
            "ts_signal": pos["ts_signal"], "px_signal": pos["px_signal"],
            "ts_entry": pos["ts_entry"], "entry": pos["entry"],
            "sl": pos["sl"], "tp": pos["tp"], "qty": pos["qty"],
            "atr_entry": pos.get("atr"), "sl_dist": pos.get("sl_dist", 0.0),
            "risk_money": round(risk_money, 4),
            "risk_pct_real": round(pos.get("risk_pct_real", 0.0), 4),
            "spread_cfg": pos.get("spread_cfg", 0.0),
            "commission_total": round(2 * self.cfg.commission, 4),
            "slippage_cfg": pos.get("slippage_cfg", 0.0),
            "contract_size": pos.get("contract_size", 1.0),
            "bars_held": (exit_idx - entry_idx) if exit_idx is not None and entry_idx is not None else None,
            "duracion_seg": dur_seg,
            "mfe_price": round(pos.get("mfe_price", 0.0), 5),
            "mae_price": round(pos.get("mae_price", 0.0), 5),
            "mfe_money": round(pos.get("mfe_price", 0.0) * pos["qty"] * self.cfg.contract_size, 2),
            "mae_money": round(pos.get("mae_price", 0.0) * pos["qty"] * self.cfg.contract_size, 2),
            "r_multiple": round(pnl / risk_money, 3) if risk_money else None,
            "ts_exit": ts_out, "exit": fill, "reason": reason,
            "pnl": pnl, "balance": self.balance,
        })
        return pnl

    def manage_bar(self, pos, bar, atr_now):
        """Aplica SL/TP/trailing/breakeven con OHLC de la barra actual. Retorna (salir, precio, motivo)."""
        d = pos["direction"]
        sl, tp = pos["sl"], pos["tp"]
        # trailing / breakeven (solo con ATR conocido)
        if atr_now and atr_now > 0:
            cfg = self.cfg
            if cfg.breakeven_mult and not pos["be_done"]:
                trig = pos["entry"] + d * cfg.breakeven_mult * atr_now
                if (d == 1 and bar["high"] >= trig) or (d == -1 and bar["low"] <= trig):
                    pos["sl"] = pos["entry"]
                    pos["be_done"] = True
                    sl = pos["sl"]
            if cfg.trailing_mult:
                if d == 1:
                    nsl = bar["close"] - cfg.trailing_mult * atr_now
                    if nsl > (sl or -1e18):
                        pos["sl"] = nsl
                        sl = nsl
                else:
                    nsl = bar["close"] + cfg.trailing_mult * atr_now
                    if sl is None or nsl < sl:
                        pos["sl"] = nsl
                        sl = nsl
        # SL primero (conservador), luego TP
        if sl is not None:
            if d == 1 and bar["low"] <= sl:
                return True, sl, "TOPE"
            if d == -1 and bar["high"] >= sl:
                return True, sl, "TOPE"
        if tp is not None:
            if d == 1 and bar["high"] >= tp:
                return True, tp, "OBJETIVO"
            if d == -1 and bar["low"] <= tp:
                return True, tp, "OBJETIVO"
        return False, None, ""
