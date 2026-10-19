"""Пример 4.5 — знако-ранговая карта Шухарта (Shewhart-SR) с правилом
серий «2 из 2».

Источник
--------
Chakraborti, S. and Graham, M.A. (2019). *Nonparametric Statistical
Process Control*. John Wiley & Sons.
Раздел 4.3.1, пример 4.5, стр. 228–229, рисунок 4.13.

Что показывает пример
---------------------
Те же данные, что и в примере 4.4 (таблица 4.7a). Предупреждающие границы
UWL/LWL = ±6 (при UCL/LCL = ±10). По SR_i = [2, −10, 10, −8, −2, 2, 10,
−2, −8, −8, 10, 6, −8, 4, −2, 0, 2, 10, −6, −2] правило «2 из 2»
срабатывает на парах (9, 10) и (11, 12); кроме того, подгруппа 2 даёт
одноточечный сигнал на LCL. Процесс OOC.
"""

from __future__ import annotations

import pandas as pd

from _common import ROOT, ExampleReport
from nonparametric_charts.charts.signed_rank_chart import SignedRankChart
from nonparametric_charts.utils.plot_style import hline

# Таблица 4.7a(a): 20 подгрупп по n = 4 (те же данные, что в примере 4.4).
DATA = [
    [-0.39, 0.03, 0.25, 0.30],
    [-0.61, -1.32, -2.84, -0.07],
    [2.04, 0.40, 0.54, 1.12],
    [-0.51, -1.63, 0.28, -0.96],
    [-0.20, -0.01, -0.21, 0.82],
    [2.03, 0.70, -1.21, -0.26],
    [0.64, 1.48, 0.91, 1.23],
    [0.19, -2.74, -0.85, 1.25],
    [-0.51, -1.77, -1.69, 0.24],
    [-0.84, -0.71, -0.82, 0.19],
    [0.29, 0.47, 0.04, 0.39],
    [0.38, 2.18, 1.24, -0.80],
    [-0.86, 0.61, -0.70, -1.13],
    [-0.31, 1.09, -0.43, 0.69],
    [0.42, 1.35, -0.51, -1.80],
    [0.39, -0.65, 1.57, -0.60],
    [1.31, -0.59, -0.21, 0.22],
    [0.64, 0.27, 0.26, 0.08],
    [-0.33, -0.49, 0.38, -1.54],
    [-0.48, -0.54, 1.73, -1.00],
]

SR_BOOK = [2, -10, 10, -8, -2, 2, 10, -2, -8, -8,
           10, 6, -8, 4, -2, 0, 2, 10, -6, -2]

UWL, LWL = 6, -6

# Книжные сигналы «2 из 2» (стр. 229).
TWO_OF_TWO_BOOK = [(9, 10), (11, 12)]


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
        "4.5",
        "знако-ранговая карта Шухарта с правилом серий «2 из 2»",
        "Chakraborti & Graham (2019), § 4.3.1, пример 4.5, "
        "стр. 228–229, рис. 4.13",
    )
    rep.start()

    chart = SignedRankChart(
        pd.DataFrame(DATA, columns=["x1", "x2", "x3", "x4"]),
        sample_size=4,
        target_value=0.0,
    )
    chart.calculate_limits()

    rep.section("Значения SR_i (табл. 4.7b, столбец c)")
    rep.check("SR_i", chart.subgroups["sr"].tolist(), SR_BOOK)

    rep.section(f"Правило «2 из 2» (UWL/LWL = ±{UWL})")
    pairs = _two_of_two(chart.subgroups["sr"].tolist(), UWL, LWL)
    rep.check("пары сигналов", pairs, TWO_OF_TWO_BOOK)

    rep.section("Одноточечное правило (|SR| ≥ 10)")
    got = [v["subgroup"] for v in chart.violations]
    rep.check("подгруппа 2 в нарушениях", 2 in got, True)
    rep.line(f"нарушения: {got}")

    path = rep.results_dir() / "example_4_5_shewhart_sr_runs_2of2.png"
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
