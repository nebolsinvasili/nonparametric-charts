"""Инварианты, регрессии и валидация движка RL CUSUM (этап 3b.9).

Проверяется то, что не привязано к конкретному числу книги:

* распределения статистик ``SN``/``SR`` (моменты, чётность, симметрия);
* согласованность PMF/CDF с ``ARL``/``SDRL``/``MRL``;
* симметрия ветвей, отражение нижней ветви, монотонность по ``h`` и ``k``;
* совпадение марковского движка с renewal и симуляцией;
* регрессионные («золотые») значения и валидация аргументов.

Сверка с первоисточником: Chakraborti & Graham (2019)
- пример 4.8 (``n = 5, k = 1, h = 4``) — стр. 233–235;
- пример 4.10 (``n = 4, k = 2, h = 6``) — стр. 238–240;
- характеристики RL — ур. 3.22–3.24, стр. 112.
"""

from __future__ import annotations

import numpy as np
import pytest

from nonparametric_charts.utils.run_length import (
    RunLengthResult,
    cusum_run_length,
    cusum_sign_run_length,
    cusum_signed_rank_run_length,
    renewal_cusum_run_length,
    sign_step_distribution,
    signed_rank_step_distribution,
    simulate_cusum_sign_run_length,
    simulate_cusum_signed_rank_run_length,
)

QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)

#: Конфигурации для инвариантов распределения RL (дешёвые по времени).
INVARIANT_CONFIGS = (
    ('SN', 1, 0.5, 2, 'upper'),
    ('SN', 5, 1, 4, 'upper'),
    ('SN', 20, 6, 4, 'two'),
    ('SR', 4, 2, 6, 'upper'),
    ('SR', 20, 41, 4, 'two'),
)


def run_config(
    statistic: str,
    n: int,
    k: float,
    h: float,
    sided: str,
    **kwargs,
) -> RunLengthResult:
    """Запустить нужную обёртку движка по имени статистики."""
    if statistic == 'SN':
        return cusum_sign_run_length(n, k, h, sided=sided, **kwargs)
    return cusum_signed_rank_run_length(n, k, h, sided=sided, **kwargs)


def step_distribution(
    statistic: str, n: int
) -> tuple[np.ndarray, np.ndarray]:
    """IC-распределение статистики подгруппы."""
    if statistic == 'SN':
        return sign_step_distribution(n)
    return signed_rank_step_distribution(n)


# --------------------------------------------------------------------------- #
#  Распределения статистики подгруппы
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('n', [1, 2, 5, 10, 20])
def test_sign_distribution_moments(n: int) -> None:
    """``SN = 2T − n``: среднее 0, дисперсия ``n``, сумма вероятностей 1."""
    values, probabilities = sign_step_distribution(n)

    assert probabilities.sum() == pytest.approx(1.0)
    assert float(values @ probabilities) == pytest.approx(0.0, abs=1e-12)
    assert float((values ** 2) @ probabilities) == pytest.approx(n)
    # Значения решётчатые: SN ≡ n (mod 2).
    assert np.all((values - n) % 2 == 0)
    # IC-распределение симметрично.
    np.testing.assert_allclose(probabilities, probabilities[::-1])


@pytest.mark.parametrize('n', [2, 3, 4, 5, 10, 20])
def test_signed_rank_distribution_moments(n: int) -> None:
    """``SR``: среднее 0, дисперсия ``n(n+1)(2n+1)/6``, шаг решётки 2."""
    values, probabilities = signed_rank_step_distribution(n)
    expected_variance = n * (n + 1) * (2 * n + 1) / 6

    assert probabilities.sum() == pytest.approx(1.0)
    assert float(values @ probabilities) == pytest.approx(0.0, abs=1e-12)
    assert float((values ** 2) @ probabilities) == pytest.approx(
        expected_variance
    )
    assert np.all(np.diff(values) == 2.0)
    np.testing.assert_allclose(probabilities, probabilities[::-1])
    # Нулевое распределение Уилкоксона — целые кратности 2⁻ⁿ.
    counts = probabilities * 2 ** n
    np.testing.assert_allclose(counts, np.rint(counts), atol=1e-12)


