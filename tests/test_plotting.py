"""Тесты визуализации распределения длины серии (RL).

Проверяют библиотечный помощник ``plot_run_length``: две оси (PMF и CDF),
усечение по ``max_t``, сохранение в файл и методы ``plot_run_length()``
у CUSUM-карт. Числа распределений берутся из примеров 4.8/4.10 книги
Chakraborti & Graham (2019), §4.3.2.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nonparametric_charts.charts.cusum_sign_chart import CusumSignChart
from nonparametric_charts.charts.cusum_signed_rank_chart import (
    CusumSignedRankChart,
)
from nonparametric_charts.utils.run_length import cusum_sign_run_length
from nonparametric_charts.utils.plotting import plot_run_length


def _frame(rows: list[list[float]], n: int) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=[f"x{i}" for i in range(1, n + 1)])


# --------------------------------------------------------------------------- #
#  Функция plot_run_length
# --------------------------------------------------------------------------- #

def test_plot_run_length_draws_pmf_and_cdf() -> None:
    """PMF на левой оси, CDF — на правой (пример 4.8: n=5, k=1, h=4)."""
    result = cusum_sign_run_length(5, 1.0, 4.0)
    fig, ax = plot_run_length(result, usetex=False)

    assert len(fig.axes) == 2
    labels = [line.get_label() for line in ax.get_lines()]
    assert r"$P(N=t)$" in labels

    cdf_ax = fig.axes[1]
    assert any(line.get_label() == r"$F(t)=P(N \leq t)$"
               for line in cdf_ax.get_lines())
    assert ax.get_ylabel() == r"$P(N=t)$"


def test_plot_run_length_uses_result_characteristics_in_title() -> None:
    """В заголовок по умолчанию попадают ARL, SDRL и MRL."""
    result = cusum_sign_run_length(5, 1.0, 4.0)
    _, ax = plot_run_length(result, usetex=False)

    title = ax.get_title()
    assert f"{result.arl:.2f}" in title
    assert f"{result.sdrl:.2f}" in title
    assert str(result.mrl) in title


def test_plot_run_length_max_t_clips_axis() -> None:
    """``max_t`` ограничивает отображённый диапазон ``t``."""
    result = cusum_sign_run_length(10, 6.0, 4.0)
    assert len(result.pmf) > 5
    _, ax = plot_run_length(result, usetex=False, max_t=5)

    assert ax.get_xlim() == pytest.approx((0.5, 5.5))


def test_plot_run_length_rejects_empty_or_bad_max_t() -> None:
    result = cusum_sign_run_length(5, 1.0, 4.0)
    with pytest.raises(ValueError):
        plot_run_length(result, usetex=False, max_t=0)

    result.pmf = result.pmf[:0]
    with pytest.raises(ValueError):
        plot_run_length(result, usetex=False)


def test_plot_run_length_saves_file(tmp_path: Path) -> None:
    result = cusum_sign_run_length(5, 1.0, 4.0)
    path = tmp_path / "rl.png"
    plot_run_length(result, usetex=False, save_path=str(path))

    assert path.exists() and path.stat().st_size > 0


def test_plot_run_length_accepts_existing_axes() -> None:
    import matplotlib.pyplot as plt

    result = cusum_sign_run_length(5, 1.0, 4.0)
    fig, ax = plt.subplots()
    out_fig, out_ax = plot_run_length(result, ax=ax, usetex=False)

    assert out_fig is fig and out_ax is ax


# --------------------------------------------------------------------------- #
#  Методы карт
# --------------------------------------------------------------------------- #

def test_cusum_sign_plot_run_length_method() -> None:
    """Метод карты использует её текущие ``k`` и ``h`` (пример 4.6)."""
    chart = CusumSignChart(
        _frame([[-1.0], [1.0], [-1.0]], 1),
        sample_size=1, target_value=0.0, k=0.5, h=3.0,
    )
    fig, ax = chart.plot_run_length()
    direct = chart.run_length()

    assert len(fig.axes) == 2
    assert f"{direct.arl:.2f}" in ax.get_title()


def test_cusum_signed_rank_plot_run_length_method() -> None:
    """Метод карты CUSUM-SR (пример 4.9: n=4, k=3, h=8)."""
    rows = [[1.0, -1.0, 2.0, -2.0]] * 3
    chart = CusumSignedRankChart(
        _frame(rows, 4), sample_size=4, target_value=0.0, k=3.0, h=8.0,
    )
    fig, ax = chart.plot_run_length()
    direct = chart.run_length()

    assert len(fig.axes) == 2
    assert f"{direct.arl:.2f}" in ax.get_title()


# --------------------------------------------------------------------------- #
#  Экспорты
# --------------------------------------------------------------------------- #

def test_plot_run_length_is_exported_from_utils() -> None:
    from nonparametric_charts.utils import plot_run_length as exported

    assert exported is plot_run_length
