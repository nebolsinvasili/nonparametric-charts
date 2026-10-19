"""Тесты марковского расчёта длины серии (RL) для CUSUM-карт.

Сверка с первоисточником: Chakraborti & Graham (2019)
- пример 4.8 (CUSUM-SN, ``n = 5, k = 1, h = 4``) — стр. 233–235;
- пример 4.10 (CUSUM-SR, ``n = 4, k = 2, h = 6``) — стр. 238–240;
- характеристики RL — ур. 3.22–3.24, стр. 112.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nonparametric_charts.charts.cusum_sign_chart import CusumSignChart
from nonparametric_charts.charts.cusum_signed_rank_chart import (
    CusumSignedRankChart,
)
from nonparametric_charts.utils.run_length import (
    cusum_run_length,
    cusum_sign_run_length,
    cusum_signed_rank_run_length,
    sign_step_distribution,
    signed_rank_step_distribution,
)

BOOK_PERCENTILES = (0.05, 0.25, 0.5, 0.75, 0.95)


# --------------------------------------------------------------------------- #
#  Распределения статистики подгруппы
# --------------------------------------------------------------------------- #

def test_sign_step_distribution_ic() -> None:
    """SN = 2T − n, T ~ BIN(n, 0.5): симметрия, среднее 0, дисперсия n."""
    values, probabilities = sign_step_distribution(5)
    assert list(values) == [-5, -3, -1, 1, 3, 5]
    assert probabilities.sum() == pytest.approx(1.0)
    assert float(values @ probabilities) == pytest.approx(0.0)
    variance = float(((values ** 2) @ probabilities))
    assert variance == pytest.approx(5.0)


def test_signed_rank_step_distribution_matches_table_4_3() -> None:
    """Нулевое распределение T⁺ для n = 4 (табл. 4.3)."""
    values, probabilities = signed_rank_step_distribution(4)
    # T⁺ = 0..10 с частотами 1,1,1,2,2,2,2,2,1,1,1 (всего 16)
    counts = [1, 1, 1, 2, 2, 2, 2, 2, 1, 1, 1]
    assert list(values) == [2 * s - 10 for s in range(11)]
    np.testing.assert_allclose(probabilities, np.array(counts) / 16)


# --------------------------------------------------------------------------- #
#  Пример 4.8: CUSUM-SN, n = 5, k = 1, h = 4
# --------------------------------------------------------------------------- #

def test_example_4_8_markov_characteristics() -> None:
    """ARL_IC = 16.62, SDRL_IC = 15.51, перцентили 2/6/12/23/48 (стр. 235)."""
    result = cusum_sign_run_length(5, 1, 4, sided='upper')

    assert result.method == 'markov'
    assert result.n_states == 2                 # Ω⁺ = {0, 2}, 4 — сигнал
    assert result.arl == pytest.approx(16.62, abs=0.01)
    assert result.sdrl == pytest.approx(15.51, abs=0.01)
    assert result.mrl == 12
    assert [result.percentiles[q] for q in BOOK_PERCENTILES] == [2, 6, 12, 23, 48]


def test_example_4_8_distribution_is_consistent() -> None:
    """PMF/CDF: монотонность, сумма ≈ 1, MRL — 50-й перцентиль."""
    result = cusum_sign_run_length(5, 1, 4, sided='upper')

    assert np.all(result.pmf >= 0)
    assert np.all(np.diff(result.cdf) >= -1e-12)
    assert result.cdf[-1] == pytest.approx(1.0, abs=1e-3)
    assert result.pmf.sum() == pytest.approx(result.cdf[-1])
    assert result.mrl == result.percentile(0.5)


# --------------------------------------------------------------------------- #
#  Пример 4.10: CUSUM-SR, n = 4, k = 2, h = 6
# --------------------------------------------------------------------------- #

def test_example_4_10_markov_characteristics() -> None:
    """ARL_IC = 6.81, SDRL_IC = 6.11, перцентили 1/2/5/9/19 (стр. 240)."""
    result = cusum_signed_rank_run_length(4, 2, 6, sided='upper')

    assert result.n_states == 3                 # Ω⁺ = {0, 2, 4}, 6 — сигнал
    assert result.arl == pytest.approx(6.81, abs=0.01)
    assert result.sdrl == pytest.approx(6.11, abs=0.01)
    assert result.mrl == 5
    assert [result.percentiles[q] for q in BOOK_PERCENTILES] == [1, 2, 5, 9, 19]


# --------------------------------------------------------------------------- #
#  Инварианты
# --------------------------------------------------------------------------- #

def test_lower_and_upper_are_identical_for_symmetric_ic() -> None:
    """В IC распределение SN симметрично: нижняя ветвь = верхняя."""
    upper = cusum_sign_run_length(5, 1, 4, sided='upper')
    lower = cusum_sign_run_length(5, 1, 4, sided='lower')
    assert lower.arl == pytest.approx(upper.arl)
    assert lower.sdrl == pytest.approx(upper.sdrl)


def test_two_sided_arl_is_smaller_than_one_sided() -> None:
    """Двусторонняя карта сигнализирует чаще любой односторонней."""
    one_sided = cusum_sign_run_length(10, 6, 4, sided='upper')
    two_sided = cusum_sign_run_length(10, 6, 4, sided='two')
    assert two_sided.arl < one_sided.arl
    assert two_sided.arl > one_sided.arl / 3


def test_shift_increases_signal_rate() -> None:
    """OOC (p > 0.5) уменьшает ARL верхней ветви."""
    ic = cusum_sign_run_length(10, 3, 8, sided='upper', p=0.5)
    ooc = cusum_sign_run_length(10, 3, 8, sided='upper', p=0.7)
    assert ooc.arl < ic.arl


def test_impossible_chart_raises() -> None:
    """Если статистика не может достичь h, ARL бесконечна — явная ошибка."""
    # Для n = 4 максимум |SR| = 10; при k = 11 приращение всегда ≤ −1
    # относительно нуля, поэтому сигнал невозможен.
    with pytest.raises(ValueError, match='ARL бесконечна'):
        cusum_signed_rank_run_length(4, 11, 10, sided='upper')


def test_generic_engine_accepts_arbitrary_steps() -> None:
    """Общий движок работает с произвольным дискретным распределением шага."""
    result = cusum_run_length(
        step_values=[-1, 1], step_probabilities=[0.5, 0.5], k=0.5, h=3,
        sided='two',
    )
    assert result.arl > 0
    assert result.n_states >= 1


# --------------------------------------------------------------------------- #
#  Интеграция с картами
# --------------------------------------------------------------------------- #

def _frame(rows: list[list[float]], n: int) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=[f'x{i}' for i in range(1, n + 1)])


def test_sign_chart_run_length_uses_chart_parameters() -> None:
    """``CusumSignChart.run_length`` берёт ``n``, ``k``, ``h`` из карты."""
    rows = [[1.0, 1.0, 1.0, 1.0, -1.0]] * 5
    chart = CusumSignChart(_frame(rows, 5), sample_size=5,
                           target_value=0.0, k=1.0, h=4.0)
    result = chart.run_length(sided='upper')
    assert result.arl == pytest.approx(16.615, abs=1e-3)


def test_signed_rank_chart_run_length_uses_chart_parameters() -> None:
    """``CusumSignedRankChart.run_length`` берёт ``n``, ``k``, ``h`` из карты."""
    rows = [[1.0, 2.0, 3.0, 4.0]] * 5
    chart = CusumSignedRankChart(_frame(rows, 4), sample_size=4,
                                 target_value=0.0, k=2.0, h=6.0)
    result = chart.run_length(sided='upper')
    assert result.arl == pytest.approx(6.8085, abs=1e-3)
