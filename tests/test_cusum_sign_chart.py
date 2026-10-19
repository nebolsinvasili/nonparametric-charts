"""Тесты кода: CUSUM-карта по знакам (CUSUM-SN).

Проверяют инварианты API карты ``CusumSignChart``: расчёт кумулятивных сумм
``SN_t⁺``/``SN_t⁻``, счётчики ``N⁺``/``N⁻``, правило сигнала, границы и
визуализацию. Числа сверены с примерами 4.6 и 4.7 книги
Chakraborti & Graham (2019), §4.3.2 (стр. 229–233).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nonparametric_charts.charts.cusum_sign_chart import CusumSignChart
from nonparametric_charts.utils.statistics import sign_counts, sign_statistic


def _frame(rows: list[list[float]], n: int) -> pd.DataFrame:
    """DataFrame с колонками x1..xn (строка = подгруппа)."""
    return pd.DataFrame(rows, columns=[f"x{i}" for i in range(1, n + 1)])


def _rows_from_sn(sn_values: list[int], n: int) -> list[list[float]]:
    """Восстановить подгруппы размера n по заданным SN = n⁺ − n⁻.

    SN и число нетаёв имеют одинаковую чётность. Если чётность SN не совпадает
    с n, одна точка подгруппы считается равной μ₀ (связка, которая
    отбрасывается при расчёте знаковой статистики).
    """
    rows = []
    for sn in sn_values:
        untied = n if (n - sn) % 2 == 0 else n - 1
        n_plus = (untied + sn) // 2
        n_minus = untied - n_plus
        rows.append([1.0] * n_plus + [-1.0] * n_minus + [0.0] * (n - untied))
    return rows


# --------------------------------------------------------------------------- #
#  Утилита знаковой статистики
# --------------------------------------------------------------------------- #

def test_sign_statistic_basic() -> None:
    """SN = n⁺ − n⁻; нули (равные μ₀) не учитываются."""
    assert sign_counts([1.0, -1.0, 2.0, 0.0], 0.0) == (2, 1, 1)
    assert sign_statistic([1.0, -1.0, 2.0, 0.0], 0.0) == 1


# --------------------------------------------------------------------------- #
#  Пример 4.6: индивидуальные измерения (n = 1, k = 0.5, h = 3)
# --------------------------------------------------------------------------- #

def test_cusum_sn_example_4_6_paths() -> None:
    """Таблица 4.8: SN_t⁺ и счётчики N⁺ (30 наблюдений)."""
    sn = [-1, -1, -1, 1, 1, 1, -1, 1, -1, 1, -1, 1, 1, -1, 1,
          -1, 1, 1, -1, 1, 1, -1, 1, 1, 1, 1, 1, 1, 1, 1]
    chart = CusumSignChart(_frame(_rows_from_sn(sn, 1), 1),
                           sample_size=1, target_value=0.0, k=0.5, h=3.0)
    chart.calculate_limits()

    assert chart.subgroups["sn"].tolist() == sn
    assert chart.subgroups["sn_plus"].tolist() == pytest.approx(
        [0, 0, 0, 0.5, 1.0, 1.5, 0, 0.5, 0, 0.5, 0, 0.5, 1.0, 0, 0.5,
         0, 0.5, 1.0, 0, 0.5, 1.0, 0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    )
    assert chart.subgroups["nplus"].tolist() == (
        [0, 0, 0, 1, 2, 3, 0, 1, 0, 1, 0, 1, 2, 0, 1,
         0, 1, 2, 0, 1, 2, 0, 1, 2, 3, 4, 5, 6, 7, 8]
    )


def test_cusum_sn_example_4_6_signal() -> None:
    """Пример 4.6: сигнал при t = 28 с N⁺ = 6 (оценка сдвига 28 − 6 = 22)."""
    sn = [-1, -1, -1, 1, 1, 1, -1, 1, -1, 1, -1, 1, 1, -1, 1,
          -1, 1, 1, -1, 1, 1, -1, 1, 1, 1, 1, 1, 1, 1, 1]
    chart = CusumSignChart(_frame(_rows_from_sn(sn, 1), 1),
                           sample_size=1, target_value=0.0, k=0.5, h=3.0)
    chart.calculate_limits()

    assert len(chart.violations) == 1
    signal = chart.violations[0]
    assert signal["subgroup"] == 28
    assert signal["side"] == "upper"
    assert signal["counter"] == 6
    assert signal["value"] == pytest.approx(3.0)


# --------------------------------------------------------------------------- #
#  Пример 4.7: подгруппы (n = 10, k = 2, h = 8)
# --------------------------------------------------------------------------- #

def test_cusum_sn_example_4_7_no_signal() -> None:
    """Таблица 4.9: обе ветви и счётчики; сигнала нет."""
    sn = [0, -8, -2, 2, -6, 0, 4, 2, 3, -2, 0, 6, 2, 2, 2]
    chart = CusumSignChart(_frame(_rows_from_sn(sn, 10), 10),
                           sample_size=10, target_value=0.0, k=2.0, h=8.0)
    chart.calculate_limits()

    assert chart.subgroups["sn"].tolist() == sn
    assert chart.subgroups["sn_plus"].tolist() == pytest.approx(
        [0, 0, 0, 0, 0, 0, 2, 2, 3, 0, 0, 4, 4, 4, 4]
    )
    assert chart.subgroups["nplus"].tolist() == (
        [0, 0, 0, 0, 0, 0, 1, 2, 3, 0, 0, 1, 2, 3, 4]
    )
    assert chart.subgroups["sn_minus"].tolist() == pytest.approx(
        [0, -6, -6, -2, -6, -4, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    )
    assert chart.subgroups["nminus"].tolist() == (
        [0, 1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    )
    assert chart.violations == []


# --------------------------------------------------------------------------- #
#  Границы, валидация, сигналы, график
# --------------------------------------------------------------------------- #

def test_cusum_sn_control_limits() -> None:
    """CL = 0, UCL = +h, LCL = −h, k и h сохранены."""
    chart = CusumSignChart(_frame([[-1], [-1], [1]], 1),
                           sample_size=1, target_value=0.0, k=0.5, h=3.0)
    limits = chart.calculate_limits()

    assert limits["CL"] == 0
    assert limits["UCL"] == 3.0
    assert limits["LCL"] == -3.0
    assert limits["k"] == 0.5
    assert limits["h"] == 3.0


def test_cusum_sn_first_signal() -> None:
    """Постоянные +1 (n = 1): SN_t⁺ = t·(1 − k) → первый сигнал при t = 2h."""
    chart = CusumSignChart(_frame([[1.0]] * 8, 1),
                           sample_size=1, target_value=0.0, k=0.5, h=3.0)
    chart.calculate_limits()

    # SN_t⁺ = 0.5·t; SN_t⁺ ≥ 3 впервые при t = 6.
    assert [v["subgroup"] for v in chart.violations] == [6]
    assert chart.violations[0]["counter"] == 6


def test_cusum_sn_invalid_parameters() -> None:
    """k ≤ 0 или h ≤ 0 запрещены."""
    with pytest.raises(ValueError):
        CusumSignChart(_frame([[1.0], [-1.0]], 1),
                       sample_size=1, target_value=0.0, k=0.0)
    with pytest.raises(ValueError):
        CusumSignChart(_frame([[1.0], [-1.0]], 1),
                       sample_size=1, target_value=0.0, h=-1.0)


def test_cusum_sn_summary_reports_signal() -> None:
    """get_summary() сообщает первый сигнал."""
    sn = [-1, -1, -1, 1, 1, 1, -1, 1, -1, 1, -1, 1, 1, -1, 1,
          -1, 1, 1, -1, 1, 1, -1, 1, 1, 1, 1, 1, 1, 1, 1]
    chart = CusumSignChart(_frame(_rows_from_sn(sn, 1), 1),
                           sample_size=1, target_value=0.0, k=0.5, h=3.0)
    summary = chart.get_summary()

    assert summary["chart_type"] == "CUSUM-SN"
    assert summary["first_signal"]["subgroup"] == 28
    assert summary["total_violations"] == 1


def test_cusum_sn_plot_returns_figure_and_axes(tmp_path: Path) -> None:
    """plot() возвращает фигуру и оси и умеет сохранять файл."""
    sn = [-1, -1, -1, 1, 1, 1, -1, 1, -1, 1, -1, 1, 1, -1, 1,
          -1, 1, 1, -1, 1, 1, -1, 1, 1, 1, 1, 1, 1, 1, 1]
    chart = CusumSignChart(_frame(_rows_from_sn(sn, 1), 1),
                           sample_size=1, target_value=0.0, k=0.5, h=3.0)
    chart.calculate_limits()

    path = tmp_path / "cusum_sn.png"
    fig, ax = chart.plot(save_path=str(path))

    assert fig is not None
    assert ax is not None
    assert path.exists()
