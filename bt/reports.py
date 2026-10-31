"""Reportes JSON/CSV/HTML ligero (SVG inline, sin Plotly)."""
import json
import os
import pandas as pd


def _svg_line(values, w=600, h=160):
    if not values:
        return "<p>Sin equity.</p>"
    mn, mx = min(values), max(values)
    rng = (mx - mn) or 1.0
    pts = []
    for i, v in enumerate(values):
        x = i / max(len(values) - 1, 1) * (w - 10) + 5
        y = h - 5 - (v - mn) / rng * (h - 10)
        pts.append(f"{x:.1f},{y:.1f}")
    return (f"<svg width='{w}' height='{h}' style='background:#0b1220;border-radius:8px'>"
            f"<polyline points='{' '.join(pts)}' fill='none' stroke='#22c55e' stroke-width='2'/></svg>")


ETIQUETAS = {
    "capital": "Capital inicial $", "balance": "Balance final $",
    "net_profit": "Beneficio neto $", "net_pct": "Beneficio neto %",
    "gross_profit": "Ganancia bruta $", "gross_loss": "Pérdida bruta $",
    "profit_factor": "Factor de beneficio", "max_drawdown": "Caída máxima $",
    "max_drawdown_pct": "Caída máxima %", "total": "Operaciones",
    "wins": "Ganadoras", "losses": "Perdedoras", "win_rate": "Aciertos %",
    "avg_win": "Ganancia media $", "avg_loss": "Pérdida media $",
    "expectancy": "Esperanza $ por operación", "sharpe": "Sharpe", "sortino": "Sortino",
    "recovery": "Recuperación", "longs": "Largas", "shorts": "Cortas",
    "best": "Mejor operación $", "worst": "Peor operación $",
    "max_win_streak": "Racha ganadora (ops)", "max_loss_streak": "Racha perdedora (ops)",
    "max_win_streak_amt": "Racha ganadora ($)", "max_loss_streak_amt": "Racha perdedora ($)",
}


def save_report(result: dict, outdir: str):
    os.makedirs(outdir, exist_ok=True)
    m = result["metrics"]
    eq = result.get("equity_curve", [])
    rows = "".join(f"<tr><td>{ETIQUETAS.get(k, k)}</td><td>{v}</td></tr>" for k, v in m.items())
    tr = result.get("trades", [])[:200]
    tr_rows = "".join(
        f"<tr><td>{t.get('direction')}</td><td>{t.get('ts_entry')}</td><td>{t.get('entry')}</td>"
        f"<td>{t.get('ts_exit')}</td><td>{t.get('exit')}</td><td>{t.get('pnl')}</td>"
        f"<td>{t.get('r_multiple')}</td><td>{t.get('reason')}</td></tr>"
        for t in tr)
    html = f"""<html lang='es'><head><meta charset='utf-8'><title>Informe {result['bt_id']}</title></head>
<body style='font-family:Arial;background:#020617;color:#e2e8f0;padding:20px'>
<h1>{result['bt_id']} — {result['config']['strategy']} {result['config']['symbol']} {result['config']['timeframe']}</h1>
<p>Capital: ${m.get('capital')} · Período: {result['config'].get('from')} → {result['config'].get('to')}</p>
<h2>Curva de capital</h2>{_svg_line(eq)}
<h2>Mediciones</h2><table border='1' cellpadding='6'>{rows}</table>
<h2>Operaciones (primeras 200)</h2><table border='1' cellpadding='4'>
<tr><th>Dirección</th><th>Hora entrada</th><th>Entrada</th><th>Hora salida</th><th>Salida</th><th>Neto $</th><th>R</th><th>Motivo</th></tr>{tr_rows}</table>
<p>Huella: {result['config_hash']} | Motor {result['config'].get('engine')}</p>
</body></html>"""
    with open(os.path.join(outdir, "report.html"), "w", encoding="utf-8") as f:
        f.write(html)
    return os.path.join(outdir, "report.html")
