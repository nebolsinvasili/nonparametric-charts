"""Производительность и размер задачи движка RL CUSUM (этап 3b.9).

Guard-тесты на вычислительную стоимость марковского расчёта: пространство
состояний и время должны оставаться ограниченными на реперных дизайнах
``n = 10`` и ``n = 20`` (книжные рис. 4.5/4.6 и дизайн 3b.7). Пороговые
значения намеренно щедрые — это защита от патологического роста (например,
дробного ``k``, дробящего решётку), а не микро-бенчмарк.

Точные времена и разбивка по фазам — в ``experiments/cusum/04_performance.py``.

Модуль помечен ``@pytest.mark.slow``: в локальном быстром цикле
пропускается командой ``npc test --fast`` (см. ``docs/reports/cusum_plan.md``).
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from nonparametric_charts.utils.run_length import (
    cusum_sign_run_length,
    cusum_signed_rank_run_length,
)

pytestmark = pytest.mark.slow

#: Реперные дизайны (statistic, n, k, h, sided).
BENCHMARK_DESIGNS = (
    ('SN', 10, 6, 4, 'upper'),
    ('SN', 10, 6, 4, 'two'),
    ('SN', 20, 6, 4, 'upper'),
    ('SN', 20, 6, 4, 'two'),
    ('SR', 10, 41, 24, 'upper'),
    ('SR', 10, 41, 24, 'two'),
    ('SR', 20, 41, 24, 'upper'),
    ('SR', 20, 41, 24, 'two'),
)

#: Ожидаемое число непоглощающих состояний на реперных дизайнах.
EXPECTED_STATES = {
    ('SN', 10, 6, 4, 'upper'): 2,
    ('SN', 10, 6, 4, 'two'): 3,
    ('SN', 20, 6, 4, 'upper'): 2,
    ('SN', 20, 6, 4, 'two'): 3,
    ('SR', 10, 41, 24, 'upper'): 12,
    ('SR', 10, 41, 24, 'two'): 23,
    ('SR', 20, 41, 24, 'upper'): 24,
    ('SR', 20, 41, 24, 'two'): 47,
}

#: Щедрый бюджет времени на один расчёт (секунды).
TIME_BUDGET = 30.0


def run_benchmark(
    statistic: str, n: int, k: float, h: float, sided: str
):
    """Запустить расчёт на реперном дизайне.

    Для ``SR`` PMF усекается по медиане: ``ARL``/число состояний от
    ``max_quantile`` не зависят, а расчёт большого ``ARL`` (рис. 4.6) иначе
    занимает секунды на развёртку хвоста.
    """
    if statistic == 'SN':
        return cusum_sign_run_length(n, k, h, sided=sided)
    return cusum_signed_rank_run_length(
        n, k, h, sided=sided, max_quantile=0.5
    )


@pytest.mark.parametrize('statistic,n,k,h,sided', BENCHMARK_DESIGNS)
def test_state_space_matches_expected_size(
    statistic: str, n: int, k: float, h: float, sided: str
) -> None:
    """Число состояний ``Q`` на реперных дизайнах зафиксировано."""
    result = run_benchmark(statistic, n, k, h, sided)

    assert result.n_states == EXPECTED_STATES[
        (statistic, n, k, h, sided)
    ]
    assert result.transition_matrix.shape == (
        result.n_states, result.n_states
    )
    expected_state_shape = (result.n_states, 2) if sided == 'two' else (
        result.n_states,
    )
    assert result.states.shape == expected_state_shape


@pytest.mark.parametrize('statistic,n,k,h,sided', BENCHMARK_DESIGNS)
def test_benchmark_design_completes_within_budget(
    statistic: str, n: int, k: float, h: float, sided: str
) -> None:
    """Реперный расчёт укладывается в щедрый бюджет времени."""
    start = time.perf_counter()
    result = run_benchmark(statistic, n, k, h, sided)
    elapsed = time.perf_counter() - start

    assert result.arl > 0.0
    assert elapsed < TIME_BUDGET, (
        f'{statistic} n={n} k={k} h={h} {sided}: {elapsed:.2f} с'
    )


def test_fractional_reference_value_does_not_explode_state_space() -> None:
    """Дробное ``k`` не размножает состояния через шаг решётки."""
    start = time.perf_counter()
    sign = cusum_sign_run_length(10, 6.5, 4, sided='two')
    rank = cusum_signed_rank_run_length(10, 40.5, 12, sided='two')
    elapsed = time.perf_counter() - start

    # Без нормализации/половинного шага состояние расплылось бы в тысячи
    # точек; при ``k`` кратном 0.5 пространство остаётся линейным по h.
    assert sign.n_states < 100
    assert rank.n_states < 200
    assert elapsed < TIME_BUDGET


def test_large_run_length_computation_is_bounded() -> None:
    """Большой ``ARL`` (рис. 4.6) не приводит к неограниченному циклу PMF.

    При ``max_quantile = 0.5`` длина PMF ограничена медианой распределения
    (≈ 55 000 при точном ``ARL ≈ 79 500``), и весь расчёт остаётся быстрым.
    """
    start = time.perf_counter()
    result = cusum_signed_rank_run_length(
        10, 41, 24, sided='two', max_quantile=0.5
    )
    elapsed = time.perf_counter() - start

    assert result.cdf[-1] >= 0.5
    assert len(result.pmf) < 200_000
    assert elapsed < TIME_BUDGET


def test_state_space_grows_linearly_in_signal_interval() -> None:
    """Для фиксированного шага решётки число состояний растёт с ``h``.

    Проверяется на ``SN``: состояния — кратные 2 в ``[0, h)``, поэтому
    ``n_states`` монотонно не убывает по ``h``.
    """
    state_counts = [
        cusum_sign_run_length(20, 3, h, sided='upper').n_states
        for h in (2, 4, 6, 8, 10)
    ]
    assert np.all(np.diff(state_counts) >= 0)
    assert state_counts[-1] <= 10
