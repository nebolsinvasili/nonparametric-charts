"""
Тесты Sign контрольной карты Шухарта (карта знаковых сумм) по книге:

С. Чакраборти, М. Грэм, «Nonparametric Statistical Process Control»,
Wiley, 2019, §4.2.1.1 и пример 4.2 (табл. 4.6), рис. 4.10.

Знаковая карта — непараметрическая карта контроля центра процесса.
Для каждой подгруппы вычисляется знаковая сумма:

    SN = n⁺ − n⁻,

где n⁺ (n⁻) — число наблюдений больше (меньше) заданного медианного
значения μ₀. Контрольные границы по книге (ур. 4.3):

    UCL = a,  CL = 0,  LCL = −a,

а карта сигнализирует о сдвиге, если |SN| ≥ a.

Пример 4.2: 15 подгрупп по n = 10 наблюдений из непрерывного
распределения, целевая медиана μ₀ = 0. Константа a = 10 подобрана по
правилу «наименьшее 0 < a ≤ n с P(SN ≥ a) ≤ FAR/2» при FAR = 0.0027
(правый хвост биномиального распределения). Все точки — внутри границ,
процесс в статистически управляемом состоянии.
"""

import numpy as np
import pandas as pd
import pytest
from scipy.special import comb

from src.charts.sign_chart import SignChart
from tests.conftest import COEFFICIENTS_FILE

# Данные книги (табл. 4.6): каждая строка — подгруппа (15), каждый
# столбец — одно наблюдение. Размер подгруппы n = 10, μ₀ = 0.
BOOK_DATA = pd.DataFrame(
    [
        [-0.30, -1.28, 0.24, 1.28, 1.20, 1.73, -2.18, -0.23, 1.10, -1.09],
        [-0.69, -1.69, -1.85, -0.98, -0.77, -2.12, -0.57, -0.40, 0.13, -0.37],
        [-0.33, -0.37, 1.34, -0.09, -0.19, -0.51, 1.97, 0.87, 2.38, -0.65],
        [1.66, -1.61, 0.54, 0.90, 1.92, -0.08, -0.52, 0.68, -0.38, 0.76],
        [-1.44, -0.85, -1.52, -0.36, -0.03, 0.03, -0.32, 2.19, -1.74, -0.74],
        [-2.58, 1.45, -1.28, -0.65, 0.76, 0.47, 0.87, 0.60, -1.37, -1.12],
        [0.69, 0.32, -0.94, -0.24, 0.13, 0.56, 0.14, -0.91, 1.88, 0.49],
        [0.07, 0.83, 0.86, -0.64, -0.92, 1.11, -1.20, -1.56, 0.71, 0.64],
        [0.21, 1.44, 1.30, 0.11, 0.00, 0.45, -0.03, -1.05, -1.77, 0.83],
        [0.44, 0.62, 0.21, -1.03, 1.24, -0.31, -0.84, -0.82, -0.43, -0.45],
        [-0.52, 0.85, 0.51, -0.61, 1.30, -1.76, 0.55, -0.12, 0.04, -0.65],
        [-0.55, 0.85, 0.80, 0.46, 0.69, 1.63, 0.30, 0.59, 1.85, -0.34],
        [1.04, 0.14, 1.14, -0.15, -0.78, 1.08, -0.58, 0.53, 0.55, -0.32],
        [-0.44, -1.37, 1.99, -0.57, 0.09, -0.23, 2.84, 1.25, 0.88, 1.33],
        [0.19, 0.54, -0.25, -1.22, 1.27, -0.29, -1.31, 0.76, 0.78, 0.43],
    ],
    columns=[f"x{i}" for i in range(1, 11)],
)

# Колонка SN контрольного листка (табл. 4.6, колонка (b)).
BOOK_SN = [0, -8, -2, 2, -6, 0, 4, 2, 3, -2, 0, 6, 2, 2, 2]

# Границы из книги (пример 4.2): a = 10, μ₀ = 0.
BOOK_A = 10
BOOK_UCL = BOOK_A
BOOK_LCL = -BOOK_A
BOOK_TARGET = 0.0


@pytest.fixture
def chart() -> SignChart:
    """Sign карта по данным книги (пример 4.2) с границей a = 10."""
    return SignChart(
        BOOK_DATA,
        sample_size=10,
        target_value=BOOK_TARGET,
        c_value=BOOK_A,
        coefficients_file=str(COEFFICIENTS_FILE),
    )


def test_book_example_sn_statistics(chart) -> None:
    """Знаковые суммы SN совпадают с колонкой (b) контрольного листка."""
    limits = chart.calculate_limits()
    assert limits["c_value"] == BOOK_A
    assert limits["target_value"] == BOOK_TARGET
    assert chart.subgroups["sn"].tolist() == BOOK_SN


