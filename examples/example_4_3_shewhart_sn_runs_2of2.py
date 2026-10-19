"""Пример 4.3 — знаковая карта Шухарта (Shewhart-SN) с правилом серий
«2 из 2».

Источник
--------
Chakraborti, S. and Graham, M.A. (2019). *Nonparametric Statistical
Process Control*. John Wiley & Sons.
Раздел 4.3.1, пример 4.3, стр. 224–225, рисунок 4.11.

Что показывает пример
---------------------
Те же данные, что и в примере 4.2 (таблица 4.6). Карта дополняется
предупреждающими границами UWL/LWL = ±6 (при UCL/LCL = ±10): сигнал
подаётся при одной точке на UCL/LCL или за ними, либо при двух подряд
идущих точках на UWL/LWL или за ними.

По SN_i = [0, −8, −2, 2, −6, 0, 4, 2, 3, −2, 0, 6, 2, 2, 2] ни одно
правило не срабатывает — процесс IC при μ₀ = 0.
"""

from __future__ import annotations

import pandas as pd

from _common import ROOT, ExampleReport
from nonparametric_charts.charts.sign_chart import SignChart
from nonparametric_charts.utils.plot_style import hline

# Таблица 4.6(a): 15 подгрупп по n = 10 (те же данные, что в примере 4.2).
DATA = [
    [-0.30, -1.28, 0.24, 1.28, 1.20, 1.73, -2.18, -0.23, 1.10, -1.09],
    [-0.69, -1.69, -1.85, -0.98, -0.77, -2.12, -0.57, -0.40, 0.13, -0.37],
    [-0.33, -0.37, 1.34, -0.09, -0.19, -0.51, 1.97, 0.87, 2.38, -0.65],
    [1.66, -1.61, 0.54, 0.90, 1.92, -0.08, -0.52, 0.68, -0.38, 0.76],
    [-1.44, -0.85, -1.52, -0.36, -0.03, 0.03, -0.32, 2.19, -1.74, -0.74],
    [-2.58, 1.45, -1.28, -0.65, 0.76, 0.47, 0.87, 0.60, -1.37, -1.12],
    [0.69, 0.32, -0.94, -0.24, 0.13, 0.56, 0.14, -0.91, 1.88, 0.49],
    [0.07, 0.83, 0.86, -0.64, -0.92, 1.11, -1.20, -1.56, 0.71, 0.64],
    [2.21, 1.44, 1.30, 0.11, 0.00, 0.45, -0.03, -1.05, -1.77, 0.83],
    [0.44, 0.62, 0.21, -1.03, 1.24, -0.31, -0.84, -0.82, -0.43, -0.45],
    [-0.52, 0.85, 0.51, -0.61, 1.30, -1.76, 0.55, -0.12, 0.04, -0.65],
    [-0.55, 0.85, 0.80, 0.46, 0.69, 1.63, 0.30, 0.59, 1.85, -0.34],
    [1.04, 0.14, 1.14, -0.15, -0.78, 1.08, -0.58, 0.53, 0.55, -0.32],
    [-0.44, -1.37, 1.99, -0.57, 0.09, -0.23, 2.84, 1.25, 0.88, 1.33],
    [0.19, 0.54, -0.25, -1.22, 1.27, -0.29, -1.31, 0.76, 0.78, 0.43],
]

SN_BOOK = [0, -8, -2, 2, -6, 0, 4, 2, 3, -2, 0, 6, 2, 2, 2]

UWL, LWL = 6, -6


def _two_of_two(values: list[int], uwl: int, lwl: int) -> list[tuple[int, int]]:
    """Пары подряд идущих точек (1-based) на UWL/LWL или за ними."""
    hits = []
    for i in range(1, len(values)):
        a, b = values[i - 1], values[i]
        if (a >= uwl and b >= uwl) or (a <= lwl and b <= lwl):
            hits.append((i, i + 1))
    return hits


def main() -> int:
    rep = ExampleReport(
        "4.3",
        "знаковая карта Шухарта с правилом серий «2 из 2»",
        "Chakraborti & Graham (2019), § 4.3.1, пример 4.3, "
        "стр. 224–225, рис. 4.11",
    )
    rep.start()

    columns = [f"x{i}" for i in range(1, 11)]
    chart = SignChart(
        pd.DataFrame(DATA, columns=columns), sample_size=10, target_value=0.0
    )
    chart.calculate_limits()

    rep.section("Значения SN_i (табл. 4.6, столбец b)")
    rep.check("SN_i", chart.subgroups["sn"].tolist(), SN_BOOK)

    rep.section("Правило одноточечное (|SN| ≥ 10)")
    rep.check("число нарушений", len(chart.violations), 0)

    rep.section(f"Правило «2 из 2» (UWL/LWL = ±{UWL})")
    pairs = _two_of_two(chart.subgroups["sn"].tolist(), UWL, LWL)
    rep.check("пары сигналов", pairs, [])
    rep.line("Правило не срабатывает — процесс IC при μ₀ = 0.")

    path = rep.results_dir() / "example_4_3_shewhart_sn_runs_2of2.png"
    rep.section("График")
    fig, ax = chart.plot()
    hline(ax, UWL, "warning", label=rf"$\mathrm{{UWL}} = +{UWL}$")
    hline(ax, LWL, "warning", label=rf"$\mathrm{{LWL}} = -{abs(LWL)}$")
    ax.legend(loc="best", fontsize=8, ncol=2, labelspacing=0.25,
              handlelength=1.4, handletextpad=0.4,
              borderpad=0.3, borderaxespad=0.4, columnspacing=1.0)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    rep.line(f"сохранён: {path.relative_to(ROOT)}")

    return rep.finish()


if __name__ == "__main__":
    raise SystemExit(main())
