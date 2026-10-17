"""
Пример 4.4 — знако-ранговая карта Шухарта (Shewhart-SR).

Источник
--------
Chakraborti, S. and Graham, M.A. (2019). *Nonparametric Statistical
Process Control*. John Wiley & Sons.
Раздел 4.3.1, пример 4.4, стр. 225–228, рисунок 4.12,
таблицы 4.7a и 4.7b.

Что показывает пример
---------------------
20 независимых подгрупп размера n = 4 из неизвестного непрерывного
распределения, симметричного относительно известной медианы μ₀ = 0
(случай K).

Для каждой подгруппы берутся абсолютные отклонения |x_ij − μ₀|, их ранги
R_ij (1..n) и знаковая статистика

    SR_i = Σ_j φ(x_ij − μ₀) · R_ij = 2·T_n⁺ − n(n+1)/2.

Наибольшее возможное значение SR равно S = n(n+1)/2 = 10. Вероятность
P(SR ≥ 10) = 1/16 = 0.0625 — это наименьший достижимый «хвост» для n = 4
(больше FAR₀/2 = 0.00135), поэтому берётся максимум a = S = 10:

    UCL = +10,  CL = 0,  LCL = −10,
    FAR = 2·0.0625 = 0.125,  ARL_IC = 1/FAR = 8.

Объяснение
----------
Начиная с подгруппы 2 статистика SR = −10 попадает на LCL, поэтому процесс
объявляется OOC и требуется поиск назначенных причин. Точки на границах
(|SR| = 10): подгруппы 2, 3, 7, 11, 18.

Замечание. Книга печатает FAR = 0.124 (округление 0.062·2) и ARL ≈ 8;
точный расчёт даёт FAR = 0.125. Тест сверяется с точным значением.
"""

import pandas as pd
import pytest

from src.charts.signed_rank_chart import SignedRankChart

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


def _dataframe() -> pd.DataFrame:
    return pd.DataFrame(DATA, columns=["x1", "x2", "x3", "x4"])


@pytest.fixture
def chart() -> SignedRankChart:
    return SignedRankChart(_dataframe(), sample_size=4, target_value=0.0)


def test_example_4_4_book_control_limits(chart) -> None:
    """a = S = 10, точный FAR = 0.125, ARL_IC = 8 (книга, стр. 225–228)."""
    limits = chart.calculate_limits()

    assert limits["UCL"] == 10
    assert limits["LCL"] == -10
    assert limits["CL"] == 0
    assert limits["c_value"] == 10
    assert limits["SR_max"] == 10
    assert limits["FAR"] == pytest.approx(0.125)
    assert limits["ARL_IC"] == pytest.approx(8.0)


def test_example_4_4_book_sr_statistics(chart) -> None:
    """Значения SR_i совпадают с таблицей 4.7b(c)."""
    chart.calculate_limits()
    assert chart.subgroups["sr"].tolist() == pytest.approx(SR_BOOK)


def test_example_4_4_process_out_of_control(chart) -> None:
    """Процесс OOC: точки на LCL/UCL в подгруппах 2, 3, 7, 11, 18."""
    chart.calculate_limits()
    assert [v["subgroup"] for v in chart.violations] == VIOLATIONS_BOOK


def test_example_4_4_plot_saved(chart, results_dir) -> None:
    """Карта примера 4.4 строится и сохраняется с номером примера."""
    chart.calculate_limits()
    path = results_dir / "example_4_4_shewhart_sr_signed_rank.png"

    fig, ax = chart.plot(save_path=str(path))

    assert fig is not None
    assert ax is not None
    assert path.exists()
