"""Paquete de datos: mueve las velas entre maquinas o desde GitHub Releases.

Git no debe cargar los .csv.gz (171 MB y regenerables). Este script empaqueta
la carpeta de datos en un .zip unico y la restaura en otra maquina.

Uso:
    python scripts/data_pack.py pack                 # crea datos_weltrade.zip
    python scripts/data_pack.py pack --src yahoo     # crea datos_yahoo.zip
    python scripts/data_pack.py info datos_weltrade.zip
    python scripts/data_pack.py unpack datos_weltrade.zip
"""
import argparse
import json
import os
import sys
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_ROOTS = {"weltrade": os.path.join(ROOT, "data", "weltrade"),
             "yahoo": os.path.join(ROOT, "data", "yahoo")}


def _walk(root):
    for sym in sorted(os.listdir(root)):
        d = os.path.join(root, sym)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith((".csv.gz", ".parquet", ".json")):
                yield sym, f, os.path.join(d, f)


def cmd_pack(a):
    root = SRC_ROOTS[a.src]
    if not os.path.isdir(root):
        print(f"ERROR: no existe {root}")
        return 1
    out = a.out or os.path.join(ROOT, f"datos_{a.src}.zip")
    items = list(_walk(root))
    if not items:
        print(f"ERROR: {root} está vacío. Descarga primero con download_data.py")
        return 1
    t0 = time.time()
    manifest = {"src": a.src, "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "files": 0, "symbols": []}
    syms = set()
    try:
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for i, (sym, f, path) in enumerate(items, 1):
                z.write(path, arcname=f"{a.src}/{sym}/{f}")
                syms.add(sym)
                manifest["files"] += 1
                if i % 50 == 0 or i == len(items):
                    print(f"\r  {i}/{len(items)} archivos…", end="", flush=True)
            manifest["symbols"] = sorted(syms)
            z.writestr(f"{a.src}/_manifest.json", json.dumps(manifest, indent=2))
    except OSError as exc:
        try:
            os.remove(out)
        except OSError:
            pass
        print(f"\nERROR escribiendo {out}: {exc}")
        print("Suele ser falta de espacio en disco. Prueba --out en otra unidad.")
        return 1
    print(f"\nOK: {out} ({os.path.getsize(out) / 1e6:.1f} MB comprimido, "
          f"{len(manifest['symbols'])} símbolos, {time.time() - t0:.1f}s)")
    print("Súbelo a GitHub Releases (no al repo) y restáuralo con 'unpack'.")
    return 0


def cmd_unpack(a):
    if not os.path.isfile(a.pack):
        print(f"ERROR: no existe {a.pack}")
        return 1
    with zipfile.ZipFile(a.pack) as z:
        names = z.namelist()
        srcs = {n.split("/")[0] for n in names if "/" in n}
        dest_default = os.path.join(ROOT, "data", a.src or sorted(srcs)[0])
        dest = a.dest or dest_default
        os.makedirs(dest, exist_ok=True)
        n = 0
        for info in z.infolist():
            if info.is_dir() or info.filename.endswith("_manifest.json"):
                continue
            parts = info.filename.split("/")
            if len(parts) < 3:
                continue
            rel = os.path.join(parts[1], parts[2])
            target = os.path.join(dest, rel)
            if os.path.abspath(target).find(os.path.abspath(dest)) != 0:
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(info) as fsrc, open(target, "wb") as fdst:
                fdst.write(fsrc.read())
            n += 1
    print(f"OK: {n} archivos restaurados en {dest}")
    cache = os.path.join(ROOT, "results", "inventory_cache.json")
    if os.path.exists(cache):
        os.remove(cache)
        print("Caché de inventario borrada: el panel verá los datos nuevos.")
    return 0


def cmd_info(a):
    if not os.path.isfile(a.pack):
        print(f"ERROR: no existe {a.pack}")
        return 1
    with zipfile.ZipFile(a.pack) as z:
        names = z.namelist()
        raw = 0
        try:
            raw = sum(i.file_size for i in z.infolist())
        except Exception:
            pass
        man = None
        for n in names:
            if n.endswith("_manifest.json"):
                try:
                    man = json.loads(z.read(n).decode())
                except Exception:
                    man = None
        print(f"{a.pack}: {len(names)} entradas, {os.path.getsize(a.pack) / 1e6:.1f} MB comprimido, "
              f"{raw / 1e6:.1f} MB sin comprimir")
        if man:
            print(f"  fuente={man.get('src')} creado={man.get('created')} "
                  f"símbolos={len(man.get('symbols', []))}")
            print("  " + ", ".join(man.get("symbols", [])[:12]) +
                  (" …" if len(man.get("symbols", [])) > 12 else ""))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Empaqueta/restaura datos de mercado")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack", help="crear un .zip con los datos locales")
    p.add_argument("--src", default="weltrade", choices=sorted(SRC_ROOTS))
    p.add_argument("--out", default="")
    p.set_defaults(func=cmd_pack)
    u = sub.add_parser("unpack", help="restaurar un .zip de datos")
    u.add_argument("pack")
    u.add_argument("--dest", default="")
    u.add_argument("--src", default="", choices=["", "weltrade", "yahoo"])
    u.set_defaults(func=cmd_unpack)
    i = sub.add_parser("info", help="ver el contenido de un .zip")
    i.add_argument("pack")
    i.set_defaults(func=cmd_info)
    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
