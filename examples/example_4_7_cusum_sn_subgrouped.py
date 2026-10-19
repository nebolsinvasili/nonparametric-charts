"""Пример 4.7 — CUSUM-карта по знакам (CUSUM-SN) для подгрупповых данных.

Источник
--------
Chakraborti, S. and Graham, M.A. (2019). *Nonparametric Statistical
Process Control*. John Wiley & Sons.
Раздел 4.3.2, пример 4.7, стр. 232–233, рисунок 4.15, таблица 4.9.

Что показывает пример
---------------------
Те же 15 подгрупп размера n = 10, что и в примере 4.2 (таблица 4.6),
из неизвестного непрерывного распределения; целевая медиана μ₀ = 0
(случай K).

CUSUM-SN с параметрами k = 2, h = 8. Ни верхняя, ни нижняя ветви не
достигают ±h: максимум SN_t⁺ = 4, минимум SN_t⁻ = −6, поэтому карта не
сигнализирует. Для этих же данных параметрическая CUSUM-карта тоже не
даёт сигнала (книга, стр. 233).
"""

from __future__ import annotations

import pandas as pd

from _common import ROOT, ExampleReport
from nonparametric_charts.charts.cusum_sign_chart import CusumSignChart

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

# Таблица 4.9, столбец (a): книжные значения SN_t.
SN_BOOK = [0, -8, -2, 2, -6, 0, 4, 2, 3, -2, 0, 6, 2, 2, 2]

# Таблица 4.9, столбец (b): верхняя кумулятивная сумма SN_t⁺.
SN_PLUS_BOOK = [0, 0, 0, 0, 0, 0, 2, 2, 3, 0, 0, 4, 4, 4, 4]

# Таблица 4.9, столбец (c): счётчик N⁺.
NPLUS_BOOK = [0, 0, 0, 0, 0, 0, 1, 2, 3, 0, 0, 1, 2, 3, 4]

# Таблица 4.9, столбец (d): нижняя кумулятивная сумма SN_t⁻.
SN_MINUS_BOOK = [0, -6, -6, -2, -6, -4, 0, 0, 0, 0, 0, 0, 0, 0, 0]

# Таблица 4.9, столбец (e): счётчик N⁻.
NMINUS_BOOK = [0, 1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0]


def main() -> int:
    rep = ExampleReport(
        "4.7",
        "CUSUM-карта по знакам, подгрупповые данные",
        "Chakraborti & Graham (2019), § 4.3.2, пример 4.7, "
        "стр. 232–233, рис. 4.15, табл. 4.9",
    )
    rep.start()

    columns = [f"x{i}" for i in range(1, 11)]
    chart = CusumSignChart(
        pd.DataFrame(DATA, columns=columns),
        sample_size=10,
        target_value=0.0,
        k=2.0,
        h=8.0,
    )
    limits = chart.calculate_limits()

    rep.section("Параметры карты (книга, стр. 232)")
    rep.check("k", limits["k"], 2.0)
    rep.check("h", limits["h"], 8.0)
    rep.check("UCL = +h", limits["UCL"], 8.0)
    rep.check("LCL = −h", limits["LCL"], -8.0)

    rep.section("Значения SN_t (табл. 4.9, столбец a)")
    rep.check("SN_t", chart.subgroups["sn"].tolist(), SN_BOOK)

    rep.section("Верхняя ветвь: SN_t⁺ и N⁺ (табл. 4.9, столбцы b, c)")
    rep.check("SN_t⁺", chart.subgroups["sn_plus"].tolist(), SN_PLUS_BOOK)
    rep.check("N⁺", chart.subgroups["nplus"].tolist(), NPLUS_BOOK)

    rep.section("Нижняя ветвь: SN_t⁻ и N⁻ (табл. 4.9, столбцы d, e)")
    rep.check("SN_t⁻", chart.subgroups["sn_minus"].tolist(), SN_MINUS_BOOK)
    rep.check("N⁻", chart.subgroups["nminus"].tolist(), NMINUS_BOOK)

    rep.section("Сигналы")
    rep.check("число сигналов", len(chart.violations), 0)
    rep.line("Ни одна ветвь не достигает ±h = ±8 — процесс IC при μ₀ = 0.")

    path = rep.results_dir() / "example_4_7_cusum_sn_subgrouped.png"
    rep.section("График")
    chart.plot(save_path=str(path))
    rep.line(f"сохранён: {path.relative_to(ROOT)}")

    return rep.finish()


if __name__ == "__main__":
    raise SystemExit(main())
