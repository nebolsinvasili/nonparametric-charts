"""
Дизайн CUSUM-карт по знакам и знаковым рангам и OC-кривые.

Модуль дополняет точный расчёт длины серии (`utils/run_length.py`):

- распределения статистики подгруппы при сдвиге процесса (OOC);
- OC-кривые ``ARL(δ)`` для разных распределений;
- подбор интервала решения ``h`` под номинальный ``ARL_IC``;
- совместный подбор ``(k, h)`` под целевой сдвиг ``δ`` и номинальный
  ``ARL_IC`` (минимум ``ARL_OOC``);
- приближённые формулы (Сигмунд, Вальд/``1/FAR``) для быстрых оценок.

Источник: Chakraborti & Graham (2019)
- выбор ``(k, h)`` — § 3.2.2, стр. 67–72 (``k = δ/2``, минимум
  ``ARL_OOC`` при фиксированном ``ARL_IC``); § 4.2.2, стр. 202–203;
  § 4.3.2, стр. 232–233, 236–238 (``k`` выбирается первым, ``h`` — под
  номинальный ``ARL_IC``); таблица ``(h, k)`` для ``n = 10`` —
  Amin, Reynolds & Bakir (1995), табл. 5;
- симуляция RL — § 4.2.2.3.2/§ 4.2.2.4.3, стр. 205/207–208;
- ARL и FAR — § 2.1.12, стр. 39–50.

Терминология: ``δ`` — сдвиг положения процесса в единицах стандартного
отклонения; ``μ₀`` — целевое значение (медиана в IC).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import factorial, gcd, inf, sqrt
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import numpy as np
import pandas as pd
from scipy import stats
from scipy.integrate import cumulative_trapezoid

from nonparametric_charts.utils.run_length import (
    _cusum_arl,
    cusum_run_length,
    sign_step_distribution,
    signed_rank_step_distribution,
)

__all__ = [
    'StandardizedDistribution',
    'sign_step_distribution_shift',
    'signed_rank_step_distribution_exact',
    'signed_rank_step_distribution_shift',
    'oc_curve',
    'siegmund_arl',
    'wald_arl',
    'compare_arl_methods',
    'cached_arl',
    'run_length_cache_info',
    'clear_run_length_cache',
    'DesignResult',
    'design_h',
    'design_sign_h',
    'design_signed_rank_h',
    'reference_k',
    'DesignKHResult',
    'design_kh',
    'design_sign_kh',
    'design_signed_rank_kh',
]


# --------------------------------------------------------------------------- #
#  Распределения процесса и статистики при сдвиге
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class StandardizedDistribution:
    """
    Стандартизованное непрерывное распределение (среднее 0, SD 1).

    Parameters
    ----------
    name : str
        Имя распределения.
    _dist : scipy.stats distribution
        Исходное (нестандартизованное) распределение.
    _center, _sd : float
        Медиана и стандартное отклонение исходного распределения.
        Центрирование по медиане гарантирует ``P(X ≥ 0) = 0.5`` в IC
        и для несимметричных распределений.
    """

    name: str
    _dist: Any
    _center: float
    _sd: float

    def sf(self, x: float) -> float:
        """``P(X ≥ x)`` для стандартизованного распределения."""
        return float(self._dist.sf(self._center + x * self._sd))

    def cdf(self, x: float) -> float:
        """``P(X ≤ x)`` для стандартизованного распределения."""
        return float(self._dist.cdf(self._center + x * self._sd))

    def pdf(self, x: float) -> float:
        """Плотность стандартизованного распределения."""
        return float(self._dist.pdf(self._center + x * self._sd)) * self._sd

    def ppf(self, q: float) -> float:
        """Квантиль стандартизованного распределения."""
        return (float(self._dist.ppf(q)) - self._center) / self._sd

    def rvs(self, size, rng: np.random.Generator) -> np.ndarray:
        """Выборка из стандартизованного распределения."""
        sample = self._dist.rvs(size=size, random_state=rng)
        return (np.asarray(sample) - self._center) / self._sd


def _cdf_array(
    std: StandardizedDistribution, x: Sequence[float]
) -> np.ndarray:
    """Векторизованная CDF стандартизованного распределения."""
    values = np.asarray(x, dtype=float)
    return np.asarray(std._dist.cdf(std._center + values * std._sd))


def _pdf_array(
    std: StandardizedDistribution, x: Sequence[float]
) -> np.ndarray:
    """Векторизованная плотность стандартизованного распределения."""
    values = np.asarray(x, dtype=float)
    return np.asarray(
        std._dist.pdf(std._center + values * std._sd)
    ) * std._sd


def _standardized(distribution: str) -> StandardizedDistribution:
    """Построить стандартизованное распределение по имени."""
    name = distribution.lower()
    if name == 'normal':
        dist = stats.norm()
    elif name in {'t', 'student'}:
        dist = stats.t(5)
    elif name == 'laplace':
        dist = stats.laplace(scale=1 / np.sqrt(2))
    elif name == 'logistic':
        dist = stats.logistic(scale=np.sqrt(3) / np.pi)
    elif name == 'uniform':
        root3 = np.sqrt(3.0)
        dist = stats.uniform(loc=-root3, scale=2 * root3)
    elif name == 'gamma':
        dist = stats.gamma(2.0)
    else:
        raise ValueError(
            f'Неизвестное распределение {distribution!r}; доступны: '
            "'normal', 't', 'laplace', 'logistic', 'uniform', 'gamma'"
        )

    return StandardizedDistribution(
        name,
        dist,
        float(dist.median()),
        float(dist.std()),
    )


def sign_step_distribution_shift(
    n: int,
    delta: float,
    distribution: str = 'normal',
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Распределение ``SN`` при сдвиге процесса на ``δ``.

    В IC ``P(X ≥ μ₀) = 0.5``; при сдвиге ``X → X + δ``:

        p = P(X + δ ≥ μ₀) = P(X ≥ −δ) = sf(−δ).

    Parameters
    ----------
    n : int
        Размер подгруппы.
    delta : float
        Сдвиг в единицах σ (``δ = 0`` — IC).
    distribution : str, default='normal'
        ``'normal'``, ``'t'``, ``'laplace'``, ``'logistic'``, ``'uniform'``,
        ``'gamma'``.

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray]
        Значения ``SN`` и вероятности.
    """
    std = _standardized(distribution)
    probability = std.sf(-delta)
    return sign_step_distribution(n, probability)


_SR_EXACT_MAX_N = 20


