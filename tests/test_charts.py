"""Тесты кода библиотеки (без привязки к конкретным примерам книги).

Проверяют инварианты API обеих непараметрических карт: построение
контрольных границ, расчёт статистик по подгруппам, правило сигнала и
визуализацию. Сверка с числами из книги и построение графиков-результатов —
в ``examples/`` (см. ``examples/README.md``).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nonparametric_charts.charts.sign_chart import SignChart
from nonparametric_charts.charts.signed_rank_chart import SignedRankChart


def _frame(rows: list[list[float]], n: int) -> pd.DataFrame:
    """DataFrame с колонками x1..xn (строка = подгруппа)."""
    return pd.DataFrame(rows, columns=[f"x{i}" for i in range(1, n + 1)])


# --------------------------------------------------------------------------- #
#  SignChart
# --------------------------------------------------------------------------- #

def test_sign_limits_are_symmetric_integers() -> None:
    """CL = 0, границы симметричны, a = UCL и лежит в 1..n."""
    chart = SignChart(_frame([[-2, -1, 0.5, 1, 2, 3, -1, -2, 1, 1]], 10),
                      sample_size=10, target_value=0.0)
    limits = chart.calculate_limits()

    assert limits["CL"] == 0
    assert limits["UCL"] == -limits["LCL"]
    assert limits["a_value"] == limits["UCL"]
    assert 1 <= limits["a_value"] <= 10


def test_sign_statistic_is_positive_minus_negative() -> None:
    """SN_i = n⁺ − n⁻ для одной подгруппы."""
    chart = SignChart(_frame([[-1, -2, 3, 4, -5]], 5),
                      sample_size=5, target_value=0.0)
    chart.calculate_limits()

    assert chart.subgroups["sn"].tolist() == [-1]


def test_sign_explicit_a_overrides_approach() -> None:
    """Явно заданное a_value задаёт границы, минуя расчёт по подходу."""
    chart = SignChart(_frame([[-1, 1, -1, 1, -1, 1, -1, 1]], 8),
                      sample_size=8, target_value=0.0, a_value=4)
    limits = chart.calculate_limits()

    assert limits["a_value"] == 4
    assert limits["UCL"] == 4
    assert limits["LCL"] == -4


def test_sign_violation_detected() -> None:
    """Все наблюдения выше μ₀ → SN = n → сигнал на верхней границе."""
    chart = SignChart(_frame([[1, 2, 3, 4, 5, 6, 7, 8]], 8),
                      sample_size=8, target_value=0.0)
    limits = chart.calculate_limits()

    assert limits["a_value"] == 8
    assert [v["subgroup"] for v in chart.violations] == [1]


def test_sign_compare_approaches_lists_all_modes() -> None:
    """Таблица сравнения подходов содержит три режима."""
    chart = SignChart(_frame([[1, -1, 2, -2, 3, -3]], 6),
                      sample_size=6, target_value=0.0)
    table = chart.compare_approaches()

    assert set(table["approach"]) == {"exact", "normal", "nearest"}
    assert {"a", "FAR", "ARL_IC"} <= set(table.columns)


def test_sign_plot_returns_figure_and_axes(tmp_path: Path) -> None:
    """plot() возвращает фигуру и оси и умеет сохранять файл."""
    chart = SignChart(_frame([[1, -1, 2, -2, 3, -3, 1, -1]], 8),
                      sample_size=8, target_value=0.0)
    chart.calculate_limits()

    path = tmp_path / "sign.png"
    fig, ax = chart.plot(save_path=str(path))

    assert fig is not None
    assert ax is not None
    assert path.exists()


# --------------------------------------------------------------------------- #
#  SignedRankChart
# --------------------------------------------------------------------------- #

def test_signed_rank_limits_and_max() -> None:
    """CL = 0, границы симметричны, SR_max = n(n+1)/2, a ≤ SR_max."""
    chart = SignedRankChart(_frame([[-0.4, 0.3, 0.2, 0.1]], 4),
                            sample_size=4, target_value=0.0)
    limits = chart.calculate_limits()

    assert limits["CL"] == 0
    assert limits["UCL"] == -limits["LCL"]
    assert limits["SR_max"] == 10
    assert 1 <= limits["a_value"] <= limits["SR_max"]


def test_signed_rank_statistic_matches_manual() -> None:
    """SR_i = Σ sign(d_j)·rank(|d_j|); ручной расчёт для n = 4."""
    # |d| = 1, 2, 3, 4; знаки +, −, +, − → 1 − 2 + 3 − 4 = −2.
    chart = SignedRankChart(_frame([[1, -2, 3, -4]], 4),
                            sample_size=4, target_value=0.0)
    chart.calculate_limits()

    assert chart.subgroups["sr"].tolist() == pytest.approx([-2])


def test_signed_rank_violation_detected() -> None:
    """Все отклонения одного знака → SR = SR_max → сигнал."""
    chart = SignedRankChart(_frame([[1, 2, 3, 4]], 4),
                            sample_size=4, target_value=0.0)
    limits = chart.calculate_limits()

    assert limits["a_value"] == limits["SR_max"]
    assert [v["subgroup"] for v in chart.violations] == [1]


def test_signed_rank_requires_at_least_two_observations() -> None:
    """n = 1 запрещено: ранжирование внутри подгруппы невозможно."""
    with pytest.raises(ValueError):
        SignedRankChart(_frame([[1]], 1), sample_size=1, target_value=0.0)


def test_signed_rank_plot_returns_figure_and_axes(tmp_path: Path) -> None:
    """plot() возвращает фигуру и оси и умеет сохранять файл."""
    chart = SignedRankChart(_frame([[1, -2, 3, -4], [-1, 2, -3, 4]], 4),
                            sample_size=4, target_value=0.0)
    chart.calculate_limits()

    path = tmp_path / "signed_rank.png"
    fig, ax = chart.plot(save_path=str(path))

    assert fig is not None
    assert ax is not None
    assert path.exists()
