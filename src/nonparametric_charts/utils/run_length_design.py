"""
Дизайн CUSUM-карт по знакам и знаковым рангам и OC-кривые.

Модуль дополняет точный расчёт длины серии (`utils/run_length.py`):

- распределения статистики подгруппы при сдвиге процесса (OOC);
- OC-кривые ``ARL(δ)`` для разных распределений;
- подбор интервала решения ``h`` под номинальный ``ARL_IC``;
- приближённые формулы (Сигмунд, Вальд/``1/FAR``) для быстрых оценок.

Источник: Chakraborti & Graham (2019)
- выбор ``(k, h)`` — § 3.2.2, стр. 67; § 4.2.2, стр. 202–203;
- симуляция RL — § 4.2.2.3.2/§ 4.2.2.4.3, стр. 205/207–208;
- ARL и FAR — § 2.1.12, стр. 39–50.

Терминология: ``δ`` — сдвиг положения процесса в единицах стандартного
отклонения; ``μ₀`` — целевое значение (медиана в IC).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import factorial, gcd, inf, sqrt
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from scipy.integrate import cumulative_trapezoid

from nonparametric_charts.utils.run_length import (
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
#  Кэш ARL для сеток дизайна
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
    return float(
        cusum_run_length(
            step_values, step_probabilities, k, h, sided=sided,
            max_quantile=0.5,
        ).arl
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

    Нужен для сеток дизайна 3b.7: при переборе ``(n, k, h)`` одинаковые
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
        """Краткая сводка результата дизайна."""
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
) -> DesignResult:
    """
    Подобрать ``h`` под номинальную ``ARL_IC``.

    ``ARL(h)`` для решётчатой статистики — ступенчатая функция: при
    переходе ``h`` через достижимое состояние меняется размер пространства
    состояний. Поэтому вместо чистой бисекции перебираются критические
    значения ``h`` (кратные шагу решётки) и выбирается вариант с минимальным
    отклонением от номинала.

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

    Returns
    -------
    DesignResult
        Ближайший достижимый дизайн.

    Notes
    -----
    Номинал может быть недостижим точно (скачок ``ARL``); в этом случае
    возвращается ближайшее значение и заполняется ``note``.
    """
    if target_arl <= 1:
        raise ValueError(f'Целевая ARL должна быть > 1, получено {target_arl}')
    if k <= 0:
        raise ValueError(
            f'Референсное значение k должно быть > 0, получено {k}'
        )

    values = np.asarray(step_values, dtype=float)
    probabilities = np.asarray(step_probabilities, dtype=float)
    probabilities = probabilities / probabilities.sum()

    step = _lattice_step(values, k)
    best: Optional[Tuple[float, float]] = None

    for index in range(1, max_candidates + 1):
        h = step * index
        try:
            arl = cached_arl(
                values, probabilities, k, h, sided=sided
            )
        except ValueError:
            continue

        if best is None or abs(arl - target_arl) < abs(best[0] - target_arl):
            best = (arl, h)

        # Ступенчатая функция: как только ARL заметно превысила номинал
        # и начала расти, дальнейшие h только ухудшают приближение.
        if best is not None and arl > 2.0 * target_arl and index > 1:
            break

    if best is None:
        raise ValueError(
            'Не удалось подобрать h: карта не сигнализирует ни при одном h'
        )

    arl, h = best
    note = ''
    if abs(arl - target_arl) / target_arl > 0.05:
        note = (
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
        n_evaluated=min(index, max_candidates),
        note=note,
    )


def design_sign_h(
    n: int,
    target_arl: float,
    k: float,
    *,
    sided: str = 'two',
    p: float = 0.5,
    max_candidates: int = 5_000,
) -> DesignResult:
    """Подобрать ``h`` для CUSUM-SN под номинальную ``ARL_IC``."""
    values, probabilities = sign_step_distribution(n, p)
    return design_h(
        values, probabilities, target_arl, k,
        sided=sided, statistic='SN', n=n,
        max_candidates=max_candidates,
    )


def design_signed_rank_h(
    n: int,
    target_arl: float,
    k: float,
    *,
    sided: str = 'two',
    max_candidates: int = 5_000,
) -> DesignResult:
    """Подобрать ``h`` для CUSUM-SR под номинальную ``ARL_IC``."""
    values, probabilities = signed_rank_step_distribution(n)
    return design_h(
        values, probabilities, target_arl, k,
        sided=sided, statistic='SR', n=n,
        max_candidates=max_candidates,
    )