# --------------------------------------------------------------------------- #
#  Инварианты распределения длины серии
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('statistic,n,k,h,sided', INVARIANT_CONFIGS)
def test_run_length_distribution_invariants(
    statistic: str, n: int, k: float, h: float, sided: str
) -> None:
    """PMF/CDF согласованы с моментами, перцентилями и усечением."""
    result = run_config(statistic, n, k, h, sided)

    assert result.method == 'markov'
    assert np.all(result.pmf >= 0.0)
    assert np.all(np.diff(result.cdf) >= -1e-12)
    assert result.cdf[-1] >= 0.9999 - 1e-9
    assert result.cdf[-1] <= 1.0 + 1e-12
    assert result.pmf.sum() == pytest.approx(result.cdf[-1])
    assert result.arl >= 1.0
    assert result.sdrl >= 0.0
    # Среднее положительной случайной величины не меньше медианы.
    assert result.arl >= result.mrl
    assert [result.percentiles[q] for q in QUANTILES] == sorted(
        result.percentiles[q] for q in QUANTILES
    )
    assert result.mrl == result.percentile(0.5)

    # Моменты, восстановленные по усечённой PMF, близки к точным.
    times = np.arange(1, len(result.pmf) + 1, dtype=float)
    mean = float(times @ result.pmf)
    second_moment = float((times ** 2) @ result.pmf)
    variance = max(second_moment - mean ** 2, 0.0)
    assert mean == pytest.approx(result.arl, rel=5e-3)
    assert np.sqrt(variance) == pytest.approx(result.sdrl, rel=5e-3)


@pytest.mark.parametrize('statistic,n,k,h', [
    ('SN', 1, 0.5, 2),
    ('SN', 5, 1, 4),
    ('SN', 10, 6, 4),
    ('SR', 4, 2, 6),
    ('SR', 10, 5, 8),
])
def test_upper_and_lower_branches_are_identical_in_ic(
    statistic: str, n: int, k: float, h: float
) -> None:
    """В IC распределение статистики симметрично: ветви эквивалентны."""
    upper = run_config(statistic, n, k, h, 'upper')
    lower = run_config(statistic, n, k, h, 'lower')

    assert lower.arl == pytest.approx(upper.arl, rel=1e-12)
    assert lower.sdrl == pytest.approx(upper.sdrl, rel=1e-12)
    assert lower.percentiles == upper.percentiles


def test_lower_branch_is_reflection_of_upper() -> None:
    """Нижняя ветвь — та же задача для ``Z → −Z`` (ур. 4.8)."""
    values, probabilities = sign_step_distribution(5)
    upper = cusum_run_length(values, probabilities, 1, 4, sided='upper')
    reflected = cusum_run_length(
        -values, probabilities, 1, 4, sided='lower'
    )
    assert reflected.arl == pytest.approx(upper.arl, rel=1e-12)


@pytest.mark.parametrize('statistic,n,k,h', [
    ('SN', 10, 6, 4),
    ('SR', 4, 2, 6),
    ('SR', 20, 41, 4),
])
def test_two_sided_chart_signals_not_later_than_one_sided(
    statistic: str, n: int, k: float, h: float
) -> None:
    """Двусторонняя карта — объединение ветвей, поэтому ``ARL`` не больше."""
    one_sided = run_config(statistic, n, k, h, 'upper')
    two_sided = run_config(statistic, n, k, h, 'two')

    assert two_sided.arl < one_sided.arl
    assert two_sided.arl > one_sided.arl / 3


@pytest.mark.parametrize('statistic,n,h,k_values', [
    ('SN', 10, 4, (1, 2, 3, 4, 5, 6, 7)),
    ('SR', 10, 4, (1, 5, 10, 20, 30, 40)),
])
def test_arl_is_monotone_in_reference_value(
    statistic: str, n: int, h: float, k_values: tuple[float, ...]
) -> None:
    """Рост ``k`` уменьшает дрейф накопленной суммы → ``ARL`` растёт."""
    arls = [
        run_config(statistic, n, k, h, 'two').arl for k in k_values
    ]
    assert np.all(np.diff(arls) > 0)


@pytest.mark.parametrize('statistic,n,k,h,delta', [
    ('SN', 10, 6, 4, 0.5),
    ('SR', 4, 2, 6, 0.5),
])
def test_shift_reduces_arl(
    statistic: str, n: int, k: float, h: float, delta: float
) -> None:
    """Положительный сдвиг увеличивает дрейф верхней ветви → ``ARL`` падает.

    Для ``SN`` распределение шага при сдвиге — то же ``2T − n`` с
    ``p = P(X ≥ μ₀) > 0.5``; для ``SR`` — распределение знаковых рангов при
    ``δ`` (OC-кривая, 3b.5).
    """
    from nonparametric_charts.utils.run_length_design import (
        sign_step_distribution_shift,
        signed_rank_step_distribution_shift,
    )

    ic = run_config(statistic, n, k, h, 'upper')
    if statistic == 'SN':
        values, probabilities = sign_step_distribution_shift(
            n, delta, 'normal'
        )
    else:
        values, probabilities = signed_rank_step_distribution_shift(
            n, delta, 'normal', method='exact'
        )
    ooc = cusum_run_length(values, probabilities, k, h, sided='upper')

    assert ooc.arl < ic.arl


