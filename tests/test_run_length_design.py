"""Тесты OC-кривых, приближений и подбора ``h`` для CUSUM-карт.

Сверка с первоисточником: Chakraborti & Graham (2019)
- выбор ``(k, h)`` — § 3.2.2, стр. 67; § 4.2.2, стр. 202–203;
- пример 4.8 (CUSUM-SN, ``n = 5, k = 1, h = 4``) — стр. 233–235;
- пример 4.10 (CUSUM-SR, ``n = 4, k = 2, h = 6``) — стр. 238–240;
- приближение Сигмунда — Siegmund (1985), § 4.2.2.2, стр. 205.
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
from nonparametric_charts.utils.run_length_design import (
    cached_arl,
    clear_run_length_cache,
    compare_arl_methods,
    design_h,
    design_sign_h,
    design_signed_rank_h,
    oc_curve,
    run_length_cache_info,
    siegmund_arl,
    sign_step_distribution_shift,
    signed_rank_step_distribution_exact,
    signed_rank_step_distribution_shift,
    wald_arl,
)

DISTRIBUTIONS = ('normal', 't', 'laplace', 'logistic', 'uniform', 'gamma')


# --------------------------------------------------------------------------- #
#  Распределения статистики при сдвиге
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('distribution', DISTRIBUTIONS)
def test_sign_shift_ic_is_distribution_free(distribution: str) -> None:
    """В IC ``P(X ≥ μ₀) = 0.5`` для любого непрерывного распределения."""
    values, probabilities = sign_step_distribution_shift(
        5, 0.0, distribution
    )
    expected_values, expected_probabilities = sign_step_distribution(5)
    np.testing.assert_allclose(values, expected_values)
    np.testing.assert_allclose(probabilities, expected_probabilities)


def test_sign_shift_positive_delta_increases_p() -> None:
    """Положительный сдвиг увеличивает ``P(X ≥ μ₀)``."""
    _, ic = sign_step_distribution_shift(5, 0.0, 'normal')
    _, ooc = sign_step_distribution_shift(5, 1.0, 'normal')
    # P(SN = 5) = p⁵
    assert float(ooc[-1]) > float(ic[-1])


def test_signed_rank_shift_ic_is_exact() -> None:
    """При ``δ = 0`` возвращается точное распределение (без симуляции)."""
    values, probabilities = signed_rank_step_distribution_shift(
        4, 0.0, 'normal', n_sim=100, seed=1
    )
    expected_values, expected_probabilities = signed_rank_step_distribution(4)
    np.testing.assert_allclose(values, expected_values)
    np.testing.assert_allclose(probabilities, expected_probabilities)


def test_signed_rank_shift_requires_symmetry() -> None:
    """SR — карта для симметричного распределения; несимметричное допустимо,
    но распределение статистики зависит от F."""
    values, probabilities = signed_rank_step_distribution_shift(
        4, 1.0, 'gamma', method='exact'
    )
    assert probabilities.sum() == pytest.approx(1.0)
    assert values.size > 1


def test_signed_rank_exact_is_deterministic() -> None:
    """Точная квадратура не зависит от seed и повторяется бит-в-бит."""
    first = signed_rank_step_distribution_exact(6, 1.0, 'normal')
    second = signed_rank_step_distribution_exact(6, 1.0, 'normal')
    np.testing.assert_array_equal(first[0], second[0])
    np.testing.assert_array_equal(first[1], second[1])


def test_signed_rank_exact_matches_monte_carlo() -> None:
    """Точное распределение совпадает с Монте-Карло в пределах шума."""
    exact_values, exact_probabilities = signed_rank_step_distribution_exact(
        4, 1.0, 'normal'
    )
    mc_values, mc_probabilities = signed_rank_step_distribution_shift(
        4, 1.0, 'normal', method='monte_carlo',
        n_sim=100_000, seed=20261019,
    )
    exact_full = np.zeros_like(exact_probabilities)
    mc_full = np.zeros_like(exact_probabilities)
    exact_index = np.rint(
        (exact_values + 10.0) / 2.0
    ).astype(int)
    mc_index = np.rint((mc_values + 10.0) / 2.0).astype(int)
    exact_full[exact_index] = exact_probabilities
    mc_full[mc_index] = mc_probabilities
    assert np.max(np.abs(exact_full - mc_full)) < 0.01


def test_signed_rank_exact_support_and_normalization() -> None:
    """Носитель — все значения SR, вероятности нормированы."""
    values, probabilities = signed_rank_step_distribution_exact(
        5, 0.75, 'laplace'
    )
    assert values[0] == -15.0
    assert values[-1] == 15.0
    assert np.all(np.diff(values) == 2.0)
    assert probabilities.sum() == pytest.approx(1.0)
    assert np.all(probabilities >= 0.0)


def test_signed_rank_shift_validates_method() -> None:
    with pytest.raises(ValueError, match='method'):
        signed_rank_step_distribution_shift(4, 1.0, method='unknown')


def test_signed_rank_auto_uses_exact_for_small_n() -> None:
    """``method='auto'`` для n = 4 совпадает с точной квадратурой."""
    auto = signed_rank_step_distribution_shift(4, 1.0, method='auto')
    exact = signed_rank_step_distribution_exact(4, 1.0)
    np.testing.assert_array_equal(auto[0], exact[0])
    np.testing.assert_array_equal(auto[1], exact[1])


# --------------------------------------------------------------------------- #
#  OC-кривые
# --------------------------------------------------------------------------- #

def test_sign_oc_curve_ic_and_monotonicity() -> None:
    """OC-кривая SN: IC совпадает с точной ARL и убывает по δ."""
    deltas = [0.0, 0.5, 1.0, 1.5, 2.0]
    curve = oc_curve(
        5, 1, 4, deltas, statistic='SN', sided='upper',
        distribution='normal',
    )
    exact = cusum_sign_run_length(5, 1, 4, sided='upper').arl
    assert curve.loc[0, 'arl'] == pytest.approx(exact, rel=1e-12)
    assert np.all(np.diff(curve['arl'].to_numpy()) < 0)
    assert (curve['arl'] >= 1.0).all()


def test_sign_oc_curve_ic_independent_of_distribution() -> None:
    """IC-ARL не зависит от распределения; OOC-ARL — зависит."""
    curves = {
        distribution: oc_curve(
            5, 1, 4, [0.0, 1.0], statistic='SN', sided='upper',
            distribution=distribution,
        )['arl'].to_numpy()
        for distribution in DISTRIBUTIONS
    }
    ic_values = [curve[0] for curve in curves.values()]
    np.testing.assert_allclose(ic_values, ic_values[0], rtol=1e-12)
    assert len({round(curve[1], 6) for curve in curves.values()}) > 1


def test_signed_rank_oc_curve_exact() -> None:
    """OC-кривая SR: IC — точная ARL, сдвиг уменьшает ARL."""
    curve = oc_curve(
        4, 2, 6, [0.0, 1.0], statistic='SR', sided='upper',
        method='exact',
    )
    assert curve.loc[0, 'arl'] == pytest.approx(6.8085106, rel=1e-6)
    assert curve.loc[1, 'arl'] < curve.loc[0, 'arl']
    assert curve.loc[1, 'arl'] >= 1.0


def test_signed_rank_oc_curve_monte_carlo_close_to_exact() -> None:
    """Монте-Карло OC-кривая близка к точной (в пределах шума)."""
    exact = oc_curve(
        4, 2, 6, [1.0], statistic='SR', sided='upper', method='exact',
    )
    monte_carlo = oc_curve(
        4, 2, 6, [1.0], statistic='SR', sided='upper',
        method='monte_carlo', n_sim=50_000, seed=20261019,
    )
    assert monte_carlo.loc[0, 'arl'] == pytest.approx(
        exact.loc[0, 'arl'], rel=0.05
    )


def test_oc_curve_rejects_unknown_statistic() -> None:
    with pytest.raises(ValueError, match='SN'):
        oc_curve(5, 1, 4, [0.0], statistic='XX')


# --------------------------------------------------------------------------- #
#  Приближения
# --------------------------------------------------------------------------- #

def test_wald_arl_example_4_8() -> None:
    """``1/FAR`` для примера 4.8: P(SN = 5) = 1/32 → ARL ≈ 32."""
    values, probabilities = sign_step_distribution(5)
    assert wald_arl(
        values, probabilities, 1, 4, sided='upper'
    ) == pytest.approx(32.0)
    assert wald_arl(
        values, probabilities, 1, 4, sided='two'
    ) == pytest.approx(16.0)


def test_siegmund_requires_positive_drift() -> None:
    """При ``E[Z] ≤ k`` приближение Сигмунда неприменимо (``inf``)."""
    values, probabilities = sign_step_distribution(5)
    assert siegmund_arl(values, probabilities, 1, 4, sided='upper') == np.inf

    shifted_values, shifted_probabilities = sign_step_distribution_shift(
        5, 2.0, 'normal'
    )
    approximation = siegmund_arl(
        shifted_values, shifted_probabilities, 1, 4, sided='upper'
    )
    assert np.isfinite(approximation)
    assert approximation > 1.0


def test_compare_arl_methods_table() -> None:
    values, probabilities = sign_step_distribution_shift(5, 1.0, 'normal')
    table = compare_arl_methods(values, probabilities, 1, 4, sided='two')
    assert list(table['method']) == ['markov', 'siegmund', 'wald_1_over_far']
    assert table.loc[0, 'relative_error'] == pytest.approx(0.0)
    assert np.isfinite(table.loc[0, 'arl'])


# --------------------------------------------------------------------------- #
#  Подбор h
# --------------------------------------------------------------------------- #

def test_design_sign_h_example_4_8() -> None:
    """Пример 4.8: ``n=5, k=1, ARL=16.615`` → ``h=4``."""
    result = design_sign_h(5, 16.615, 1, sided='upper')
    assert result.h == pytest.approx(4.0)
    assert result.arl == pytest.approx(16.615, rel=1e-3)
    assert result.relative_error < 1e-3


def test_design_signed_rank_h_example_4_10() -> None:
    """Пример 4.10: ``n=4, k=2, ARL=6.809`` → ``h=6``."""
    result = design_signed_rank_h(4, 6.809, 2, sided='upper')
    assert result.h == pytest.approx(6.0)
    assert result.arl == pytest.approx(6.809, rel=1e-3)


def test_design_h_reports_unreachable_nominal() -> None:
    """Для ``n=10, k=6`` номинал 500 недостижим: ``h=4`` даёт ARL ≈ 460."""
    result = design_sign_h(10, 500, 6, sided='two')
    assert result.h == pytest.approx(4.0)
    assert result.arl == pytest.approx(460.2828, rel=1e-6)
    assert result.relative_error < 0.1
    assert result.note


def test_design_h_validates_arguments() -> None:
    values, probabilities = sign_step_distribution(5)
    with pytest.raises(ValueError, match='> 1'):
        design_h(values, probabilities, 1.0, 1)
    with pytest.raises(ValueError, match='k'):
        design_h(values, probabilities, 100.0, 0)


def test_arl_is_monotone_in_h() -> None:
    """``ARL(h)`` не убывает по ``h`` (монотонность дизайна)."""
    sign_values, sign_probabilities = sign_step_distribution(10)
    sign_arls = [
        cusum_run_length(
            sign_values, sign_probabilities, 6, h,
            sided='two', max_quantile=0.5,
        ).arl
        for h in (2.0, 4.0, 6.0, 8.0)
    ]
    assert np.all(np.diff(sign_arls) >= 0)

    rank_values, rank_probabilities = signed_rank_step_distribution(10)
    rank_arls = [
        cusum_run_length(
            rank_values, rank_probabilities, 41, h,
            sided='two', max_quantile=0.5,
        ).arl
        for h in (4.0, 8.0, 12.0, 14.0)
    ]
    assert np.all(np.diff(rank_arls) >= 0)


def test_figure_4_5_design() -> None:
    """Рис. 4.5 (``n=10, k=6``): номинал 500 → ``h=4``, точная ARL ≈ 460.3."""
    result = design_sign_h(10, 500, 6, sided='two')
    assert result.h == pytest.approx(4.0)
    assert result.arl == pytest.approx(460.2828, rel=1e-4)
    # В книге — 454.24, симуляция 3b.2 — 461.05; расхождение в пределах
    # ошибки книги/симуляции, код не подгоняется.
    assert abs(result.arl - 454.24) / 454.24 < 0.02


def test_figure_4_6_open_discrepancy() -> None:
    """Рис. 4.6: точный расчёт не воспроизводит книжные 500.30 при h=24.

    Это открытое расхождение (см. ``docs/reports/cusum_plan.md``): точная
    двусторонняя ARL при ``n=10, k=41, h=24`` ≈ 79 500. Подбор под номинал
    500 даёт ``h=14``. Тест фиксирует текущее состояние, а не подгоняет код
    под книгу.
    """
    exact = cusum_signed_rank_run_length(
        10, 41, 24, sided='two', max_quantile=0.5
    )
    assert exact.arl > 50_000

    result = design_signed_rank_h(10, 500, 41, sided='two')
    assert result.h == pytest.approx(14.0)
    assert result.arl == pytest.approx(480.5997, rel=1e-4)


def test_design_h_is_monotone_in_nominal() -> None:
    """Чем больше номинал, тем больше (или равен) подобранный ``h``."""
    previous_h = 0.0
    for target in (10.0, 50.0, 200.0):
        result = design_sign_h(10, target, 6, sided='two')
        assert result.h >= previous_h
        previous_h = result.h


def test_chart_design_h_uses_chart_parameters() -> None:
    rows = [[1.0, 1.0, 1.0, 1.0, -1.0]] * 5
    sign_chart = CusumSignChart(
        pd.DataFrame(rows, columns=[f'x{i}' for i in range(1, 6)]),
        sample_size=5, target_value=0.0, k=1.0, h=4.0,
    )
    sign_result = sign_chart.design_h(16.615, sided='upper')
    assert sign_result.h == pytest.approx(4.0)

    rows = [[1.0, 2.0, 3.0, 4.0]] * 5
    rank_chart = CusumSignedRankChart(
        pd.DataFrame(rows, columns=[f'x{i}' for i in range(1, 5)]),
        sample_size=4, target_value=0.0, k=2.0, h=6.0,
    )
    rank_result = rank_chart.design_h(6.809, sided='upper')
    assert rank_result.h == pytest.approx(6.0)


def test_design_result_arl_matches_engine() -> None:
    """Достигнутая в дизайне ARL совпадает с прямым расчётом."""
    result = design_sign_h(10, 500, 6, sided='two')
    direct = cusum_run_length(
        *sign_step_distribution(10), 6, result.h, sided='two'
    )
    assert result.arl == pytest.approx(direct.arl, rel=1e-12)


# --------------------------------------------------------------------------- #
#  Кэш ARL для сеток дизайна
# --------------------------------------------------------------------------- #

def test_cached_arl_hits_on_repeated_call() -> None:
    clear_run_length_cache()
    values, probabilities = sign_step_distribution(10)
    first = cached_arl(values, probabilities, 6, 4, sided='two')
    second = cached_arl(values, probabilities, 6, 4, sided='two')
    assert first == second
    info = run_length_cache_info()
    assert info.misses >= 1
    assert info.hits >= 1


def test_cached_arl_matches_direct_engine() -> None:
    values, probabilities = sign_step_distribution(10)
    direct = cusum_run_length(
        values, probabilities, 6, 4, sided='two'
    ).arl
    assert cached_arl(
        values, probabilities, 6, 4, sided='two'
    ) == pytest.approx(direct, rel=1e-12)


def test_design_uses_cache() -> None:
    """Повторный подбор ``h`` не пересчитывает уже встречавшиеся ARL."""
    clear_run_length_cache()
    design_sign_h(10, 500, 6, sided='two')
    first = run_length_cache_info()
    design_sign_h(10, 500, 6, sided='two')
    second = run_length_cache_info()
    assert second.misses == first.misses
    assert second.hits > first.hits


def test_clear_run_length_cache() -> None:
    values, probabilities = sign_step_distribution(5)
    cached_arl(values, probabilities, 1, 4, sided='upper')
    assert run_length_cache_info().currsize >= 1
    clear_run_length_cache()
    assert run_length_cache_info().currsize == 0
