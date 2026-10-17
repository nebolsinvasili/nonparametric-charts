"""
Пример 4.2 — знаковая карта Шухарта (Shewhart-SN) по подгрупповым данным.

Источник
--------
Chakraborti, S. and Graham, M.A. (2019). *Nonparametric Statistical
Process Control*. John Wiley & Sons.
Раздел 4.3.1, пример 4.2, стр. 222–224, рисунок 4.10, таблица 4.6.

Что показывает пример
---------------------
15 независимых подгрупп размера n = 10 из неизвестного непрерывного
распределения. Известная целевая медиана μ₀ = 0 (случай K).

Знаковая статистика SN_i = n_i⁺ − n_i⁻ = 2T_i − n, где T_i ~ BIN(n, 0.5)
в IC. Для n = 10 из таблицы A (правосторонний «хвост» при 10) берётся
P(SN ≥ 10) = 1/1024 ≈ 0.000977 ≤ FAR₀/2 = 0.00135, откуда a = 10:

    UCL = +10,  CL = 0,  LCL = −10,
    FAR = 2·0.000977 ≈ 0.001953,  ARL_IC = 1/FAR ≈ 512.

Объяснение
----------
Ни одна точка не попадает на границы или за них, поэтому процесс считается
IC при μ₀ = 0. Пример подчёркивает distribution-free свойство: никаких
предположений о форме распределения (и о дисперсии) не требуется.

Замечание о книжном значении FAR
--------------------------------
Книга печатает FAR = 0.001994 и ARL_IC ≈ 502; точный расчёт даёт
FAR = 2/1024 = 0.001953125 и ARL_IC = 512 (в книге опечатка). Тест
сверяется с точным значением.
"""

import pandas as pd
import pytest

from src.charts.sign_chart import SignChart

# Таблица 4.6(a): 15 подгрупп по n = 10.
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

# Таблица 4.6(b): книжные значения SN_i.
SN_BOOK = [0, -8, -2, 2, -6, 0, 4, 2, 3, -2, 0, 6, 2, 2, 2]


def _dataframe() -> pd.DataFrame:
    columns = [f"x{i}" for i in range(1, 11)]
    return pd.DataFrame(DATA, columns=columns)


@pytest.fixture
def chart() -> SignChart:
    return SignChart(_dataframe(), sample_size=10, target_value=0.0)


def test_example_4_2_book_control_limits(chart) -> None:
    """a = 10 и точный FAR = 2/1024 (книга, стр. 222)."""
    limits = chart.calculate_limits()

    assert limits["UCL"] == 10
    assert limits["LCL"] == -10
    assert limits["CL"] == 0
    assert limits["c_value"] == 10
    assert limits["FAR"] == pytest.approx(2 / 1024)
    assert limits["ARL_IC"] == pytest.approx(1024 / 2)


def test_example_4_2_book_sn_statistics(chart) -> None:
    """Значения SN_i совпадают с таблицей 4.6(b)."""
    chart.calculate_limits()
    assert chart.subgroups["sn"].tolist() == SN_BOOK


def test_example_4_2_process_in_control(chart) -> None:
    """Ни одной точки на границах/вне них — процесс IC при μ₀ = 0."""
    chart.calculate_limits()
    assert chart.violations == []


def test_example_4_2_plot_saved(chart, results_dir) -> None:
    """Карта примера 4.2 строится и сохраняется с номером примера."""
    chart.calculate_limits()
    path = results_dir / "example_4_2_shewhart_sn_subgrouped.png"

    fig, ax = chart.plot(save_path=str(path))

    assert fig is not None
    assert ax is not None
    assert path.exists()
