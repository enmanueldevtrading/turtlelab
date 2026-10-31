"""Ejecuta la suite del motor bt sin depender de pytest."""
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import test_bt_engine as tests


def main() -> int:
    names = [name for name in dir(tests) if name.startswith("test_")]
    failed = []
    started = time.time()
    for name in names:
        try:
            getattr(tests, name)()
            print("PASS", name)
        except Exception as exc:
            failed.append((name, exc))
            print("FAIL", name, repr(exc))
            traceback.print_exc()
    passed = len(names) - len(failed)
    print(f"{passed}/{len(names)} passed in {time.time() - started:.1f}s")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
