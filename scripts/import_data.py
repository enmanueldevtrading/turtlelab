"""Busca datos sueltos en el proyecto y los fusiona en data/weltrade.

Uso:
    python scripts/import_data.py              # solo informa (no toca nada)
    python scripts/import_data.py --apply       # importa de verdad
    python scripts/import_data.py --apply --dirs SwitchX1800_Dataset
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="importar (por defecto solo informa)")
    ap.add_argument("--dirs", default="", help="carpetas extra separadas por comas")
    ap.add_argument("--root", default=ROOT)
    a = ap.parse_args()
    os.chdir(a.root)
    from bt.importer import import_all
    extra = [d.strip() for d in a.dirs.split(",") if d.strip()]
    from bt import importer
    items = importer.plan(a.root, extra_dirs=extra)
    if not items:
        print("No se encontraron archivos OHLC fuera de data/. Nada que importar.")
        return 0
    print(f"{'archivo':58s} {'símbolo':16s} {'TF':4s} {'filas':>8s} {'nuevas':>8s}  acción")
    for it in items:
        print(f"{it['path'][:58]:58s} {str(it['symbol'])[:16]:16s} {it['timeframe']:4s} "
              f"{it['rows']:8d} {it.get('new_rows', 0):8d}  {it.get('action')}")
    if not a.apply:
        print("\nSolo lectura. Ejecuta con --apply para fusionarlos en data/weltrade/.")
        return 0
    rep = import_all(a.root, dry_run=False)
    for r in rep["imported"]:
        print(f"  OK {r['symbol']} {r['timeframe']}: {r['before']} -> {r['after']} "
              f"(+{r['added']}) {r['csv']}")
    print(f"\n{len(rep['imported'])} archivos importados. El panel los verá al recargar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
