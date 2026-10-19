"""Пример 4.1 — знаковая карта Шухарта (Shewhart-SN) по индивидуальным
наблюдениям.

Источник
--------
Chakraborti, S. and Graham, M.A. (2019). *Nonparametric Statistical
Process Control*. John Wiley & Sons.
Раздел 4.3.1, пример 4.1, стр. 219–221, рисунок 4.9, таблица 4.5.

Что показывает пример
---------------------
30 индивидуальных наблюдений (таблица 4.5, столбец (a)); первые 20 — из
N(μ₀ = 10, σ₀ = 1), последние 10 — из N(μ₁ = 11, σ₀ = 1). Известная
целевая медиана μ₀ = 10 (случай K).

Для n = 1 статистика SN_i = sign(x_i − μ₀) принимает лишь −1 / +1, а
наименьшая достижимая «правосторонняя» вероятность P(SN ≥ a) = 0.5 больше
FAR₀/2 = 0.00135. Поэтому берётся максимально широкое a = 1: FAR = 1,
ARL_IC = 1, любое наблюдение оказывается на границе. Пример показывает,
почему знаковая карта по индивидуальным измерениям непригодна.
"""

from __future__ import annotations

import pandas as pd

from _common import ROOT, ExampleReport
from nonparametric_charts.charts.sign_chart import SignChart

# Таблица 4.5, столбец (a): 30 индивидуальных наблюдений.
DATA = [
    9.45, 7.99, 9.29, 11.66, 12.16, 10.18, 8.04, 11.46, 9.20, 10.34,
    9.03, 11.47, 10.51, 9.40, 10.08, 9.37, 10.62, 10.31, 8.52, 10.84,
    10.90, 9.33, 12.29, 11.50, 10.60, 11.08, 10.38, 11.62, 11.31, 10.52,
]

# Таблица 4.5, столбец (b): книжные значения SN_i.
SN_BOOK = [
    -1, -1, -1, 1, 1, 1, -1, 1, -1, 1,
    -1, 1, 1, -1, 1, -1, 1, 1, -1, 1,
    1, -1, 1, 1, 1, 1, 1, 1, 1, 1,
]


def main() -> int:
    rep = ExampleReport(
        "4.1",
        "знаковая карта Шухарта по индивидуальным наблюдениям",
        "Chakraborti & Graham (2019), § 4.3.1, пример 4.1, "
        "стр. 219–221, рис. 4.9, табл. 4.5",
    )
    rep.start()

    chart = SignChart(
        pd.DataFrame({"x1": DATA}), sample_size=1, target_value=10.0
    )
    limits = chart.calculate_limits()

    rep.section("Контрольные границы (книга, стр. 221)")
    rep.check("LCL", limits["LCL"], -1)
    rep.check("CL", limits["CL"], 0)
    rep.check("UCL", limits["UCL"], 1)
    rep.check("a", limits["a_value"], 1)
    rep.check("FAR", limits["FAR"], 1.0, approx=True)
    rep.check("ARL_IC", limits["ARL_IC"], 1.0, approx=True)

    rep.section("Значения SN_i (табл. 4.5, столбец b)")
    rep.check("SN_i", chart.subgroups["sn"].tolist(), SN_BOOK)

    rep.section("Сигналы (|SN_i| ≥ a = 1)")
    rep.check("число нарушений", len(chart.violations), 30)
    rep.line("FAR = 1: каждое наблюдение лежит на границе — карта непригодна.")

    path = rep.results_dir() / "example_4_1_shewhart_sn_individual.png"
    rep.section("График")
    chart.plot(save_path=str(path))
    rep.line(f"сохранён: {path.relative_to(ROOT)}")

    return rep.finish()


if __name__ == "__main__":
    raise SystemExit(main())
