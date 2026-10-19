"""Пример 4.6 — CUSUM-карта по знакам (CUSUM-SN) для индивидуальных
измерений.

Источник
--------
Chakraborti, S. and Graham, M.A. (2019). *Nonparametric Statistical
Process Control*. John Wiley & Sons.
Раздел 4.3.2, пример 4.6, стр. 229–231, рисунок 4.14, таблица 4.8.

Что показывает пример
---------------------
Те же 30 индивидуальных наблюдений, что и в примере 4.1 (таблица 4.5):
первые 20 — из N(μ₀ = 10, σ₀ = 1), последние 10 — из N(μ₁ = 11, σ₀ = 1).
Известная целевая медиана μ₀ = 10 (случай K).

CUSUM-SN с параметрами k = 0.5, h = 3. Верхняя ветвь
SN_t⁺ = max(0, SN_{t−1}⁺ + SN_t − k) накапливает положительные знаки и
впервые достигает h = 3 при t = 28 (SN_t⁺ = 3, N⁺ = 6). Счётчик N⁺ = 6
указывает, что сдвиг, скорее всего, произошёл при t − N⁺ = 28 − 6 = 22.
Для сравнения параметрическая (нормальная) CUSUM-карта на этих же данных
сигнализирует на одно наблюдение позже — при t = 29 (книга, стр. 231).
"""

from __future__ import annotations

import pandas as pd

from _common import ROOT, ExampleReport
from nonparametric_charts.charts.cusum_sign_chart import CusumSignChart

# Таблица 4.5, столбец (a): 30 индивидуальных наблюдений (как в примере 4.1).
DATA = [
    9.45, 7.99, 9.29, 11.66, 12.16, 10.18, 8.04, 11.46, 9.20, 10.34,
    9.03, 11.47, 10.51, 9.40, 10.08, 9.37, 10.62, 10.31, 8.52, 10.84,
    10.90, 9.33, 12.29, 11.50, 10.60, 11.08, 10.38, 11.62, 11.31, 10.52,
]

# Таблица 4.8, столбец (a): книжные значения SN_t.
SN_BOOK = [
    -1, -1, -1, 1, 1, 1, -1, 1, -1, 1,
    -1, 1, 1, -1, 1, -1, 1, 1, -1, 1,
    1, -1, 1, 1, 1, 1, 1, 1, 1, 1,
]

# Таблица 4.8, столбец (b): верхняя кумулятивная сумма SN_t⁺.
SN_PLUS_BOOK = [
    0, 0, 0, 0.5, 1.0, 1.5, 0, 0.5, 0, 0.5,
    0, 0.5, 1.0, 0, 0.5, 0, 0.5, 1.0, 0, 0.5,
    1.0, 0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0,
]

# Таблица 4.8, столбец (c): счётчик N⁺.
NPLUS_BOOK = [
    0, 0, 0, 1, 2, 3, 0, 1, 0, 1,
    0, 1, 2, 0, 1, 0, 1, 2, 0, 1,
    2, 0, 1, 2, 3, 4, 5, 6, 7, 8,
]


def main() -> int:
    rep = ExampleReport(
        "4.6",
        "CUSUM-карта по знакам, индивидуальные измерения",
        "Chakraborti & Graham (2019), § 4.3.2, пример 4.6, "
        "стр. 229–231, рис. 4.14, табл. 4.8",
    )
    rep.start()

    chart = CusumSignChart(
        pd.DataFrame({"x1": DATA}),
        sample_size=1,
        target_value=10.0,
        k=0.5,
        h=3.0,
    )
    limits = chart.calculate_limits()

    rep.section("Параметры карты (книга, стр. 229)")
    rep.check("μ₀", limits["target_value"], 10.0)
    rep.check("k", limits["k"], 0.5)
    rep.check("h", limits["h"], 3.0)
    rep.check("UCL = +h", limits["UCL"], 3.0)
    rep.check("LCL = −h", limits["LCL"], -3.0)

    rep.section("Значения SN_t (табл. 4.8, столбец a)")
    rep.check("SN_t", chart.subgroups["sn"].tolist(), SN_BOOK)

    rep.section("Верхняя кумулятивная сумма SN_t⁺ (табл. 4.8, столбец b)")
    got_plus = chart.subgroups["sn_plus"].tolist()
    rep.check("SN_t⁺", got_plus, SN_PLUS_BOOK)

    rep.section("Счётчик N⁺ (табл. 4.8, столбец c)")
    rep.check("N⁺", chart.subgroups["nplus"].tolist(), NPLUS_BOOK)

    rep.section("Сигнал")
    rep.check("число сигналов", len(chart.violations), 1)
    signal = chart.violations[0]
    rep.check("подгруппа-сигнал", signal["subgroup"], 28)
    rep.check("SN_t⁺ в точке сигнала", signal["value"], 3.0, approx=True)
    rep.check("счётчик N⁺", signal["counter"], 6)
    rep.line(
        f"Оценка точки сдвига: t − N⁺ = {signal['subgroup']} − "
        f"{signal['counter']} = {signal['subgroup'] - signal['counter']}."
    )

    path = rep.results_dir() / "example_4_6_cusum_sn_individual.png"
    rep.section("График")
    chart.plot(save_path=str(path))
    rep.line(f"сохранён: {path.relative_to(ROOT)}")

    return rep.finish()


if __name__ == "__main__":
    raise SystemExit(main())