def signed_rank_step_distribution_exact(
    n: int,
    delta: float,
    distribution: str = 'normal',
    *,
    quadrature_points: int = 2_001,
    cdf_points: int = 20_001,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Распределение ``SR`` при сдвиге ``δ`` численным интегрированием.

    Для ``T⁺ = Σ r·I_r`` условно по порядковым статистикам ``|X|`` знаки
    независимы: ``I_r ~ Bernoulli(q(u_r))``, где ``u_r`` — порядковая
    статистика равномерного распределения, а

        q(u) = f_X(t) / (f_X(t) + f_X(−t)),   t = F_{|X|}⁻¹(u).

    Совместная плотность порядковых статистик ``u_1 < … < u_n`` равна ``n!``,
    поэтому производящий полином

        D_r(u, z) = ∫_0^u D_{r−1}(v, z)
                    [1 − q(v) + q(v)·z^r] dv

    даёт ``P(T⁺ = s) = n!·[z^s] D_n(1, z)``. Интегралы считаются
    кумулятивной трапецией на узлах Чебышёва—Лобатто (сгущение к краям
    ``u = 0, 1``); для ``n ≤ 20`` это доли секунды и ошибка порядка
    ``10⁻⁸…10⁻⁹`` (см. ``experiments/cusum/02_sr_exact_vs_mc.py``).

    Parameters
    ----------
    n : int
        Размер подгруппы (``2 ≤ n ≤ 60``).
    delta : float
        Сдвиг в единицах σ (``δ = 0`` — IC).
    distribution : str, default='normal'
        Распределение процесса; для SR предполагается симметричным, но
        метод работает и для несимметричной gamma.
    quadrature_points : int, default=2001
        Число узлов Чебышёва—Лобатто по ``u ∈ [0, 1]``.
    cdf_points : int, default=20001
        Число узлов для обращения ``F_{|X|}``.

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray]
        Значения ``SR = 2T⁺ − n(n+1)/2`` и вероятности.

    Notes
    -----
    При ``δ = 0`` возвращается точное нулевое распределение Уилкоксона
    (табл. 4.3), без квадратуры. Вывод метода — порядковые статистики
    ``|X|``; связь с RL — ур. 4.12 (Chakraborti & Graham, 2019, стр. 206).
    """
    if not isinstance(n, (int, np.integer)) or n < 2:
        raise ValueError(
            f'Размер подгруппы должен быть целым ≥ 2, получено {n}'
        )
    if n > 60:
        raise ValueError(
            'Точное интегрирование для SR поддержано до n = 60; '
            f'получено {n}. Используйте method="monte_carlo"'
        )
    if quadrature_points < 101:
        raise ValueError('quadrature_points должно быть ≥ 101')
    if cdf_points < 101:
        raise ValueError('cdf_points должно быть ≥ 101')
    if delta == 0:
        return signed_rank_step_distribution(n)

    std = _standardized(distribution)

    # Верхняя граница |X|: для ограниченного носителя — точная, иначе
    # квантиль 1 − 1e-12 (хвост за ней даёт вклад < 1e-12).
    lower = std.ppf(0.0)
    upper = std.ppf(1.0)
    if np.isfinite(lower) and np.isfinite(upper):
        max_absolute = max(abs(lower - delta), abs(upper - delta))
    else:
        max_absolute = max(
            abs(std.ppf(1e-12) - delta),
            abs(std.ppf(1.0 - 1e-12) - delta),
        )
    max_absolute = max(float(max_absolute), 1e-6)

    t_grid = np.linspace(0.0, max_absolute, cdf_points)
    cdf = (
        _cdf_array(std, t_grid - delta)
        - _cdf_array(std, -t_grid - delta)
    )
    cdf = np.maximum.accumulate(np.clip(cdf, 0.0, 1.0))

    # Узлы Чебышёва—Лобатто: сгущаются к u = 0 и u = 1, где производная
    # q(u) для тяжёлых хвостов/границ носителя имеет особенность.
    nodes = np.linspace(0.0, 1.0, quadrature_points)
    u_grid = 0.5 * (1.0 - np.cos(np.pi * nodes))
    t_values = np.interp(u_grid, cdf, t_grid)

    density_plus = _pdf_array(std, t_values - delta)
    density_minus = _pdf_array(std, -t_values - delta)
    denominator = density_plus + density_minus
    q = np.divide(
        density_plus,
        denominator,
        out=np.ones_like(density_plus),
        where=denominator > 0,
    )

    # D_r(u, z): коэффициенты по степеням z для каждого узла u.
    coefficients = np.ones((1, quadrature_points), dtype=float)
    for rank in range(1, n + 1):
        updated = np.zeros(
            (rank * (rank + 1) // 2 + 1, quadrature_points), dtype=float
        )
        for degree, values in enumerate(coefficients):
            updated[degree] += cumulative_trapezoid(
                values * (1.0 - q), u_grid, initial=0.0
            )
            updated[degree + rank] += cumulative_trapezoid(
                values * q, u_grid, initial=0.0
            )
        coefficients = updated

    probabilities = coefficients[:, -1] * float(factorial(n))
    probabilities = np.clip(probabilities, 0.0, None)
    total = float(probabilities.sum())
    if total <= 0:
        raise ValueError('Не удалось вычислить распределение SR')
    probabilities = probabilities / total

    support = 2.0 * np.arange(probabilities.size) - n * (n + 1) / 2.0
    return support, probabilities


def signed_rank_step_distribution_shift(
    n: int,
    delta: float,
    distribution: str = 'normal',
    *,
    method: str = 'auto',
    n_sim: int = 200_000,
    seed: Optional[int] = None,
    exact_max_n: int = _SR_EXACT_MAX_N,
    quadrature_points: int = 2_001,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Распределение ``SR`` при сдвиге процесса на ``δ``.

    Для ``δ = 0`` возвращается точное нулевое распределение Уилкоксона
    (табл. 4.3). Для ``δ ≠ 0`` доступны два метода:

    - ``'exact'`` — численное интегрирование по порядковым статистикам
      (``signed_rank_step_distribution_exact``), детерминированный результат;
    - ``'monte_carlo'`` — моделирование ``n_sim`` подгрупп, ошибка
      ``O(1/√n_sim)``;
    - ``'auto'`` (по умолчанию) — ``'exact'`` при ``n ≤ exact_max_n``,
      иначе ``'monte_carlo'``.

    Parameters
    ----------
    n : int
        Размер подгруппы (``n ≥ 2``).
    delta : float
        Сдвиг в единицах σ.
    distribution : str, default='normal'
        Симметричное (для SR) распределение процесса.
    method : {'auto', 'exact', 'monte_carlo'}, default='auto'
        Метод расчёта распределения при ``δ ≠ 0``.
    n_sim : int, default=200000
        Число моделируемых подгрупп (только Монте-Карло).
    seed : int, optional
        Зерно генератора (только Монте-Карло).
    exact_max_n : int, default=20
        Порог ``n`` для ``method='auto'``.
    quadrature_points : int, default=2001
        Число узлов квадратуры для точного метода.

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray]
        Значения ``SR`` и вероятности.

    Notes
    -----
    Точный метод убирает шум ``n_sim``; при ``n = 4`` ошибка Монте-Карло
    (100 000 подгрупп) порядка ``10⁻³``, точного — ``10⁻¹²``. Для ``n > 20``
    квадратура дороже, поэтому по умолчанию остаётся Монте-Карло.
    """
    method = method.lower()
    if method not in {'auto', 'exact', 'monte_carlo'}:
        raise ValueError(
            "method должен быть 'auto', 'exact' или 'monte_carlo', "
            f'получено {method!r}'
        )
    if delta == 0:
        return signed_rank_step_distribution(n)

    use_exact = method == 'exact' or (
        method == 'auto' and n <= exact_max_n
    )
    if use_exact:
        return signed_rank_step_distribution_exact(
            n, delta, distribution, quadrature_points=quadrature_points
        )

    std = _standardized(distribution)
    rng = np.random.default_rng(seed)
    sample = std.rvs((n_sim, n), rng) + delta

    absolute = np.abs(sample)
    order = np.argsort(absolute, axis=1)
    ranks = np.empty_like(order)
    np.put_along_axis(
        ranks, order, np.arange(1, n + 1, dtype=order.dtype), axis=1
    )
    values = np.sign(sample) * ranks
    statistics = values.sum(axis=1)

    support, counts = np.unique(statistics, return_counts=True)
    return support.astype(float), counts / n_sim


