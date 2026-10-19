"""Пример 4.9 — CUSUM-карта по знаковым рангам (CUSUM-SR).

Источник
--------
Chakraborti, S. and Graham, M.A. (2019). *Nonparametric Statistical
Process Control*. John Wiley & Sons.
Раздел 4.3.2, пример 4.9, стр. 236–238, рисунок 4.16, таблица 4.12.

Что показывает пример
---------------------
Те же 20 подгрупп n = 4 (таблица 4.7a), что и в примерах 4.4/4.5, с известной
медианой μ₀ = 0 (случай K). Требуется симметрия распределения.

CUSUM-SR с параметрами k = 3, h = 8. Верхняя ветвь
SR_t⁺ = max(0, SR_{t−1}⁺ + SR_t − k) и нижняя
SR_t⁻ = min(0, SR_{t−1}⁻ + SR_t + k) дают два сигнала: на t = 10
(SR⁻ = −10 < −h = −8, N⁻ = 2) и на t = 12 (SR⁺ = 10 > h = 8, N⁺ = 2).
Оба счётчика указывают на сдвиг около подгруппы t − N = 8.

Опечатка книги: печатная формула нижней ветви (ур. 4.11, стр. 206) содержит
``− k``; приведённый здесь расчёт (стр. 237) использует ``+ k`` — реализация
следует примеру.
"""

from __future__ import annotations

import pandas as pd

from _common import ROOT, ExampleReport
from nonparametric_charts.charts.cusum_signed_rank_chart import CusumSignedRankChart

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

# Таблица 4.12, столбец (a): значения SR_t.
SR_BOOK = [2, -10, 10, -8, -2, 2, 10, -2, -8, -8,
           10, 6, -8, 4, -2, 0, 2, 10, -6, -2]

# Таблица 4.12, столбец (a): верхняя кумулятивная сумма SR_t⁺.
SR_PLUS_BOOK = [0, 0, 7, 0, 0, 0, 7, 2, 0, 0,
                7, 10, 0, 1, 0, 0, 0, 7, 0, 0]

# Таблица 4.12, столбец (a): счётчик N⁺.
NPLUS_BOOK = [0, 0, 1, 0, 0, 0, 1, 2, 0, 0,
              1, 2, 0, 1, 0, 0, 0, 1, 0, 0]

# Таблица 4.12, столбец (b): нижняя кумулятивная сумма SR_t⁻.
SR_MINUS_BOOK = [0, -7, 0, -5, -4, 0, 0, 0, -5, -10,
                 0, 0, -5, 0, 0, 0, 0, 0, -3, -2]

# Таблица 4.12, столбец (b): счётчик N⁻.
NMINUS_BOOK = [0, 1, 0, 1, 2, 0, 0, 0, 1, 2,
               0, 0, 1, 0, 0, 0, 0, 0, 1, 2]


def main() -> int:
    rep = ExampleReport(
        "4.9",
        "CUSUM-карта по знаковым рангам",
        "Chakraborti & Graham (2019), § 4.3.2, пример 4.9, "
        "стр. 236–238, рис. 4.16, табл. 4.12",
    )
    rep.start()

    chart = CusumSignedRankChart(
        pd.DataFrame(DATA, columns=["x1", "x2", "x3", "x4"]),
        sample_size=4,
        target_value=0.0,
        k=3.0,
        h=8.0,
    )
    limits = chart.calculate_limits()

    rep.section("Параметры карты (книга, стр. 236)")
    rep.check("μ₀", limits["target_value"], 0.0)
    rep.check("k", limits["k"], 3.0)
    rep.check("h", limits["h"], 8.0)
    rep.check("UCL = +h", limits["UCL"], 8.0)
    rep.check("LCL = −h", limits["LCL"], -8.0)

    rep.section("Значения SR_t (табл. 4.12, столбец a)")
    rep.check("SR_t", chart.subgroups["sr"].tolist(), SR_BOOK)

    rep.section("Верхняя кумулятивная сумма SR_t⁺ и счётчик N⁺ "
                "(табл. 4.12, столбец a)")
    rep.check("SR_t⁺", chart.subgroups["sr_plus"].tolist(), SR_PLUS_BOOK)
    rep.check("N⁺", chart.subgroups["nplus"].tolist(), NPLUS_BOOK)

    rep.section("Нижняя кумулятивная сумма SR_t⁻ и счётчик N⁻ "
                "(табл. 4.12, столбец b)")
    rep.check("SR_t⁻", chart.subgroups["sr_minus"].tolist(), SR_MINUS_BOOK)
    rep.check("N⁻", chart.subgroups["nminus"].tolist(), NMINUS_BOOK)

    rep.section("Сигналы (рис. 4.16, стр. 237)")
    rep.check("число сигналов", len(chart.violations), 2)
    lower, upper = chart.violations
    rep.check("подгруппа нижнего сигнала", lower["subgroup"], 10)
    rep.check("SR_t⁻ в точке сигнала", lower["value"], -10, approx=True)
    rep.check("счётчик N⁻", lower["counter"], 2)
    rep.check("подгруппа верхнего сигнала", upper["subgroup"], 12)
    rep.check("SR_t⁺ в точке сигнала", upper["value"], 10, approx=True)
    rep.check("счётчик N⁺", upper["counter"], 2)
    rep.line(
        "Оценка точки сдвига: t − N = 10 − 2 = 8 и 12 − 2 = 10; "
        "книга указывает сдвиг около подгруппы 8 (стр. 237)."
    )

    path = rep.results_dir() / "example_4_9_cusum_sr.png"
    rep.section("График")
    chart.plot(save_path=str(path))
    rep.line(f"сохранён: {path.relative_to(ROOT)}")

    return rep.finish()


if __name__ == "__main__":
    raise SystemExit(main())