def test_book_example_positive_negative_counts(chart) -> None:
    """Количества положительных и отрицательных отклонений (n⁺ и n⁻) верны."""
    chart.calculate_limits()
    positives = (BOOK_DATA > BOOK_TARGET).sum(axis=1)
    negatives = (BOOK_DATA < BOOK_TARGET).sum(axis=1)
    zeros = (BOOK_DATA == BOOK_TARGET).sum(axis=1)
    assert chart.subgroups["positive"].tolist() == positives.tolist()
    assert chart.subgroups["negative"].tolist() == negatives.tolist()
    assert chart.subgroups["zero"].tolist() == zeros.tolist()


def test_book_example_control_limits(chart) -> None:
    """Контрольные границы совпадают с книгой: UCL = +10, CL = 0, LCL = −10."""
    limits = chart.calculate_limits()
    assert limits["UCL"] == 10
    assert limits["CL"] == 0
    assert limits["LCL"] == -10
    assert limits["n"] == 10


def test_book_example_process_in_control(chart) -> None:
    """Ни одна точка не выходит за границы — процесс в стат. упр. состоянии."""
    chart.calculate_limits()
    outside = [v["subgroup"] for v in chart.violations]
    assert outside == []
    summary = chart.get_summary()
    assert summary["total_violations"] == 0
    assert summary["mean_sn"] == pytest.approx(np.mean(BOOK_SN), rel=1e-9)