# --------------------------------------------------------------------------- #
#  OC-кривые
# --------------------------------------------------------------------------- #

def oc_curve(
    n: int,
    k: float,
    h: float,
    deltas: Iterable[float],
    *,
    statistic: str = 'SN',
    sided: str = 'two',
    distribution: str = 'normal',
    method: str = 'auto',
    n_sim: int = 200_000,
    seed: Optional[int] = None,
    quadrature_points: int = 2_001,
) -> pd.DataFrame:
    """
    OC-кривая: ``ARL`` в зависимости от сдвига ``δ``.

    Parameters
    ----------
    n : int
        Размер подгруппы.
    k, h : float
        Параметры карты.
    deltas : iterable of float
        Сдвиги в единицах σ (``δ = 0`` — IC).
    statistic : {'SN', 'SR'}, default='SN'
        Знаковая или знаково-ранговая статистика.
    sided : {'upper', 'lower', 'two'}, default='two'
        Тип карты.
    distribution : str, default='normal'
        Распределение процесса.
    method : {'auto', 'exact', 'monte_carlo'}, default='auto'
        Метод распределения ``SR`` при ``δ ≠ 0``: точная квадратура для
        малых ``n``, Монте-Карло для больших (см.
        ``signed_rank_step_distribution_shift``).
    n_sim : int, default=200000
        Число подгрупп для оценки распределения ``SR`` при ``δ ≠ 0``.
    seed : int, optional
        Зерно генератора.
    quadrature_points : int, default=2001
        Число узлов квадратуры для точного метода.

    Returns
    -------
    pandas.DataFrame
        Столбцы ``delta``, ``arl``, ``sdrl``, ``mrl``, ``rejections``
        (1/ARL — частота сигналов на шаг).

    Notes
    -----
    IC-значение ``δ = 0`` для ``SR`` считается по точному распределению
    Уилкоксона, поэтому не зависит от ``n_sim``. При ``method='auto'`` и
    ``n ≤ 20`` OOC-распределение тоже точное (без шума симуляции).
    """
    statistic = statistic.upper()
    if statistic not in {'SN', 'SR'}:
        raise ValueError(f"statistic должен быть 'SN' или 'SR', "
                         f'получено {statistic!r}')

    rows = []
    for index, delta in enumerate(deltas):
        if statistic == 'SN':
            values, probabilities = sign_step_distribution_shift(
                n, delta, distribution
            )
        else:
            values, probabilities = signed_rank_step_distribution_shift(
                n, delta, distribution,
                method=method,
                n_sim=n_sim,
                seed=None if seed is None else seed + index,
                quadrature_points=quadrature_points,
            )

        result = cusum_run_length(
            values, probabilities, k, h, sided=sided
        )
        rows.append({
            'delta': float(delta),
            'arl': result.arl,
            'sdrl': result.sdrl,
            'mrl': result.mrl,
            'rejections': 1.0 / result.arl,
        })

    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
#  Приближённые формулы
# --------------------------------------------------------------------------- #

def _moments(
    step_values: Sequence[float],
    step_probabilities: Sequence[float],
) -> Tuple[float, float]:
    values = np.asarray(step_values, dtype=float)
    probabilities = np.asarray(step_probabilities, dtype=float)
    probabilities = probabilities / probabilities.sum()
    mean = float(values @ probabilities)
    variance = float(((values - mean) ** 2) @ probabilities)
    return mean, sqrt(max(variance, 0.0))


def _siegmund_one_side(
    mean: float,
    sigma: float,
    k: float,
    h: float,
    correction: float,
) -> float:
    drift = mean - k
    if drift <= 0:
        return inf
    boundary = h + correction * sigma
    return float(
        (np.exp(-2.0 * drift * boundary) + 2.0 * drift * boundary - 1.0)
        / (2.0 * drift ** 2)
    )


def siegmund_arl(
    step_values: Sequence[float],
    step_probabilities: Sequence[float],
    k: float,
    h: float,
    *,
    sided: str = 'upper',
    correction: float = 1.166,
) -> float:
    """
    Приближение Сигмунда для ``ARL`` односторонней CUSUM.

    Для дрейфа ``Δ = E[Z] − k > 0``:

        ARL ≈ [exp(−2Δb) + 2Δb − 1] / (2Δ²),   b = h + 1.166·σ

    (Siegmund, 1985; поправка 1.166 — для стандартизованных приращений).
    При ``Δ ≤ 0`` приближение не применимо — возвращается ``inf``.
    Для двусторонней карты стороны объединяются гармонически:
    ``1/ARL = 1/ARL⁺ + 1/ARL⁻``.

    Parameters
    ----------
    step_values, step_probabilities : sequence[float]
        Распределение статистики подгруппы.
    k, h : float
        Параметры карты.
    sided : {'upper', 'lower', 'two'}, default='upper'
        Тип карты.
    correction : float, default=1.166
        Поправка на перескок границы.

    Returns
    -------
    float
        Приближённая ``ARL`` (``inf``, если приближение неприменимо).
    """
    mean, sigma = _moments(step_values, step_probabilities)
    upper = _siegmund_one_side(mean, sigma, k, h, correction)
    lower = _siegmund_one_side(-mean, sigma, k, h, correction)

    if sided == 'upper':
        return upper
    if sided == 'lower':
        return lower
    if not np.isfinite(upper) and not np.isfinite(lower):
        return inf
    if not np.isfinite(upper):
        return lower
    if not np.isfinite(lower):
        return upper
    return 1.0 / (1.0 / upper + 1.0 / lower)