# --------------------------------------------------------------------------- #
#  Независимые методы
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('statistic,n,k,h,sided', [
    ('SN', 5, 1, 4, 'upper'),
    ('SN', 20, 6, 4, 'two'),
    ('SR', 4, 2, 6, 'upper'),
    ('SR', 20, 41, 4, 'two'),
])
def test_renewal_agrees_with_markov(
    statistic: str, n: int, k: float, h: float, sided: str
) -> None:
    """Renewal-движок (3b.3) независимо воспроизводит марковский расчёт."""
    values, probabilities = step_distribution(statistic, n)
    renewal = renewal_cusum_run_length(
        values, probabilities, k, h, sided=sided
    )
    markov = cusum_run_length(
        values, probabilities, k, h, sided=sided
    )

    assert renewal.method == 'renewal'
    assert renewal.arl == pytest.approx(markov.arl, rel=1e-9)
    assert renewal.sdrl == pytest.approx(markov.sdrl, rel=1e-8)
    assert renewal.percentiles == markov.percentiles


def test_simulation_signed_rank_within_standard_error() -> None:
    """Монте-Карло SR согласуется с точным ``ARL`` в пределах 3 SE."""
    exact = cusum_signed_rank_run_length(4, 2, 6, sided='upper')
    simulated = simulate_cusum_signed_rank_run_length(
        4, 2, 6, sided='upper', n_rep=5_000, seed=20261020
    )
    standard_error = simulated.metadata['standard_error_arl']
    assert abs(simulated.arl - exact.arl) < 3 * standard_error
    assert simulated.metadata['n_rep'] == 5_000


def test_generic_engine_matches_sign_wrapper() -> None:
    """Общий движок на распределении ``SN`` даёт те же характеристики."""
    values, probabilities = sign_step_distribution(10)
    generic = cusum_run_length(
        values, probabilities, 6, 4, sided='two'
    )
    wrapped = cusum_sign_run_length(10, 6, 4, sided='two')

    assert generic.arl == pytest.approx(wrapped.arl, rel=1e-12)
    assert generic.sdrl == pytest.approx(wrapped.sdrl, rel=1e-12)
    np.testing.assert_array_equal(generic.pmf, wrapped.pmf)


def test_zero_probability_steps_are_ignored() -> None:
    """Шаги с нулевой вероятностью не меняют ни состояние, ни ``ARL``."""
    values, probabilities = sign_step_distribution(5)
    padded_values = np.concatenate([values, [101.0, -101.0]])
    padded_probabilities = np.concatenate([probabilities, [0.0, 0.0]])

    base = cusum_run_length(values, probabilities, 1, 4, sided='two')
    padded = cusum_run_length(
        padded_values, padded_probabilities, 1, 4, sided='two'
    )
    assert padded.arl == pytest.approx(base.arl, rel=1e-12)
    np.testing.assert_array_equal(padded.states, base.states)


def test_repeated_calculation_is_bitwise_identical() -> None:
    """Движок детерминирован: повторный расчёт даёт те же массивы."""
    first = cusum_sign_run_length(10, 6, 4, sided='two')
    second = cusum_sign_run_length(10, 6, 4, sided='two')

    np.testing.assert_array_equal(first.transition_matrix,
                                  second.transition_matrix)
    np.testing.assert_array_equal(first.pmf, second.pmf)
    np.testing.assert_array_equal(first.cdf, second.cdf)


# --------------------------------------------------------------------------- #
#  Регрессии на зафиксированные значения
# --------------------------------------------------------------------------- #