def test_book_constant_a_from_binomial_far() -> None:
    """Константа a = 10 воспроизводится по правилу книги (FAR = 0.0027)."""
    n = 10
    alpha = 0.0027
    far_half = alpha / 2

    # a — наименьшее целое 0 < a <= n (той же чётности, что и n) с
    # P(SN >= a) <= alpha/2, где P(SN >= a) = P(T >= (n + a) / 2).
    a_book = None
    for a in range(1, n + 1):
        if a % 2 != n % 2:
            continue
        t = n + a
        p = sum(comb(n, m) * 0.5**n for m in range(t // 2, n + 1))
        if p <= far_half:
            a_book = a
            break
    assert a_book == 10

    chart = SignChart(
        BOOK_DATA,
        sample_size=n,
        target_value=BOOK_TARGET,
        alpha=alpha,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    assert chart.calculate_limits()["c_value"] == 10


def test_p_false_signal_matches_binomial_probability() -> None:
    """P(FS) = 2·P(SN >= 10) = 2·C(10,10)/2^10 для a = 10."""
    chart = SignChart(
        BOOK_DATA,
        sample_size=10,
        target_value=BOOK_TARGET,
        c_value=10,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    limits = chart.calculate_limits()
    expected = 2 * comb(10, 10) * 0.5**10  # 2 · (1/1024)
    assert limits["p_false_signal"] == pytest.approx(expected, rel=1e-12)
    assert limits["p_false_signal"] == pytest.approx(0.001953125, rel=1e-12)


def test_signal_rule_signals_at_limits() -> None:
    """Карта сигнализирует при |SN| >= c (правило книги, а не строгое >)."""
    data = pd.DataFrame(
        [
            [1.0, 1.0, 1.0],  # SN = 3 = c -> сигнал
            [-1.0, -1.0, 1.0],  # SN = -1, |SN| < 3
            [1.0, -1.0, -1.0],  # SN = -1
            [1.0, 1.0, -1.0],  # SN = 1
        ]
    )
    chart = SignChart(
        data,
        sample_size=3,
        target_value=0.0,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    limits = chart.calculate_limits()
    assert limits["c_value"] == 3
    assert chart.subgroups["sn"].tolist() == [3, -1, -1, 1]
    outside = [v["subgroup"] for v in chart.violations]
    assert outside == [1]


def test_default_alpha_more_sensitive_on_book_data() -> None:
    """При α = 0.05 по умолчанию константа c = 8 и подгруппа 2 сигналит."""
    chart = SignChart(
        BOOK_DATA,
        sample_size=10,
        target_value=BOOK_TARGET,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    limits = chart.calculate_limits()
    assert limits["c_value"] == 8
    assert limits["p_false_signal"] == pytest.approx(2 * 11 / 2**10, rel=1e-12)
    outside = [v["subgroup"] for v in chart.violations]
    assert outside == [2]  # SN = -8 -> |SN| >= 8


def test_class_matches_manual_calculation(chart) -> None:
    """Результаты класса совпадают с независимым ручным расчётом на pandas."""
    # Независимый ручной расчёт по формулам книги.
    positives = (BOOK_DATA > 0).sum(axis=1)
    negatives = (BOOK_DATA < 0).sum(axis=1)
    manual_sn = positives - negatives
    manual_outside = set((manual_sn.index + 1)[manual_sn.abs() >= BOOK_A])

    limits = chart.calculate_limits()
    assert chart.subgroups["sn"].tolist() == manual_sn.tolist()
    assert limits["UCL"] == BOOK_UCL
    assert limits["LCL"] == BOOK_LCL
    outside = {v["subgroup"] for v in chart.violations}
    assert outside == manual_outside


def test_subgroups_dataframe_structure(chart) -> None:
    """DataFrame подгрупп содержит нужные колонки и нумерацию 1..15."""
    chart.calculate_limits()
    assert list(chart.subgroups.columns) == [
        "positive",
        "negative",
        "zero",
        "sn",
        "subgroup",
    ]
    assert chart.subgroups["subgroup"].tolist() == list(range(1, 16))


def test_get_sn_table_returns_copy(chart) -> None:
    """get_sn_table() копирует подгруппы и не меняет состояние класса."""
    chart.calculate_limits()
    table = chart.get_sn_table()
    assert table.equals(chart.subgroups)
    table.loc[0, "sn"] = -999
    assert chart.subgroups.loc[0, "sn"] != -999


def test_control_limits_lazy() -> None:
    """Границы не считаются до вызова calculate_limits()."""
    chart = SignChart(
        BOOK_DATA,
        sample_size=10,
        target_value=BOOK_TARGET,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    assert chart.control_limits is None
    assert chart.subgroups is None
    limits = chart.calculate_limits()
    assert limits["UCL"] == 8  # константа по умолчанию для n = 10, α = 0.05
    assert chart.control_limits is not None


def test_plot_returns_figure_and_axes(chart, tmp_path) -> None:
    """plot() возвращает фигуру/оси и сохраняет график по save_path."""
    target = tmp_path / "sign_book.png"
    fig, ax = chart.plot(save_path=str(target))
    assert fig is not None
    assert ax is not None
    assert len(ax.get_lines()) >= 4  # данные + CL + UCL + LCL
    assert target.exists()
    assert target.stat().st_size > 0


def test_default_target_is_overall_median() -> None:
    """Если target_value не задан, используется медиана всех наблюдений."""
    data = pd.DataFrame([[1.0, 2.0], [3.0, 4.0]])
    chart = SignChart(
        data,
        sample_size=2,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    assert chart.target_value == pytest.approx(2.5, rel=1e-12)


def test_individual_measurements_n1() -> None:
    """Для n = 1 (пример 4.1) константа a = 1, границы ±1, FAR = 1."""
    data = pd.DataFrame([[9.45], [7.99], [9.29], [11.66], [12.16]])
    chart = SignChart(
        data,
        sample_size=1,
        target_value=10.0,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    limits = chart.calculate_limits()
    assert limits["c_value"] == 1
    assert limits["UCL"] == 1
    assert limits["LCL"] == -1
    assert chart.subgroups["sn"].tolist() == [-1, -1, -1, 1, 1]
    assert len(chart.violations) == 5  # |SN| = 1 = a -> каждая точка сигналит


def test_c_value_parity_correction() -> None:
    """При несовпадении чётности c_value корректируется (n=5, c=10 -> 11)."""
    data = pd.DataFrame(np.random.RandomState(1).randn(3, 5))
    chart = SignChart(
        data,
        sample_size=5,
        target_value=0.0,
        c_value=10,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    limits = chart.calculate_limits()
    assert limits["UCL"] == 11
    assert limits["LCL"] == -11


def test_data_csv_median_target_signals_on_boundary() -> None:
    """На data.csv при цели = медиане константа c = 8; SN = −8 на границе."""
    df = pd.read_csv("data/data.csv")
    chart = SignChart(
        df,
        sample_size=14,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    limits = chart.calculate_limits()
    assert limits["c_value"] == 8
    assert chart.target_value == pytest.approx(0.323, rel=1e-2)
    assert chart.subgroups["sn"].tolist() == [-4, 4, 4, 6, -6, 0, 4, 2, -2, -8]
    assert chart.subgroups["sn"].mean() == pytest.approx(0.0, abs=1e-9)
    # Правило книги |SN| >= a: подгруппа 10 с SN = −8 оказывается на границе.
    assert [(v["subgroup"], v["value"]) for v in chart.violations] == [(10, -8)]
    assert chart.get_summary()["total_violations"] == 1


def test_data_csv_shift_detection() -> None:
    """Смещённая цель (5.0) детектируется: все 10 подгрупп выходят за границы."""
    df = pd.read_csv("data/data.csv")
    chart = SignChart(
        df,
        sample_size=14,
        target_value=5.0,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    summary = chart.get_summary()
    assert summary["total_subgroups"] == 10
    assert summary["total_violations"] == 10
    assert set(v["subgroup"] for v in chart.violations) == set(range(1, 11))
    assert all(v["value"] <= -12 for v in chart.violations)
