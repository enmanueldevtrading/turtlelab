"""Valida datos locales e informe de calidad."""
import json
import sys
sys.path.insert(0, ".")
from bt.data_manager import inventory, load_bars
from bt.validator import validate


def main():
    inv = inventory()
    print(f"Pares/TF locales: {len(inv)}")
    out = []
    for item in inv:
        try:
            df = load_bars(item["symbol"], item["timeframe"])
            rep = validate(df, item["timeframe"])
        except Exception as e:
            rep = {"ok": False, "errors": [str(e)[:150]]}
        row = {**item, **rep}
        out.append(row)
        print(f"{item['symbol']} {item['timeframe']}: rows={item.get('rows')} ok={rep.get('ok')} gaps={rep.get('gaps')}")
    with open("results/validation_report.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    print("Reporte: results/validation_report.json")


if __name__ == "__main__":
    main()
