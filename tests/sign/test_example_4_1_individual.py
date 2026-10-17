"""
Пример 4.1 — знаковая карта Шухарта (Shewhart-SN) по индивидуальным
наблюдениям.

Источник
--------
Chakraborti, S. and Graham, M.A. (2019). *Nonparametric Statistical
Process Control*. John Wiley & Sons.
Раздел 4.3.1 (Shewhart Control Charts), пример 4.1, стр. 219–221,
рисунок 4.9, таблица 4.5.

Что показывает пример
---------------------
30 индивидуальных наблюдений (таблица 4.5, столбец (a)). Первые 20
извлечены из N(μ₀ = 10, σ₀ = 1), последние 10 — из N(μ₁ = 11, σ₀ = 1),
то есть со смещением δ = 1. Известная целевая медиана μ₀ = 10 (случай K).

Для n = 1 знаковая статистика SN_i = sign(x_i − μ₀) принимает лишь
значения −1 / +1, а наименьшая достижимая «правосторонняя» вероятность
P(SN ≥ a) равна 0.5 — это больше FAR₀/2 = 0.00135. Поэтому берётся
максимально широкое a = 1 (наименьший достижимый FAR). Книга даёт:

    UCL = +1,   CL = 0,   LCL = −1,   FAR = 1,   ARL_IC = 1.

Объяснение
----------
Пример иллюстрирует, почему знаковая карта по *индивидуальным* измерениям
непригодна: FAR = 1, любое наблюдение оказывается на границе, ARL_IC = 1.
Для малых выборок книга рекомендует CUSUM-SN / EWMA-SN (примеры 4.6, 4.11).
"""

import pandas as pd
import pytest

from src.charts.sign_chart import SignChart

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


def _dataframe() -> pd.DataFrame:
    return pd.DataFrame({"x1": DATA})


@pytest.fixture
def chart() -> SignChart:
    return SignChart(_dataframe(), sample_size=1, target_value=10.0)


def test_example_4_1_book_control_limits(chart) -> None:
    """Контрольные границы и характеристики как в книге (стр. 221)."""
    limits = chart.calculate_limits()

    assert limits["UCL"] == 1
    assert limits["LCL"] == -1
    assert limits["CL"] == 0
    assert limits["c_value"] == 1
    assert limits["FAR"] == pytest.approx(1.0)
    assert limits["ARL_IC"] == pytest.approx(1.0)


def test_example_4_1_book_sn_statistics(chart) -> None:
    """Значения SN_i совпадают с таблицей 4.5(b)."""
    chart.calculate_limits()
    assert chart.subgroups["sn"].tolist() == SN_BOOK


def test_example_4_1_plot_saved(chart, results_dir) -> None:
    """Карта примера 4.1 строится и сохраняется с номером примера."""
    chart.calculate_limits()
    path = results_dir / "example_4_1_shewhart_sn_individual.png"

    fig, ax = chart.plot(save_path=str(path))

    assert fig is not None
    assert ax is not None
    assert path.exists()
