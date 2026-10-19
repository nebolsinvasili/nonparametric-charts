"""Тесты кода: CUSUM-карта по знаковым рангам (CUSUM-SR).

Проверяют инварианты API карты ``CusumSignedRankChart``: расчёт кумулятивных
сумм ``SR_t⁺``/``SR_t⁻``, счётчики ``N⁺``/``N⁻``, правило сигнала, границы и
визуализацию. Числа сверены с примером 4.9 книги Chakraborti & Graham (2019),
§4.3.2 (стр. 236–237, таблица 4.12).

Опечатка книги: печатная формула нижней ветви (ур. 4.11, стр. 206) содержит
``− k``; рабочий пример 4.9 (стр. 237) и параллель с ур. 4.8 (SN) требуют
``+ k``. Реализация следует ``+ k``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nonparametric_charts.charts.cusum_signed_rank_chart import CusumSignedRankChart
from nonparametric_charts.charts.signed_rank_chart import SignedRankChart
from nonparametric_charts.utils.statistics import (
    signed_rank_details,
    signed_rank_statistic,
)


# Таблица 4.7a (стр. 226): 20 подгрупп по n = 4, μ₀ = 0.
DATA_4_7A = [
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

# Таблица 4.12, столбец (a) / значения SR_t, восстановленные из табл. 4.7a.
SR_BOOK = [2, -10, 10, -8, -2, 2, 10, -2, -8, -8,
           10, 6, -8, 4, -2, 0, 2, 10, -6, -2]
SR_PLUS_BOOK = [0, 0, 7, 0, 0, 0, 7, 2, 0, 0,
                7, 10, 0, 1, 0, 0, 0, 7, 0, 0]
NPLUS_BOOK = [0, 0, 1, 0, 0, 0, 1, 2, 0, 0,
              1, 2, 0, 1, 0, 0, 0, 1, 0, 0]
SR_MINUS_BOOK = [0, -7, 0, -5, -4, 0, 0, 0, -5, -10,
                 0, 0, -5, 0, 0, 0, 0, 0, -3, -2]
NMINUS_BOOK = [0, 1, 0, 1, 2, 0, 0, 0, 1, 2,
               0, 0, 1, 0, 0, 0, 0, 0, 1, 2]


def _frame(rows: list[list[float]], n: int) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=[f"x{i}" for i in range(1, n + 1)])


def _chart(**kwargs) -> CusumSignedRankChart:
    params = dict(sample_size=4, target_value=0.0, k=3.0, h=8.0)
    params.update(kwargs)
    return CusumSignedRankChart(_frame(DATA_4_7A, 4), **params)


# --------------------------------------------------------------------------- #
#  Утилита знаково-ранговой статистики
# --------------------------------------------------------------------------- #

def test_signed_rank_statistic_basic() -> None:
    """SR = Σ sign(x)·rank(|x|): полный положительный набор квадратов."""
    assert signed_rank_statistic([1.0, 2.0, 3.0], 0.0) == 1 + 2 + 3
    assert signed_rank_statistic([-1.0, -2.0, -3.0], 0.0) == -(1 + 2 + 3)
    assert signed_rank_statistic([-1.0, 2.0, 3.0], 0.0) == -1 + 2 + 3


def test_signed_rank_details_matches_chart() -> None:
    """Утилита и ``SignedRankChart`` дают одинаковые SR для одних данных."""
    chart = SignedRankChart(_frame(DATA_4_7A, 4), sample_size=4,
                            target_value=0.0)
    chart.calculate_limits()
    for row in DATA_4_7A:
        assert signed_rank_details(row, 0.0)["sr"] == pytest.approx(
            signed_rank_statistic(row, 0.0))
    assert chart.subgroups["sr"].tolist() == pytest.approx(SR_BOOK)


# --------------------------------------------------------------------------- #
#  Пример 4.9: n = 4, k = 3, h = 8
# --------------------------------------------------------------------------- #

def test_cusum_sr_example_4_9_values() -> None:
    """Таблица 4.12: SR_t и обе ветви кумулятивных сумм."""
    chart = _chart()
    chart.calculate_limits()

    assert chart.subgroups["sr"].tolist() == pytest.approx(SR_BOOK)
    assert chart.subgroups["sr_plus"].tolist() == pytest.approx(SR_PLUS_BOOK)
    assert chart.subgroups["sr_minus"].tolist() == pytest.approx(SR_MINUS_BOOK)
    assert chart.subgroups["nplus"].tolist() == NPLUS_BOOK
    assert chart.subgroups["nminus"].tolist() == NMINUS_BOOK


def test_cusum_sr_example_4_9_signals() -> None:
    """Пример 4.9: сигнал на t = 10 (−10) и t = 12 (+10), счётчики N = 2."""
    chart = _chart()
    chart.calculate_limits()

    assert len(chart.violations) == 2
    lower, upper = chart.violations
    assert lower["subgroup"] == 10
    assert lower["side"] == "lower"
    assert lower["value"] == pytest.approx(-10.0)
    assert lower["counter"] == 2
    assert upper["subgroup"] == 12
    assert upper["side"] == "upper"
    assert upper["value"] == pytest.approx(10.0)
    assert upper["counter"] == 2


def test_cusum_sr_lower_branch_uses_plus_k() -> None:
    """Нижняя ветвь — ``+ k`` (пример 4.9), а не ``− k`` из печатной ур. 4.11."""
    # Знаки: SR_1 = −10 (все отрицательные, ранги 1..4).
    rows = [[-3.0, -2.0, -1.0, -0.5]]
    chart = CusumSignedRankChart(_frame(rows, 4), sample_size=4,
                                 target_value=0.0, k=3.0, h=8.0)
    chart.calculate_limits()
    # min(0, 0 + (−10) + 3) = −7  (с ошибочным −k было бы −13).
    assert chart.subgroups["sr_minus"].iloc[0] == pytest.approx(-7.0)


# --------------------------------------------------------------------------- #
#  Границы, валидация, сигналы, сводка, график
# --------------------------------------------------------------------------- #

def test_cusum_sr_control_limits() -> None:
    """CL = 0, UCL = +h, LCL = −h, k и h сохранены."""
    limits = _chart().calculate_limits()

    assert limits["CL"] == 0
    assert limits["UCL"] == 8.0
    assert limits["LCL"] == -8.0
    assert limits["k"] == 3.0
    assert limits["h"] == 8.0


def test_cusum_sr_first_signal_on_constant_side() -> None:
    """Постоянный максимальный SR (n = 4): SR_t⁺ = t·(S − k), сигнал при t = 2."""
    rows = [[1.0, 2.0, 3.0, 4.0]] * 4  # SR = 10 = S на каждой подгруппе
    chart = CusumSignedRankChart(_frame(rows, 4), sample_size=4,
                                 target_value=0.0, k=3.0, h=8.0)
    chart.calculate_limits()
    # SR_t⁺ = 7, 14 → первый сигнал при t = 2.
    assert [v["subgroup"] for v in chart.violations] == [2]
    assert chart.violations[0]["counter"] == 2


def test_cusum_sr_requires_n_at_least_two() -> None:
    """Ранжирование внутри подгруппы невозможно при n = 1."""
    with pytest.raises(ValueError):
        CusumSignedRankChart(_frame([[1.0], [-1.0]], 1),
                             sample_size=1, target_value=0.0)


def test_cusum_sr_invalid_parameters() -> None:
    """k ≤ 0 или h ≤ 0 запрещены."""
    with pytest.raises(ValueError):
        _chart(k=0.0)
    with pytest.raises(ValueError):
        _chart(h=-1.0)


def test_cusum_sr_summary_reports_signals() -> None:
    """get_summary() сообщает первый сигнал и общее число сигналов."""
    summary = _chart().get_summary()

    assert summary["chart_type"] == "CUSUM-SR"
    assert summary["first_signal"]["subgroup"] == 10
    assert summary["total_violations"] == 2


def test_cusum_sr_plot_returns_figure_and_axes(tmp_path: Path) -> None:
    """plot() возвращает фигуру и оси и умеет сохранять файл."""
    chart = _chart()
    chart.calculate_limits()

    path = tmp_path / "cusum_sr.png"
    fig, ax = chart.plot(save_path=str(path))

    assert fig is not None
    assert ax is not None
    assert path.exists()
