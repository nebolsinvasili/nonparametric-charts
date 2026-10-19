"""
Проверка правила выбора константы a (контрольных границ) в знаковой и
знако-ранговой картах.

Источник
--------
Chakraborti, S. and Graham, M.A. (2019). *Nonparametric Statistical
Process Control*. John Wiley & Sons.
Раздел 4.2.1.1 (знаковая карта, стр. 189–196) и § 4.2.1.2
(знако-ранговая карта, стр. 196–202).

Правило (точный подход, id ``exact``)
-------------------------------------
a — наименьшее *достижимое* значение статистики (той же чётности, что n
для SN и что S = n(n+1)/2 для SR), для которого

    P(статистика ≥ a) ≤ FAR₀/2,

то есть FAR = 2·P(· ≥ a) ≤ FAR₀. Если целевая вероятность недостижима
(малое n), берётся максимально возможное a = n (для SN) или a = S (для SR)
— самые широкие границы и наименьший достижимый FAR; так книга поступает
для n = 1 (a = 1, стр. 190) и n = 4 у SR (a = S = 10, пример 4.4).

Нормальная аппроксимация (id ``normal``)
----------------------------------------
a — наименьшее достижимое значение (той же чётности), не меньше
z_{1−FAR₀/2} · SD(статистики), где SD(SN) = sqrt(n),
SD(SR) = sqrt(n(n+1)(2n+1)/6). Это асимптотическая граница
(ср. npSPC::Limits_asymptotical); достигнутый FAR не обязан быть ≤ FAR₀,
а при малых n, где z·SD превышает максимум статистики, a = n (для SN)
или a = S (для SR).

Регрессия
---------
Ранее перебор a шёл сверху вниз и возвращал *наибольшее* подходящее a
(при n ≥ 10 это давало a = n, а при малых n — ошибочный fallback a = 1).
Здесь зафиксировано правильное поведение: наименьшее достижимое a.
"""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from nonparametric_charts.charts.sign_chart import SignChart
from nonparametric_charts.charts.signed_rank_chart import SignedRankChart

FAR0 = 0.0027


# ----------------------------------------------------------------------
#  Знаковая карта (SN, attainable-значения −n, −n+2, ..., n)
# ----------------------------------------------------------------------

@pytest.mark.parametrize("n, expected_a", [
    (1, 1),    # книга, пример 4.1: недостижимо, a = n = 1
    (8, 8),    # недостижимо, fallback a = n (раньше ошибочно 1)
    (10, 10),  # книга, пример 4.2
    (14, 12),  # наименьшее достижимое (раньше ошибочно 14)
    (16, 14),  # наименьшее достижимое
])
def test_sign_exact_book_values(n: int, expected_a: int) -> None:
    a, far = SignChart._calc_a_exact(n, FAR0)
    assert a == expected_a
    assert far == pytest.approx(2.0 * SignChart._p_sn_ge_a(n, a))


@pytest.mark.parametrize("n", range(1, 31))
def test_sign_exact_properties(n: int) -> None:
    """Минимальность, достижимая чётность и fallback = n."""
    a, far = SignChart._calc_a_exact(n, FAR0)

    assert 1 <= a <= n
    assert (a - n) % 2 == 0, "a должно быть достижимым (та же чётность, что n)"
    assert far == pytest.approx(2.0 * SignChart._p_sn_ge_a(n, a))

    p_a = SignChart._p_sn_ge_a(n, a)
    assert p_a <= FAR0 / 2 or a == n

    if a - 2 >= 1:
        assert SignChart._p_sn_ge_a(n, a - 2) > FAR0 / 2, "a не минимально"


@pytest.mark.parametrize("n", range(1, 31))
def test_sign_normal_approximation(n: int) -> None:
    """Нормальный подход: наименьшее достижимое a >= z·SD(SN), SD = sqrt(n)."""
    a, far = SignChart._calc_a_normal(n, FAR0)
    target = stats.norm.ppf(1.0 - FAR0 / 2.0) * np.sqrt(n)

    assert (a - n) % 2 == 0, "a должно быть достижимым (та же чётность, что n)"
    assert 1 <= a <= n
    # либо граница упирается в максимум (a = n), либо это наименьшее достижимое
    # значение не ниже нормального порога
    assert a == n or (a >= target - 1e-9 and a - 2 < target)
    assert far == pytest.approx(2.0 * SignChart._p_sn_ge_a(n, a))


# ----------------------------------------------------------------------
#  Знако-ранговая карта (SR, attainable-значения кратны 2 и лежат
#  в диапазоне −S..S, S = n(n+1)/2)
# ----------------------------------------------------------------------

def _sr_chart(n: int = 4) -> SignedRankChart:
    data = pd.DataFrame([[0.1 * (j + 1) for j in range(n)]])
    return SignedRankChart(data, sample_size=n, target_value=0.0)


def test_signed_rank_exact_book_example_4_4() -> None:
    """Пример 4.4: n = 4, целевая вероятность недостижима → a = S = 10."""
    chart = _sr_chart(4)
    a, far = SignedRankChart._calc_a_exact(4, FAR0, chart._p_sr_ge_a)

    assert a == 10
    assert a == 4 * 5 // 2
    assert far == pytest.approx(0.125)


@pytest.mark.parametrize("n", range(2, 17))
def test_signed_rank_exact_properties(n: int) -> None:
    """Минимальность, достижимая чётность (чётность S) и fallback = S."""
    chart = _sr_chart(n)
    S = n * (n + 1) // 2
    a, far = SignedRankChart._calc_a_exact(n, FAR0, chart._p_sr_ge_a)

    assert 1 <= a <= S
    assert (a - S) % 2 == 0, "a должно иметь чётность S"
    assert far == pytest.approx(2.0 * chart._p_sr_ge_a(n, a))

    p_a = chart._p_sr_ge_a(n, a)
    assert p_a <= FAR0 / 2 or a == S

    if a - 2 >= 1:
        assert chart._p_sr_ge_a(n, a - 2) > FAR0 / 2, "a не минимально"


@pytest.mark.parametrize("n", range(2, 21))
def test_signed_rank_normal_approximation(n: int) -> None:
    """
    Нормальный подход (нормальная аппроксимация): наименьшее достижимое a
    не меньше z·SD(SR), SD = sqrt(n(n+1)(2n+1)/6).
    """
    chart = _sr_chart(n)
    S = n * (n + 1) // 2
    a, far = SignedRankChart._calc_a_normal(n, FAR0, chart._p_sr_ge_a)
    target = stats.norm.ppf(1.0 - FAR0 / 2.0) * np.sqrt(n * (n + 1) * (2 * n + 1) / 6)

    assert (a - S) % 2 == 0, "a должно иметь чётность S"
    assert 1 <= a <= S
    assert a == S or (a >= target - 1e-9 and a - 2 < target)
    assert far == pytest.approx(2.0 * chart._p_sr_ge_a(n, a))