def wald_arl(
    step_values: Sequence[float],
    step_probabilities: Sequence[float],
    k: float,
    h: float,
    *,
    sided: str = 'upper',
) -> float:
    """
    Грубая оценка ``ARL ≈ 1/FAR`` по одному шагу (Вальд/shewhart-подобная).

    ``FAR`` — вероятность того, что одна статистика сразу пересекает границу:
    ``P(Z ≥ k + h)`` для верхней ветви (и симметрично для нижней). Память
    CUSUM игнорируется, поэтому оценка обычно завышает ``ARL``.

    Parameters
    ----------
    step_values, step_probabilities : sequence[float]
        Распределение статистики подгруппы.
    k, h : float
        Параметры карты.
    sided : {'upper', 'lower', 'two'}, default='upper'
        Тип карты.

    Returns
    -------
    float
        ``1/FAR`` (``inf``, если сигнал за один шаг невозможен).
    """
    values = np.asarray(step_values, dtype=float)
    probabilities = np.asarray(step_probabilities, dtype=float)
    probabilities = probabilities / probabilities.sum()

    upper = float(probabilities[values >= k + h].sum())
    lower = float(probabilities[values <= -k - h].sum())

    if sided == 'upper':
        probability = upper
    elif sided == 'lower':
        probability = lower
    else:
        probability = upper + lower

    if probability <= 0:
        return inf
    return 1.0 / min(probability, 1.0)


def compare_arl_methods(
    step_values: Sequence[float],
    step_probabilities: Sequence[float],
    k: float,
    h: float,
    *,
    sided: str = 'two',
) -> pd.DataFrame:
    """
    Таблица «метод → ARL»: точный марковский, Сигмунд, Вальд.

    Returns
    -------
    pandas.DataFrame
        Столбцы ``method``, ``arl``, ``relative_error`` (к точному).
    """
    exact = cusum_run_length(
        step_values, step_probabilities, k, h, sided=sided
    ).arl
    rows = [('markov', exact)]
    rows.append(('siegmund', siegmund_arl(
        step_values, step_probabilities, k, h, sided=sided
    )))
    rows.append(('wald_1_over_far', wald_arl(
        step_values, step_probabilities, k, h, sided=sided
    )))

    records = []
    for method, value in rows:
        if np.isfinite(value) and exact > 0:
            relative_error = abs(value - exact) / exact
        else:
            relative_error = np.nan
        records.append({
            'method': method,
            'arl': value,
            'relative_error': relative_error,
        })
    return pd.DataFrame(records)


# --------------------------------------------------------------------------- #
#  Кэш ARL для сеток подбора
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=4_096)
def _cached_arl_core(
    step_values: Tuple[float, ...],
    step_probabilities: Tuple[float, ...],
    k: float,
    h: float,
    sided: str,
) -> float:
    """ARL по нормированному распределению шага (внутренний кэш)."""
    return _cusum_arl(
        step_values, step_probabilities, k, h, sided=sided
    )


def cached_arl(
    step_values: Sequence[float],
    step_probabilities: Sequence[float],
    k: float,
    h: float,
    *,
    sided: str = 'two',
) -> float:
    """
    ``ARL`` с кэшированием по распределению шага и ``(k, h)``.

    Нужен для сеток подбора 3b.7: при переборе ``(n, k, h)`` одинаковые
    состояния не пересчитываются. Кэш хранит только ``ARL`` (не PMF),
    максимум 4096 записей; сброс — ``clear_run_length_cache()``.

    Parameters
    ----------
    step_values, step_probabilities : sequence[float]
        Распределение статистики подгруппы.
    k, h : float
        Параметры карты.
    sided : {'upper', 'lower', 'two'}, default='two'
        Тип карты.

    Returns
    -------
    float
        ``ARL``.

    Notes
    -----
    Ключ кэша — кортежи значений/вероятностей; распределения нормируются.
    Для ``SN``/``SR`` это компактно (до ``n = 20`` — сотни чисел).
    """
    values = np.asarray(step_values, dtype=float)
    probabilities = np.asarray(step_probabilities, dtype=float)
    total = float(probabilities.sum())
    if total <= 0:
        raise ValueError('Сумма вероятностей должна быть > 0')
    probabilities = probabilities / total
    mask = probabilities > 0
    return _cached_arl_core(
        tuple(values[mask].tolist()),
        tuple(probabilities[mask].tolist()),
        float(k),
        float(h),
        sided,
    )


def run_length_cache_info():
    """Статистика кэша ``cached_arl`` (``hits``/``misses``/``maxsize``)."""
    return _cached_arl_core.cache_info()


def clear_run_length_cache() -> None:
    """Очистить кэш ``cached_arl``."""
    _cached_arl_core.cache_clear()


# --------------------------------------------------------------------------- #
#  Подбор h под номинальный ARL
# --------------------------------------------------------------------------- #

@dataclass
class DesignResult:
    """
    Результат подбора интервала решения ``h``.

    Attributes
    ----------
    h : float
        Найденный интервал решения.
    arl : float
        Достигнутая ``ARL_IC``.
    target_arl : float
        Номинальная ``ARL_IC``.
    k : float
        Референсное значение.
    sided : str
        Тип карты.
    statistic : str
        ``'SN'`` или ``'SR'``.
    n : int, optional
        Размер подгруппы.
    n_evaluated : int
        Сколько вариантов ``h`` просчитано.
    note : str
        Пояснение (достижимость номинала на решётке).
    """

    h: float
    arl: float
    target_arl: float
    k: float
    sided: str
    statistic: str
    n: Optional[int]
    n_evaluated: int
    note: str = ''

    @property
    def relative_error(self) -> float:
        """Относительное отклонение достигнутой ARL от номинала."""
        return abs(self.arl - self.target_arl) / self.target_arl

    def summary(self) -> Dict:
        """Краткая сводка результата подбора."""
        return {
            'statistic': self.statistic,
            'n': self.n,
            'k': self.k,
            'h': self.h,
            'ARL': self.arl,
            'target_ARL': self.target_arl,
            'relative_error': self.relative_error,
            'sided': self.sided,
            'n_evaluated': self.n_evaluated,
            'note': self.note,
        }


