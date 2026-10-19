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
from math import gcd, inf, sqrt
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from nonparametric_charts.utils.run_length import (
    cusum_run_length,
    sign_step_distribution,
    signed_rank_step_distribution,
)

__all__ = [
    'StandardizedDistribution',
    'sign_step_distribution_shift',
    'signed_rank_step_distribution_shift',
    'oc_curve',
    'siegmund_arl',
    'wald_arl',
    'compare_arl_methods',
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

    def rvs(self, size, rng: np.random.Generator) -> np.ndarray:
        """Выборка из стандартизованного распределения."""
        sample = self._dist.rvs(size=size, random_state=rng)
        return (np.asarray(sample) - self._center) / self._sd


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


def signed_rank_step_distribution_shift(
    n: int,
    delta: float,
    distribution: str = 'normal',
    *,
    n_sim: int = 200_000,
    seed: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Распределение ``SR`` при сдвиге процесса на ``δ`` (Монте-Карло).

    Для ``δ = 0`` возвращается точное нулевое распределение Уилкоксона
    (табл. 4.3). Для ``δ ≠ 0`` распределение зависит от функции
    распределения, поэтому статистика моделируется: ``n_sim`` подгрупп,
    ранги ``|X_j|`` внутри подгруппы.

    Parameters
    ----------
    n : int
        Размер подгруппы (``n ≥ 2``).
    delta : float
        Сдвиг в единицах σ.
    distribution : str, default='normal'
        Симметричное (для SR) распределение процесса.
    n_sim : int, default=200000
        Число моделируемых подгрупп.
    seed : int, optional
        Зерно генератора.

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray]
        Значения ``SR`` и вероятности.

    Notes
    -----
    Для ``δ = 0`` симуляция не нужна — используется точное распределение
    ``T_n⁺``. Для ``δ ≠ 0`` это оценка; её ошибка убывает как ``1/√n_sim``.
    """
    if delta == 0:
        return signed_rank_step_distribution(n)

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
    n_sim: int = 200_000,
    seed: Optional[int] = None,
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
    n_sim : int, default=200000
        Число подгрупп для оценки распределения ``SR`` при ``δ ≠ 0``.
    seed : int, optional
        Зерно генератора.

    Returns
    -------
    pandas.DataFrame
        Столбцы ``delta``, ``arl``, ``sdrl``, ``mrl``, ``rejections``
        (1/ARL — частота сигналов на шаг).

    Notes
    -----
    IC-значение ``δ = 0`` для ``SR`` считается по точному распределению
    Уилкоксона, поэтому не зависит от ``n_sim``.
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
                n_sim=n_sim,
                seed=None if seed is None else seed + index,
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
            arl = cusum_run_length(
                values, probabilities, k, h,
                sided=sided, max_quantile=0.5,
            ).arl
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