GOLDEN = (
    # statistic, n, k, h, sided, ARL, SDRL, MRL, n_states, percentiles
    ('SN', 1, 0.5, 2, 'upper', 30.0, 27.092434368288234, 22, 4,
     (4, 11, 22, 40, 84)),
    ('SN', 5, 1, 4, 'upper', 16.61538461538463, 15.508730124003447, 12, 2,
     (2, 6, 12, 23, 48)),
    ('SN', 10, 6, 4, 'two', 460.28282828283005, 464.3606725986238, 318, 3,
     (20, 129, 318, 640, 1387)),
    ('SN', 20, 6, 4, 'two', 21.742708146155582, 22.000970758051448, 15, 3,
     (1, 6, 15, 30, 66)),
    ('SR', 4, 2, 6, 'upper', 6.8085106382978715, 6.1063459113709255, 5, 3,
     (1, 2, 5, 9, 19)),
    ('SR', 10, 41, 14, 'two', 480.59969834711404, 486.27369893074973, 331,
     13, (19, 134, 331, 668, 1451)),
    ('SR', 20, 41, 4, 'two', 2.3880496864693463, 1.858223444300178, 2, 7,
     (1, 1, 2, 3, 6)),
)


@pytest.mark.parametrize(
    'statistic,n,k,h,sided,arl,sdrl,mrl,n_states,percentiles', GOLDEN
)
def test_golden_run_length_values(
    statistic: str,
    n: int,
    k: float,
    h: float,
    sided: str,
    arl: float,
    sdrl: float,
    mrl: int,
    n_states: int,
    percentiles: tuple[int, ...],
) -> None:
    """Зафиксированные значения движка (регрессия при рефакторингах)."""
    result = run_config(statistic, n, k, h, sided)

    assert result.arl == pytest.approx(arl, rel=1e-12)
    assert result.sdrl == pytest.approx(sdrl, rel=1e-10)
    assert result.mrl == mrl
    assert result.n_states == n_states
    assert tuple(result.percentiles[q] for q in QUANTILES) == percentiles
    assert result.metadata['statistic'] == statistic
    assert result.metadata['n'] == n


def test_summary_reports_all_characteristics() -> None:
    """``summary()`` содержит метод, параметры, моменты и число состояний."""
    result = cusum_sign_run_length(5, 1, 4, sided='upper')
    summary = result.summary()

    assert summary['method'] == 'markov'
    assert summary['sided'] == 'upper'
    assert summary['k'] == pytest.approx(1.0)
    assert summary['h'] == pytest.approx(4.0)
    assert summary['ARL'] == pytest.approx(result.arl)
    assert summary['SDRL'] == pytest.approx(result.sdrl)
    assert summary['MRL'] == result.mrl
    assert summary['n_states'] == result.n_states
    assert summary['truncated'] is result.truncated
    assert summary['statistic'] == 'SN'


# --------------------------------------------------------------------------- #
#  Валидация аргументов
# --------------------------------------------------------------------------- #

def test_sign_distribution_validates_arguments() -> None:
    with pytest.raises(ValueError, match='≥ 1'):
        sign_step_distribution(0)
    with pytest.raises(ValueError, match='p'):
        sign_step_distribution(5, p=1.5)


def test_signed_rank_distribution_validates_arguments() -> None:
    with pytest.raises(ValueError, match='n ≥ 2'):
        signed_rank_step_distribution(1)


def test_engine_validates_parameters() -> None:
    values, probabilities = sign_step_distribution(5)
    with pytest.raises(ValueError, match='k'):
        cusum_run_length(values, probabilities, 0, 4)
    with pytest.raises(ValueError, match='h'):
        cusum_run_length(values, probabilities, 1, -1)
    with pytest.raises(ValueError, match='sided'):
        cusum_run_length(values, probabilities, 1, 4, sided='middle')


def test_engine_validates_step_distribution() -> None:
    with pytest.raises(ValueError, match='одной длины'):
        cusum_run_length([-1, 1], [1.0], 1, 4)
    with pytest.raises(ValueError, match='непустым'):
        cusum_run_length([], [], 1, 4)
    with pytest.raises(ValueError, match='отрицательными'):
        cusum_run_length([-1, 1], [1.5, -0.5], 1, 4)
    with pytest.raises(ValueError, match='> 0'):
        cusum_run_length([-1, 1], [0.0, 0.0], 1, 4)


def test_simulation_validates_repetitions() -> None:
    with pytest.raises(ValueError, match='повторов'):
        simulate_cusum_sign_run_length(5, 1, 4, n_rep=0)


def test_percentile_validates_level() -> None:
    result = cusum_sign_run_length(5, 1, 4, sided='upper')
    with pytest.raises(ValueError, match='перцентиля'):
        result.percentile(0.0)
    with pytest.raises(ValueError, match='перцентиля'):
        result.percentile(1.0)