def _lattice_step(
    step_values: Sequence[float],
    k: float,
    scale: int = 1_000_000,
) -> float:
    """
    Шаг решётки, на которой лежат состояния CUSUM.

    Состояния — суммы ``Z_t − k``, поэтому шаг задаётся общим делителем
    приращений ``Z_t − k``. Для ``SN``/``SR`` это обычно 2.
    """
    numbers = [abs(float(value) - float(k)) for value in step_values]
    scaled = [int(round(number * scale)) for number in numbers
              if number > 1e-12]
    if not scaled:
        return 1.0
    common = 0
    for number in scaled:
        common = gcd(common, number)
    step = common / scale
    return step if step > 0 else 1.0


def _values_step(
    step_values: Sequence[float],
    scale: int = 1_000_000,
) -> float:
    """
    Шаг решётки значений статистики (НОД разностей соседних значений).

    Для ``SN``/``SR`` равен 2. Используется как основа шага сетки ``k``:
    при целом ``k`` на этой решётке приращения ``Z_t − k`` остаются на
    решётке, и пространство состояний конечно (ср. §4.3.2, стр. 234: для
    нечётного ``n`` берут нечётное ``k``, чтобы ``SN_i − k`` были чётными).
    """
    values = sorted({float(value) for value in step_values})
    if len(values) < 2:
        return 1.0
    differences = [
        int(round((values[index + 1] - values[index]) * scale))
        for index in range(len(values) - 1)
    ]
    common = 0
    for number in differences:
        common = gcd(common, abs(number))
    step = common / scale
    return step if step > 0 else 1.0


def design_h(
    step_values: Sequence[float],
    step_probabilities: Sequence[float],
    target_arl: float,
    k: float,
    *,
    sided: str = 'two',
    statistic: str = '',
    n: Optional[int] = None,
    max_candidates: int = 5_000,
    ic_rule: str = 'conservative',
) -> DesignResult:
    """
    Подобрать ``h`` под номинальную ``ARL_IC``.

    Для дискретной статистики номинал, как правило, недостижим точно, и
    книга предписывает **консервативный** подход: ``h`` выбирается так,
    чтобы достигнутая ``ARL_IC`` была **не больше** номинала (§ 3.2.2,
    стр. 71). Соответственно ``ic_rule='conservative'`` (по умолчанию)
    берёт наибольшее ``h`` с ``ARL ≤ номинала`` — ближайшее снизу; если ни
    одно ``h`` не даёт ``ARL ≤ номинала``, возвращается ближайшее сверху и
    заполняется ``note``. ``ic_rule='nearest'`` — прежнее поведение (минимум
    ``|ARL − номинал|``) без оглядки на сторону.

    ``ARL(h)`` для решётчатой статистики — ступенчатая функция, но
    неубывающая по ``h``. Поиск идёт по индексам решётки: верхняя граница
    расширяется экспоненциально до первого ``ARL ≥`` номинала, затем
    бисекция находит первый такой индекс. Консервативное правило берёт
    предыдущий узел, ``nearest`` — ближайший из соседних. При нарушении
    монотонности или недостижимости сигнала используется прежний линейный
    скан (fallback).

    Parameters
    ----------
    step_values, step_probabilities : sequence[float]
        Распределение статистики подгруппы в IC.
    target_arl : float
        Номинальная ``ARL_IC`` (например, 370 или 500).
    k : float
        Референсное значение.
    sided : {'upper', 'lower', 'two'}, default='two'
        Тип карты.
    statistic, n : optional
        Метаданные для отчёта.
    max_candidates : int, default=5000
        Предохранитель перебора.
    ic_rule : {'conservative', 'nearest'}, default='conservative'
        Правило достижения номинала: ``conservative`` — ``ARL ≤ номинала``
        (книга), ``nearest`` — минимум отклонения по модулю.

    Returns
    -------
    DesignResult
        Найденный ``h``, достигнутая ``ARL`` и отклонение от номинала.

    Notes
    -----
    Номинал может быть недостижим точно (скачок ``ARL``); в этом случае
    возвращается ближайшее по правилу значение и заполняется ``note``.
    """
    if target_arl <= 1:
        raise ValueError(f'Целевая ARL должна быть > 1, получено {target_arl}')
    if k <= 0:
        raise ValueError(
            f'Референсное значение k должно быть > 0, получено {k}'
        )
    if ic_rule not in {'conservative', 'nearest'}:
        raise ValueError(
            "ic_rule должен быть 'conservative' или 'nearest', "
            f'получено {ic_rule!r}'
        )

    values = np.asarray(step_values, dtype=float)
    probabilities = np.asarray(step_probabilities, dtype=float)
    probabilities = probabilities / probabilities.sum()

    step = _lattice_step(values, k)
    evaluations: Dict[int, Optional[float]] = {}

    def arl_at(index: int) -> Optional[float]:
        """ARL на ``h = step·index``; ``None`` — расчёт невозможен."""
        if index in evaluations:
            return evaluations[index]
        try:
            arl = cached_arl(
                values, probabilities, k, step * index, sided=sided
            )
        except ValueError:
            arl = None
        evaluations[index] = arl
        return arl

    def linear_search() -> Tuple[
        Tuple[float, float], Optional[Tuple[float, float]]
    ]:
        """Прежний линейный скан — запасной путь при немонотонном ARL."""
        nearest: Optional[Tuple[float, float]] = None
        conservative: Optional[Tuple[float, float]] = None
        for index in range(1, max_candidates + 1):
            arl = arl_at(index)
            if arl is None:
                continue
            if nearest is None or abs(arl - target_arl) < abs(
                nearest[0] - target_arl
            ):
                nearest = (arl, step * index)
            if arl <= target_arl and (
                conservative is None or arl >= conservative[0]
            ):
                conservative = (arl, step * index)
            if nearest is not None and arl > 2.0 * target_arl and index > 1:
                break
        if nearest is None:
            raise ValueError(
                'Не удалось подобрать h: карта не сигнализирует ни при одном h'
            )
        return nearest, conservative

    def search() -> Tuple[
        Tuple[float, float], Optional[Tuple[float, float]]
    ]:
        """Поиск перехода ARL через номинал по монотонности."""
        first = arl_at(1)
        if first is None:
            # Нет сигнала уже на первом шаге: линейный скан точнее покажет,
            # достижим ли он вообще.
            return linear_search()

        # Экспоненциально расширяем верхнюю границу до первого ARL ≥ номинала.
        upper = 1
        while True:
            arl = arl_at(upper)
            if arl is not None and arl >= target_arl:
                break
            if upper >= max_candidates:
                return linear_search()
            upper = min(upper * 2, max_candidates)
        if arl_at(upper) is None:
            return linear_search()

        # Бисекция: первый индекс с ARL ≥ номинала.
        low, high = 0, upper
        while high - low > 1:
            middle = (low + high) // 2
            arl = arl_at(middle)
            if arl is None or arl >= target_arl:
                high = middle
            else:
                low = middle
        crossing = high

        above = arl_at(crossing)
        below_index = crossing - 1
        below = arl_at(below_index) if below_index >= 1 else None

        # Консервативное правило: наибольшее h с ARL ≤ номинала. Если ARL
        # точно равна номиналу, плато может тянуться дальше точки перехода.
        conservative: Optional[Tuple[float, float]] = None
        if above is not None and above == target_arl:
            index = crossing
            while index < max_candidates and arl_at(index + 1) == target_arl:
                index += 1
            conservative = (target_arl, step * index)
        elif below is not None and below <= target_arl:
            conservative = (below, step * below_index)

        if below is not None and (
            above is None
            or abs(below - target_arl) <= abs(above - target_arl)
        ):
            nearest = (below, step * below_index)
        elif above is not None:
            nearest = (above, step * crossing)
        else:
            return linear_search()
        return nearest, conservative

    best_nearest, best_conservative = search()

    conservative_fallback = False
    if ic_rule == 'conservative' and best_conservative is not None:
        arl, h = best_conservative
    else:
        arl, h = best_nearest
        conservative_fallback = ic_rule == 'conservative'

    notes: List[str] = []
    if conservative_fallback:
        notes.append(
            'Ни одно h не даёт ARL_IC ≤ номинала: возвращено ближайшее '
            'сверху (номинал недостижим на решётке)'
        )
    if abs(arl - target_arl) / target_arl > 0.05:
        notes.append(
            'Номинал недостижим точно: ARL(h) — ступенчатая функция '
            '(решётчатое распределение статистики)'
        )

    return DesignResult(
        h=float(h),
        arl=float(arl),
        target_arl=float(target_arl),
        k=float(k),
        sided=sided,
        statistic=statistic,
        n=n,
        n_evaluated=len(evaluations),
        note='; '.join(notes),
    )


