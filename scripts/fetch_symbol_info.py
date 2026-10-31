"""Lee SYMBOL_INFO real de MT5 y la guarda por simbolo. Solo aqui se usa MT5."""
import json
import os
import sys
sys.path.insert(0, ".")
from bt.downloader import connect, available_symbols, MT5_PATH_DEFAULT

FIELDS = ["spread", "trade_tick_value", "trade_tick_size", "volume_min",
          "volume_max", "volume_step", "trade_contract_size", "digits",
          "point", "trade_mode"]


def main():
    mt5 = connect(MT5_PATH_DEFAULT)
    syms = available_symbols(mt5)
    print(f"Simbolos: {len(syms)}")
    n = 0
    for s in syms:
        try:
            mt5.symbol_select(s, True)
            info = mt5.symbol_info(s)
            if info is None:
                print(f"  {s}: sin info")
                continue
            d = {f: getattr(info, f, None) for f in FIELDS}
            d["point_price"] = d["spread"] * d["point"] if d["spread"] and d["point"] else 0.0
            safe = "".join(c if (c.isalnum() or c in ("-", "_", " ")) else "_" for c in s).strip()
            path = os.path.join("data", "weltrade", safe, "info.json")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            json.dump(d, open(path, "w", encoding="utf-8"), indent=2)
            n += 1
        except Exception as e:
            print(f"  {s} ERROR: {str(e)[:100]}")
    mt5.shutdown()
    print(f"Guardados: {n}/{len(syms)} en data/weltrade/<SIMBOLO>/info.json")


if __name__ == "__main__":
    main()
