"""Запуск всех скриптов проверки примеров книги и сводка.

Каждый скрипт запускается отдельным процессом, чтобы падение одного примера
не мешало остальным. Код возврата: 0 — все примеры совпали с книгой,
1 — есть расхождения.

Запуск из корня репозитория::

    poetry run python examples/run_all.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    scripts = sorted(HERE.glob("example_*.py"))
    if not scripts:
        print("Не найдено ни одного скрипта example_*.py")
        return 1

    failed: list[str] = []
    for script in scripts:
        print(f"\n>>> {script.name}", flush=True)
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=HERE,
        )
        if result.returncode != 0:
            failed.append(script.name)

    print("\n" + "=" * 72)
    if failed:
        print(f"Провалены: {', '.join(failed)}")
        return 1
    print(f"Все примеры ({len(scripts)}) прошли проверку")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