def design_sign_h(
    n: int,
    target_arl: float,
    k: float,
    *,
    sided: str = 'two',
    p: float = 0.5,
    max_candidates: int = 5_000,
    ic_rule: str = 'conservative',
) -> DesignResult:
    """Подобрать ``h`` для CUSUM-SN под номинальную ``ARL_IC``."""
    values, probabilities = sign_step_distribution(n, p)
    return design_h(
        values, probabilities, target_arl, k,
        sided=sided, statistic='SN', n=n,
        max_candidates=max_candidates, ic_rule=ic_rule,
    )


def design_signed_rank_h(
    n: int,
    target_arl: float,
    k: float,
    *,
    sided: str = 'two',
    max_candidates: int = 5_000,
    ic_rule: str = 'conservative',
) -> DesignResult:
    """Подобрать ``h`` для CUSUM-SR под номинальную ``ARL_IC``."""
    values, probabilities = signed_rank_step_distribution(n)
    return design_h(
        values, probabilities, target_arl, k,
        sided=sided, statistic='SR', n=n,
        max_candidates=max_candidates, ic_rule=ic_rule,
    )


# --------------------------------------------------------------------------- #
#  Совместный подбор (k, h) под целевой сдвиг
# --------------------------------------------------------------------------- #

def _shift_step_distribution(
    n: int,
    delta: float,
    statistic: str,
    distribution: str,
    *,
    method: str = 'auto',
    n_sim: int = 200_000,
    seed: Optional[int] = None,
    quadrature_points: int = 2_001,
) -> Tuple[np.ndarray, np.ndarray]:
    """Распределение шага ``Z_t`` при сдвиге ``δ`` для выбранной статистики."""
    statistic = statistic.upper()
    if statistic == 'SN':
        return sign_step_distribution_shift(n, delta, distribution)
    if statistic == 'SR':
        return signed_rank_step_distribution_shift(
            n, delta, distribution,
            method=method, n_sim=n_sim, seed=seed,
            quadrature_points=quadrature_points,
        )
    raise ValueError(
        f"statistic должен быть 'SN' или 'SR', получено {statistic!r}"
    )


def reference_k(
    n: int,
    delta: float,
    *,
    statistic: str = 'SN',
    distribution: str = 'normal',
    method: str = 'auto',
    n_sim: int = 200_000,
    seed: Optional[int] = None,
) -> float:
    """
    Референсное значение ``k`` из целевого сдвига ``δ``: ``k = E[Z_δ]/2``.

    В книге правило ``k = ½δ`` сформулировано для **параметрической** карты на
    нормальной теории: «k is typically chosen relative to the size of the
    shift that we want to detect, that is, k = ½δ» (Lucas, 1985; Montgomery,
    2009; § 3.2.2, стр. 71). Для непараметрических ``SN``/``SR`` книга задаёт
    лишь порядок «``k`` — первым, обычно малым» и отсылает к § 3.2.2
    (§ 4.2.2.3.2, стр. 205; § 4.3.2, стр. 232). Поэтому здесь используется
    **аналог** этого правила, применённый к масштабу статистики: половина её
    ожидаемого приращения при сдвиге ``δ``,

        k = E[Z_δ] / 2,   например E[SN_δ] = n(2p − 1),  p = P(X ≥ μ₀ | δ)

    (``E[SN]`` — табл. 4.1, стр. 193). Это не формула книги, а перенос её
    нормального правила на непараметрическую статистику.

    Parameters
    ----------
    n : int
        Размер подгруппы.
    delta : float
        Целевой сдвиг в единицах σ (``δ ≠ 0``).
    statistic : {'SN', 'SR'}, default='SN'
        Знаковая или знаково-ранговая статистика.
    distribution : str, default='normal'
        Распределение процесса.
    method, n_sim, seed
        Параметры распределения ``SR`` под сдвигом (см.
        ``signed_rank_step_distribution_shift``).

    Returns
    -------
    float
        Половина ожидаемого приращения статистики (``> 0`` при ``δ > 0``).
    """
    if delta == 0:
        raise ValueError(
            'Целевой сдвиг δ должен быть отличен от 0: '
            'в IC E[Z] = 0 и референсное k не определено'
        )
    values, probabilities = _shift_step_distribution(
        n, delta, statistic, distribution,
        method=method, n_sim=n_sim, seed=seed,
    )
    mean, _ = _moments(values, probabilities)
    return mean / 2.0


