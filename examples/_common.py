"""Общие помощники для скриптов проверки примеров книги.

Каталог ``examples/`` — это *проверка примеров* из книги Чакраборти и Грэма
(2019): каждый скрипт печатает результаты расчёта в консоль, сверяет их с
книжными значениями и сохраняет график в ``results/examples/``.

Запуск из корня репозитория::

    poetry run python examples/example_4_1_shewhart_sn_individual.py

или все примеры сразу::

    poetry run python examples/run_all.py

Тесты кода библиотеки живут отдельно, в ``tests/`` (pytest).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, List

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

# Пакет импортируется и без установки (pip/poetry install делают то же самое).
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Куда складываются графики, построенные в примерах.
RESULTS_DIR = ROOT / "results" / "examples"


class ExampleReport:
    """Консольный отчёт о проверке одного примера книги."""

    def __init__(self, number: str, title: str, source: str) -> None:
        self.number = number
        self.title = title
        self.source = source
        self.failures: List[str] = []

    def start(self) -> None:
        print("=" * 72)
        print(f"Пример {self.number} — {self.title}")
        print(f"Источник: {self.source}")
        print("=" * 72)

    def section(self, text: str) -> None:
        print(f"\n{text}")
        print("-" * len(text))

    def line(self, text: str = "") -> None:
        print(f"  {text}")

    def check(
        self,
        label: str,
        got: Any,
        expected: Any,
        *,
        approx: bool = False,
        tol: float = 1e-9,
    ) -> bool:
        """Сверить значение с книжным и напечатать результат проверки."""
        if approx:
            ok = abs(float(got) - float(expected)) <= tol
        else:
            ok = got == expected

        mark = "OK  " if ok else "FAIL"
        print(
            f"  [{mark}] {label}: получено={self._fmt(got)}  "
            f"книга={self._fmt(expected)}"
        )
        if not ok:
            self.failures.append(label)
        return ok

    @staticmethod
    def _fmt(value: Any) -> str:
        if isinstance(value, float):
            return f"{value:.6g}"
        return repr(value)

    def results_dir(self) -> Path:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        return RESULTS_DIR

    def finish(self) -> int:
        print()
        print("=" * 72)
        if self.failures:
            print(
                f"ИТОГ: расхождения с книгой в {len(self.failures)} пункт(ах): "
                + ", ".join(self.failures)
            )
            return 1
        print("ИТОГ: все значения совпали с книгой")
        return 0


def plot_run_length(result, path: Path, title: str) -> None:
    """График распределения длины серии: PMF (столбики) и CDF (ступень).

    Тонкая обёртка над :func:`nonparametric_charts.utils.plot_run_length`:
    сохраняет прежнюю подпись ``(result, path, title)``, которой пользуются
    примеры книги. ``path`` — путь сохранения графика.
    """
    from nonparametric_charts.utils.plotting import plot_run_length as _plot

    fig, _ = _plot(result, title=title, save_path=str(path))

    import matplotlib.pyplot as plt
    plt.close(fig)
