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
    """График распределения длины серии: PMF (столбики) и CDF (ступень)."""
    import matplotlib.pyplot as plt
    import numpy as np

    from nonparametric_charts.utils.plot_style import (
        ACCENT,
        INK,
        apply_minimal_latex_style,
        despine,
        math_text,
    )

    apply_minimal_latex_style()
    t = np.arange(1, len(result.pmf) + 1)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.vlines(t, 0.0, result.pmf, color=ACCENT, linewidth=1.0)
    ax.plot(t, result.pmf, 'o', color=ACCENT, markersize=3.0,
            label=rf'$P(N=t)$')

    ax.set_xlabel(r'$t$ (' + math_text('длина серии') + ')')
    ax.set_ylabel(r'$P(N=t)$', color=ACCENT)
    ax.tick_params(axis='y', colors=ACCENT)
    ax.set_xlim(0.5, t[-1] + 0.5)
    ax.set_ylim(0.0, max(float(result.pmf.max()) * 1.2, 1e-3))

    ax2 = ax.twinx()
    ax2.step(t, result.cdf, where='post', color=INK, linewidth=1.2,
             label=rf'$F(t)=P(N \leq t)$')
    ax2.set_ylabel(r'$F(t)$', color=INK)
    ax2.set_ylim(0.0, 1.05)

    lines = ax.get_lines() + ax2.get_lines()
    ax.legend(lines, [line.get_label() for line in lines],
              loc='center right', fontsize=9, frameon=True)

    ax.set_title(
        title + '\n'
        + rf'$\mathrm{{ARL}} = {result.arl:.2f}$, '
          rf'$\mathrm{{SDRL}} = {result.sdrl:.2f}$, '
          rf'$\mathrm{{MRL}} = {result.mrl}$'
    )
    ax.grid(alpha=0.25, linestyle=':')
    despine(ax)
    despine(ax2)

    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"График сохранён: {path}")