@dataclass
class DesignKHResult:
    """
    Результат совместного подбора ``(k, h)``.

    Attributes
    ----------
    k, h : float
        Найденные параметры.
    arl_ic : float
        Достигнутая ``ARL_IC`` (в IC, ``δ = 0``).
    arl_ooc : float
        Значение критерия ``ARL_OOC`` — максимум по целевым ``deltas``.
    target_arl : float
        Номинальная ``ARL_IC``.
    deltas : tuple of float
        Целевые сдвиги (критерий — минимум максимального ``ARL_OOC``).
    statistic, sided, distribution : str
        Описание карты.
    n : int, optional
        Размер подгруппы.
    n_k, n_evaluated : int
        Число проверенных ``k`` и суммарно просчитанных ``(k, h)``.
    ooc_by_delta : dict
        ``ARL_OOC`` по каждому целевому сдвигу для выбранного варианта.
    table : pandas.DataFrame
        Полная сетка: ``k``, ``h``, ``arl_ic``, ``arl_ooc``,
        ``relative_error_ic``, ``feasible``.
    note : str
        Пояснение (достижимость, выбранная сетка ``k``).
    """

    k: float
    h: float
    arl_ic: float
    arl_ooc: float
    target_arl: float
    deltas: Tuple[float, ...]
    statistic: str
    sided: str
    distribution: str
    n: Optional[int]
    n_k: int
    n_evaluated: int
    ooc_by_delta: Dict[float, float]
    table: pd.DataFrame
    note: str = ''

    @property
    def relative_error_ic(self) -> float:
        """Относительное отклонение достигнутой ``ARL_IC`` от номинала."""
        return abs(self.arl_ic - self.target_arl) / self.target_arl

    def summary(self) -> Dict:
        """Краткая сводка подбора."""
        return {
            'statistic': self.statistic,
            'n': self.n,
            'k': self.k,
            'h': self.h,
            'ARL_IC': self.arl_ic,
            'ARL_OOC': self.arl_ooc,
            'target_ARL': self.target_arl,
            'relative_error_ic': self.relative_error_ic,
            'deltas': self.deltas,
            'ooc_by_delta': dict(self.ooc_by_delta),
            'sided': self.sided,
            'n_k': self.n_k,
            'n_evaluated': self.n_evaluated,
            'note': self.note,
        }


def _ooc_arl(
    ooc_distributions: Dict[float, Tuple[np.ndarray, np.ndarray]],
    k: float,
    h: float,
    sided: str,
) -> Tuple[float, Dict[float, float]]:
    """``ARL_OOC`` по всем целевым сдвигам; критерий — максимум."""
    by_delta: Dict[float, float] = {}
    for delta, (values, probabilities) in ooc_distributions.items():
        try:
            by_delta[delta] = cached_arl(
                values, probabilities, k, h, sided=sided
            )
        except ValueError:
            by_delta[delta] = inf
    criterion = max(by_delta.values()) if by_delta else inf
    return criterion, by_delta


