"""Пример 4.4 — знако-ранговая карта Шухарта (Shewhart-SR).

Источник
--------
Chakraborti, S. and Graham, M.A. (2019). *Nonparametric Statistical
Process Control*. John Wiley & Sons.
Раздел 4.3.1, пример 4.4, стр. 225–228, рисунок 4.12,
таблицы 4.7a и 4.7b.

Что показывает пример
---------------------
20 независимых подгрупп размера n = 4 из непрерывного распределения,
симметричного относительно известной медианы μ₀ = 0 (случай K).

SR_i = Σ_j φ(x_ij − μ₀)·R_ij = 2·T_n⁺ − n(n+1)/2. Максимум SR равен
S = n(n+1)/2 = 10, а P(SR ≥ 10) = 1/16 больше FAR₀/2, поэтому берётся
a = S = 10: UCL/LCL = ±10, FAR = 0.125, ARL_IC = 8. Начиная с подгруппы 2
SR = −10 попадает на LCL — процесс OOC (подгруппы 2, 3, 7, 11, 18).
"""

from __future__ import annotations

import pandas as pd

from _common import ROOT, ExampleReport
from nonparametric_charts.charts.signed_rank_chart import SignedRankChart

# Таблица 4.7a(a): 20 подгрупп по n = 4.
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

# Таблица 4.7b(c): книжные значения SR_i.
SR_BOOK = [2, -10, 10, -8, -2, 2, 10, -2, -8, -8,
           10, 6, -8, 4, -2, 0, 2, 10, -6, -2]

# Подгруппы, где |SR_i| ≥ a = 10 (точки на границах).
VIOLATIONS_BOOK = [2, 3, 7, 11, 18]


def main() -> int:
    rep = ExampleReport(
        "4.4",
        "знако-ранговая карта Шухарта",
        "Chakraborti & Graham (2019), § 4.3.1, пример 4.4, "
        "стр. 225–228, рис. 4.12, табл. 4.7a/4.7b",
    )
    rep.start()

    chart = SignedRankChart(
        pd.DataFrame(DATA, columns=["x1", "x2", "x3", "x4"]),
        sample_size=4,
        target_value=0.0,
    )
    limits = chart.calculate_limits()

    rep.section("Контрольные границы (книга, стр. 225–228)")
    rep.check("LCL", limits["LCL"], -10)
    rep.check("CL", limits["CL"], 0)
    rep.check("UCL", limits["UCL"], 10)
    rep.check("a", limits["a_value"], 10)
    rep.check("SR_max = n(n+1)/2", limits["SR_max"], 10)
    # Книга печатает FAR = 0.124 (округление); точное значение 0.125.
    rep.check("FAR (точное 0.125)", limits["FAR"], 0.125, approx=True)
    rep.check("ARL_IC", limits["ARL_IC"], 8.0, approx=True)

    rep.section("Значения SR_i (табл. 4.7b, столбец c)")
    rep.check("SR_i", chart.subgroups["sr"].tolist(), SR_BOOK)

    rep.section("Сигналы (|SR_i| ≥ a = 10)")
    got = [v["subgroup"] for v in chart.violations]
    rep.check("подгруппы-нарушения", got, VIOLATIONS_BOOK)
    rep.line("Процесс OOC — требуется поиск назначенных причин.")

    path = rep.results_dir() / "example_4_4_shewhart_sr_signed_rank.png"
    rep.section("График")
    chart.plot(save_path=str(path))
    rep.line(f"сохранён: {path.relative_to(ROOT)}")

    return rep.finish()


if __name__ == "__main__":
    raise SystemExit(main())