def design_kh(
    n: int,
    target_arl: float,
    delta: Union[float, Sequence[float]],
    *,
    statistic: str = 'SN',
    sided: str = 'two',
    distribution: str = 'normal',
    k_values: Optional[Iterable[float]] = None,
    k_fractions: Sequence[float] = (0.25, 0.375, 0.5, 0.625, 0.75, 1.0),
    k_step: Optional[float] = None,
    tol: float = 0.10,
    ic_rule: str = 'conservative',
    method: str = 'auto',
    n_sim: int = 200_000,
    seed: Optional[int] = None,
    quadrature_points: int = 2_001,
    max_candidates: int = 5_000,
) -> DesignKHResult:
    """
    Совместный подбор ``(k, h)`` под номинальный ``ARL_IC`` и сдвиг ``δ``.

    Процедура книги (§ 3.2.2, стр. 71–72): ``k`` выбирается первым, затем
    ``h`` — так, чтобы достигался номинальный ``ARL_IC``; оптимальной
    считается пара с минимальным ``ARL_OOC`` при фиксированном ``ARL_IC`` и
    заданном сдвиге ``δ``: «the optimal pair is that for which the ARL_OOC
    is the lowest». Когда ``δ`` задан сеткой, берётся минимум максимума
    ``ARL_OOC`` по сетке (минимакс) — это **обобщение** критерия книги,
    рассчитанного на один сдвиг, а не процедура из книги.

    При ``k_values=None`` кандидаты строятся из ожидаемого приращения
    статистики при сдвиге: ``k = frac · E[Z_δ]`` для ``frac`` из
    ``k_fractions`` (по умолчанию — от ``0.25`` до ``1.0``); это
    непараметрический аналог правила ``k = δ/2`` (§ 3.2.2, стр. 71, см.
    ``reference_k``).

    Parameters
    ----------
    n : int
        Размер подгруппы.
    target_arl : float
        Номинальная ``ARL_IC`` (например, 370 или 500).
    delta : float or sequence of float
        Целевой сдвиг (сдвиги) в единицах σ; ``δ = 0`` недопустим.
    statistic : {'SN', 'SR'}, default='SN'
        Статистика карты.
    sided : {'upper', 'lower', 'two'}, default='two'
        Тип карты.
    distribution : str, default='normal'
        Распределение процесса при сдвиге.
    k_values : iterable of float, optional
        Явная сетка ``k`` (перебивает ``k_fractions``).
    k_fractions : sequence of float, default=(0.25, …, 1.0)
        Доли ``E[Z_δ]`` для автоматической сетки ``k``.
    k_step : float, optional
        Шаг решётки для кандидатов ``k``. По умолчанию берётся шаг решётки
        значений статистики (``2`` для ``SN``/``SR``, т. е. ``k`` целые при
        ``k_step = step/2 = 1``); при слишком узком диапазоне ``k`` шаг
        последовательно уменьшается вдвое. Явная сетка ``k_values``
        используется без привязки к решётке.
    tol : float, default=0.10
        Допуск по относительному отклонению ``ARL_IC`` от номинала: ``k``,
        для которого ``h`` не удаётся настроить в этих пределах, помечается
        недопустимым и не участвует в выборе оптимума.
    ic_rule : {'conservative', 'nearest'}, default='conservative'
        Правило достижения номинала при подборе ``h``: ``conservative`` —
        ``ARL_IC ≤ номинала`` (книга, стр. 71), ``nearest`` — минимум
        отклонения по модулю.
    method, n_sim, seed, quadrature_points
        Параметры распределения ``SR`` под сдвигом.
    max_candidates : int, default=5000
        Предохранитель перебора ``h`` внутри ``design_h``.

    Returns
    -------
    DesignKHResult
        Оптимальная пара ``(k, h)``, её характеристики и полная сетка.

    Notes
    -----
    ``ARL(h)`` при фиксированном ``k`` — ступенчатая функция (решётчатые
    ``SN``/``SR``), поэтому ``ARL_IC`` может быть недостижим точно. При
    ``k``, при котором сигнал недостижим (``k ≥ max|Z|``), вариант
    пропускается. Дизайн — только Case K (``μ₀`` известна). Готовой таблицы
    ``(h, k)`` для ``n = 10`` (Amin, Reynolds & Bakir, 1995, табл. 5) в
    книге нет — на неё дана только ссылка (§ 4.3.2, стр. 232), поэтому
    ``(k, h)`` вычисляются движком.

    Ссылки: § 3.2.2, стр. 67–72 (``k``, минимум ``ARL_OOC``, консервативный
    ``h``); § 4.2.2, стр. 202–206 (определения ур. 4.7–4.12); § 4.3.2,
    стр. 232–238 (порядок подбора и примеры).
    """
    statistic = statistic.upper()
    if statistic not in {'SN', 'SR'}:
        raise ValueError(
            f"statistic должен быть 'SN' или 'SR', получено {statistic!r}"
        )
    if target_arl <= 1:
        raise ValueError(
            f'Целевая ARL должна быть > 1, получено {target_arl}'
        )
    if statistic == 'SR' and n < 2:
        raise ValueError(
            f'Для CUSUM-SR размер подгруппы должен быть ≥ 2, получено {n}'
        )
    if statistic == 'SN' and n < 1:
        raise ValueError(
            f'Для CUSUM-SN размер подгруппы должен быть ≥ 1, получено {n}'
        )
    if tol <= 0:
        raise ValueError(f'Допуск tol должен быть > 0, получено {tol}')

    if isinstance(delta, (int, float, np.floating)):
        deltas: Tuple[float, ...] = (float(delta),)
    else:
        deltas = tuple(float(value) for value in delta)
    if not deltas:
        raise ValueError('Нужен хотя бы один целевой сдвиг δ')
    if any(value == 0 for value in deltas):
        raise ValueError(
            'Целевые сдвиги должны быть отличны от 0 (в IC E[Z] = 0)'
        )

    ic_values, ic_probabilities = _shift_step_distribution(
        n, 0.0, statistic, distribution
    )
    ooc_distributions = {
        value: _shift_step_distribution(
            n, value, statistic, distribution,
            method=method, n_sim=n_sim, seed=seed,
            quadrature_points=quadrature_points,
        )
        for value in deltas
    }

    max_absolute = float(np.max(np.abs(ic_values)))

    if k_values is not None:
        candidates: List[float] = sorted(
            {float(value) for value in k_values}
        )
        grid_note = 'задана явно'
    else:
        means = [
            _moments(*ooc_distributions[value])[0] for value in deltas
        ]
        reference_mean = max(means)
        if reference_mean <= 0:
            raise ValueError(
                'Ожидаемое приращение статистики при сдвиге не положительно; '
                'проверьте знак δ относительно направления карты'
            )
        raw = [
            fraction * reference_mean
            for fraction in k_fractions
            if fraction * reference_mean > 0
        ]
        # Шаг решётки статистики: состояния CUSUM должны лежать на
        # конечной решётке, иначе k «дробит» пространство состояний.
        z_step = _values_step(ic_values)
        if z_step <= 0:
            z_step = 1.0
        if k_step is None or k_step <= 0:
            k_step = z_step / 2.0
        snapped: List[float] = []
        step = k_step
        for _ in range(3):
            snapped = sorted({
                round(value / step) * step
                for value in raw
                if 0 < round(value / step) * step < max_absolute
            })
            if snapped:
                break
            step /= 2.0
        candidates = snapped
        grid_note = (
            'k = frac·E[Z_δ], frac ∈ '
            + ', '.join(f'{fraction:g}' for fraction in k_fractions)
            + f'; шаг решётки k = {step:g}'
        )

    candidates = [value for value in candidates
                  if 0 < value < max_absolute]
    if not candidates:
        raise ValueError(
            'Не осталось допустимых k: все кандидаты вне (0, max|Z|)'
        )

    records: List[Dict[str, Any]] = []
    evaluated = 0
    for k in candidates:
        try:
            design = design_h(
                ic_values, ic_probabilities, target_arl, k,
                sided=sided, statistic=statistic, n=n,
                max_candidates=max_candidates, ic_rule=ic_rule,
            )
        except ValueError:
            records.append({
                'k': k, 'h': np.nan, 'arl_ic': np.inf, 'arl_ooc': np.inf,
                'relative_error_ic': np.inf, 'feasible': False,
            })
            continue

        evaluated += design.n_evaluated
        arl_ooc, _ = _ooc_arl(ooc_distributions, k, design.h, sided)
        relative_error = design.relative_error
        records.append({
            'k': k,
            'h': design.h,
            'arl_ic': design.arl,
            'arl_ooc': arl_ooc,
            'relative_error_ic': relative_error,
            'feasible': bool(relative_error <= tol),
        })

    table = pd.DataFrame(records)
    finite = table[np.isfinite(table['arl_ooc'])]
    feasible = finite[finite['feasible']]

    if not feasible.empty:
        best = feasible.sort_values(
            ['arl_ooc', 'relative_error_ic', 'k']
        ).iloc[0]
        note = ''
    elif not finite.empty:
        best = finite.sort_values(
            ['relative_error_ic', 'arl_ooc', 'k']
        ).iloc[0]
        note = (
            f'Ни один k не даёт ARL_IC в пределах {tol:.0%} от номинала: '
            'выбран вариант с наименьшим отклонением'
        )
    else:
        raise ValueError(
            'Ни один кандидат k не даёт конечной ARL при заданном сдвиге'
        )

    best_k = float(best['k'])
    best_h = float(best['h'])
    _, ooc_by_delta = _ooc_arl(ooc_distributions, best_k, best_h, sided)

    if not note:
        note = grid_note
    else:
        note = f'{note}; сетка k: {grid_note}'

    return DesignKHResult(
        k=best_k,
        h=best_h,
        arl_ic=float(best['arl_ic']),
        arl_ooc=float(best['arl_ooc']),
        target_arl=float(target_arl),
        deltas=deltas,
        statistic=statistic,
        sided=sided,
        distribution=distribution,
        n=n,
        n_k=len(candidates),
        n_evaluated=evaluated,
        ooc_by_delta=ooc_by_delta,
        table=table,
        note=note,
    )


def design_sign_kh(
    n: int,
    target_arl: float,
    delta: Union[float, Sequence[float]],
    *,
    sided: str = 'two',
    distribution: str = 'normal',
    **kwargs: Any,
) -> DesignKHResult:
    """Совместный подбор ``(k, h)`` для CUSUM-SN."""
    return design_kh(
        n, target_arl, delta, statistic='SN', sided=sided,
        distribution=distribution, **kwargs,
    )


def design_signed_rank_kh(
    n: int,
    target_arl: float,
    delta: Union[float, Sequence[float]],
    *,
    sided: str = 'two',
    distribution: str = 'normal',
    **kwargs: Any,
) -> DesignKHResult:
    """Совместный подбор ``(k, h)`` для CUSUM-SR."""
    return design_kh(
        n, target_arl, delta, statistic='SR', sided=sided,
        distribution=distribution, **kwargs,
    )
