"""
Распределение длины серии (run length, RL) для CUSUM-карт.

Модуль реализует точный расчёт характеристик RL для непараметрических
CUSUM-карт по знакам (CUSUM-SN) и знаковым рангам (CUSUM-SR) марковским
методом, а также строит распределения статистик подгруппы.

Теория (Chakraborti & Graham, 2019):

- марковская цепь для CUSUM-SN — § 4.2.2.3.1, ур. 4.9, стр. 203–204;
- марковская цепь для CUSUM-SR — § 4.2.2.4.3, ур. 4.12, стр. 206;
- характеристики RL по ``Q`` — § 3.6.1.2, ур. 3.21–3.24, стр. 112;
- распределение ``SN`` — биномиальное, ``SN = 2T − n``, ``T ~ BIN(n, p)``,
  ``p = P(X ≥ μ₀)``; в IC ``p = 0.5`` (§ 4.2.1.1, стр. 189–190);
- распределение ``SR`` — из распределения статистики знаковых рангов
  Уилкоксона ``T_n⁺``, ``SR = 2T_n⁺ − n(n+1)/2`` (§ 4.2.1.2, стр. 196–197;
  табл. 4.3).

Состояние цепи для верхней односторонней карты:

    S_t = min{h, max{0, S_{t−1} + Z_t − k}},   S_0 = 0,

где ``Z_t`` — статистика подгруппы (``SN_t`` или ``SR_t``). Состояние ``h``
(и всё, что выше) — поглощающее: карта сигнализирует. Для нижней ветви
используется отражение ``Z → −Z``; для двусторонней карты состояние —
пара ``(S⁺, S⁻)``.

Матрица переходов ``Q`` строится по непоглощающим состояниям, затем:

    ARL   = ξ (I − Q)⁻¹ 1
    SDRL  = sqrt(ξ (I + Q)(I − Q)⁻² 1 − ARL²)
    P(N ≤ t) = 1 − ξ Qᵗ 1

(ур. 3.22–3.24, стр. 112), где ``ξ`` — распределение начального состояния
(всегда состояние 0).

Примеры для сверки: 4.8 (``n = 5, k = 1, h = 4`` → ``ARL_IC = 16.62``,
``SDRL_IC = 15.51``) и 4.10 (``n = 4, k = 2, h = 6`` → ``6.81`` и ``6.11``),
стр. 233–240.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Sequence, Tuple

import numpy as np
from scipy import stats

__all__ = [
    'RunLengthResult',
    'sign_step_distribution',
    'signed_rank_step_distribution',
    'cusum_run_length',
    'cusum_sign_run_length',
    'cusum_signed_rank_run_length',
]

#: Точность, с которой состояния цепи считаются совпадающими.
_STATE_DECIMALS = 10
#: Защита от взрыва числа состояний (например, при иррациональном ``k``).
_MAX_STATES = 20_000


# --------------------------------------------------------------------------- #
#  Распределения статистики подгруппы
# --------------------------------------------------------------------------- #

def sign_step_distribution(
    n: int,
    p: float = 0.5,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Распределение знаковой статистики ``SN = 2T − n``.

    Parameters
    ----------
    n : int
        Размер подгруппы (``n ≥ 1``).
    p : float, default=0.5
        Вероятность ``P(X ≥ μ₀)``. В IC ``p = 0.5``; ``p ≠ 0.5`` задаёт
        сдвиг процесса (OOC).

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray]
        Значения ``SN`` (по возрастанию) и соответствующие вероятности.

    Notes
    -----
    ``T ~ BIN(n, p)`` (Chakraborti & Graham, 2019, § 4.2.1.1, стр. 189–190).
    """
    if n < 1:
        raise ValueError(f'Размер подгруппы должен быть ≥ 1, получено {n}')
    if not 0.0 <= p <= 1.0:
        raise ValueError(f'Вероятность p должна быть в [0, 1], получено {p}')

    t = np.arange(n + 1)
    values = 2.0 * t - n
    probabilities = stats.binom.pmf(t, n, p)
    return values, probabilities


def signed_rank_step_distribution(n: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Распределение знаково-ранговой статистики ``SR`` в IC.

    Parameters
    ----------
    n : int
        Размер подгруппы (``n ≥ 2``).

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray]
        Значения ``SR`` (по возрастанию) и вероятности.

    Notes
    -----
    ``SR = 2T_n⁺ − n(n+1)/2``, где ``T_n⁺`` — статистика знаковых рангов
    Уилкоксона (Chakraborti & Graham, 2019, § 4.2.1.2, стр. 196–197).
    Нулевое распределение ``T_n⁺`` — сумма случайного подмножества рангов
    ``{1, …, n}``; считается точной динамикой по подмножествам (табл. 4.3).

    Для OOC-расчётов нужно распределение ``T_n⁺`` при сдвиге; оно зависит от
    функции распределения и будет добавлено отдельным шагом (этап 3b.5).
    """
    if n < 2:
        raise ValueError(
            'Знаково-ранговая статистика требует n ≥ 2, '
            f'получено {n}'
        )

    # counts[s] — число подмножеств {1..n} с суммой s (целые, точные).
    counts = [0] * (n * (n + 1) // 2 + 1)
    counts[0] = 1
    for rank in range(1, n + 1):
        for total in range(len(counts) - 1, rank - 1, -1):
            counts[total] += counts[total - rank]

    total_subsets = 2 ** n
    probabilities = np.array(counts, dtype=float) / total_subsets
    t_plus = np.arange(len(counts), dtype=float)
    values = 2.0 * t_plus - n * (n + 1) / 2.0
    return values, probabilities


# --------------------------------------------------------------------------- #
#  Результат расчёта
# --------------------------------------------------------------------------- #

@dataclass
class RunLengthResult:
    """
    Характеристики распределения длины серии.

    Attributes
    ----------
    arl : float
        Средняя длина серии ``E(N)``.
    sdrl : float
        Стандартное отклонение ``SD(N)``.
    mrl : int
        Медиана распределения RL (``MRL``).
    percentiles : dict[float, int]
        Перцентили распределения RL.
    pmf, cdf : numpy.ndarray
        Усечённые PMF и CDF; ``pmf[t−1] = P(N = t)``.
    states : numpy.ndarray
        Непоглощающие состояния цепи (для односторонней карты) либо
        закодированные пары ``(S⁺, S⁻)`` (для двусторонней).
    n_states : int
        Число непоглощающих состояний.
    method : str
        Метод расчёта (``'markov'``).
    truncated : bool
        ``True``, если хвост распределения отсечён по ``max_quantile``.
    k, h : float
        Параметры карты.
    sided : str
        ``'upper'``, ``'lower'`` или ``'two'``.
    """

    arl: float
    sdrl: float
    mrl: int
    percentiles: Dict[float, int]
    pmf: np.ndarray
    cdf: np.ndarray
    states: np.ndarray
    n_states: int
    method: str
    truncated: bool
    k: float
    h: float
    sided: str
    metadata: Dict[str, float] = field(default_factory=dict)

    def percentile(self, q: float) -> int:
        """Перцентиль уровня ``q`` (наименьшее ``t`` с ``F(t) ≥ q``)."""
        if not 0.0 < q < 1.0:
            raise ValueError(f'Уровень перцентиля должен быть в (0, 1), получено {q}')
        return _percentile_from_cdf(self.cdf, q)

    def summary(self) -> Dict:
        """Краткая сводка характеристик RL."""
        return {
            'method': self.method,
            'sided': self.sided,
            'k': self.k,
            'h': self.h,
            'ARL': self.arl,
            'SDRL': self.sdrl,
            'MRL': self.mrl,
            'percentiles': dict(self.percentiles),
            'n_states': self.n_states,
            'truncated': self.truncated,
            **self.metadata,
        }


def _percentile_from_cdf(cdf: np.ndarray, q: float) -> int:
    """Наименьшее ``t`` (1-based) с ``cdf[t−1] ≥ q``."""
    index = int(np.searchsorted(cdf, q, side='left'))
    if index >= len(cdf):  # хвост отсечён — возвращаем последнюю точку
        return len(cdf)
    return index + 1


# --------------------------------------------------------------------------- #
#  Построение состояний и матрицы переходов
# --------------------------------------------------------------------------- #

def _normalize_state(value: float) -> float:
    """Округление состояния, чтобы суммы с плавающей точкой совпадали."""
    normalized = round(float(value), _STATE_DECIMALS)
    return 0.0 if normalized == 0 else normalized


def _reachable_upper_states(
    step_values: Sequence[float],
    k: float,
    h: float,
) -> list[float]:
    """Незамкнутое множество непоглощающих состояний верхней ветви."""
    start = 0.0
    states = {start}
    queue = [start]

    while queue:
        state = queue.pop()
        for value in step_values:
            candidate = max(0.0, state + value - k)
            if candidate >= h:
                continue
            candidate = _normalize_state(candidate)
            if candidate not in states:
                if len(states) >= _MAX_STATES:
                    raise ValueError(
                        'Слишком большое пространство состояний '
                        f'(> {_MAX_STATES}); проверьте k и h'
                    )
                states.add(candidate)
                queue.append(candidate)

    return sorted(states)


def _reachable_two_sided_states(
    step_values: Sequence[float],
    k: float,
    h: float,
) -> list[Tuple[float, float]]:
    """Множество непоглощающих состояний двусторонней карты ``(S⁺, S⁻)``."""
    start = (0.0, 0.0)
    states = {start}
    queue = [start]

    while queue:
        upper, lower = queue.pop()
        for value in step_values:
            new_upper = max(0.0, upper + value - k)
            new_lower = min(0.0, lower + value + k)
            if new_upper >= h or new_lower <= -h:
                continue
            candidate = (_normalize_state(new_upper),
                         _normalize_state(new_lower))
            if candidate not in states:
                if len(states) >= _MAX_STATES:
                    raise ValueError(
                        'Слишком большое пространство состояний '
                        f'(> {_MAX_STATES}); проверьте k и h'
                    )
                states.add(candidate)
                queue.append(candidate)

    return sorted(states)


def _transition_matrix_upper(
    states: Sequence[float],
    step_values: np.ndarray,
    step_probabilities: np.ndarray,
    k: float,
    h: float,
) -> np.ndarray:
    """Матрица ``Q`` для верхней односторонней карты."""
    index = {state: i for i, state in enumerate(states)}
    size = len(states)
    matrix = np.zeros((size, size), dtype=float)

    for i, state in enumerate(states):
        for value, probability in zip(step_values, step_probabilities):
            if probability == 0.0:
                continue
            candidate = max(0.0, state + value - k)
            if candidate >= h:
                continue
            matrix[i, index[_normalize_state(candidate)]] += probability

    return matrix


def _transition_matrix_two_sided(
    states: Sequence[Tuple[float, float]],
    step_values: np.ndarray,
    step_probabilities: np.ndarray,
    k: float,
    h: float,
) -> np.ndarray:
    """Матрица ``Q`` для двусторонней карты (состояние — пара ветвей)."""
    index = {state: i for i, state in enumerate(states)}
    size = len(states)
    matrix = np.zeros((size, size), dtype=float)

    for i, (upper, lower) in enumerate(states):
        for value, probability in zip(step_values, step_probabilities):
            if probability == 0.0:
                continue
            new_upper = max(0.0, upper + value - k)
            new_lower = min(0.0, lower + value + k)
            if new_upper >= h or new_lower <= -h:
                continue
            candidate = (_normalize_state(new_upper),
                         _normalize_state(new_lower))
            matrix[i, index[candidate]] += probability

    return matrix


# --------------------------------------------------------------------------- #
#  Характеристики RL по матрице Q
# --------------------------------------------------------------------------- #

def _run_length_characteristics(
    matrix: np.ndarray,
    *,
    max_quantile: float = 0.9999,
    quantiles: Iterable[float] = (0.05, 0.25, 0.5, 0.75, 0.95),
    max_t: int = 2_000_000,
) -> Tuple[float, float, np.ndarray, np.ndarray, Dict[float, int], bool]:
    """
    ARL, SDRL и усечённое распределение RL по матрице ``Q``.

    Используются ур. 3.22–3.24 (Chakraborti & Graham, 2019, стр. 112).
    """
    size = matrix.shape[0]
    identity = np.eye(size)
    ones = np.ones(size)
    start = np.zeros(size)
    start[0] = 1.0

    # (I − Q) 1 — вероятность поглощения за один шаг из каждого состояния.
    absorbing_probability = (identity - matrix) @ ones

    # Если из начального состояния нельзя дойти до поглощающего, ARL
    # бесконечна, а (I − Q) вырождена. Проверяем достижимость поглощения
    # по обратному графу.
    can_absorb = absorbing_probability > 0
    changed = True
    while changed:
        changed = False
        for i in range(size):
            if can_absorb[i]:
                continue
            if np.any((matrix[i] > 0) & can_absorb):
                can_absorb[i] = True
                changed = True
    if not can_absorb[0]:
        raise ValueError(
            'Карта не сигнализирует при данных k и h: ARL бесконечна '
            '(поглощающее состояние недостижимо из начального)'
        )

    # ARL = ξ (I − Q)⁻¹ 1
    fundamental = np.linalg.solve(identity - matrix, ones)
    arl = float(start @ fundamental)

    # E(N²) = ξ (I + Q)(I − Q)⁻² 1
    second_moment_matrix = np.linalg.solve(identity - matrix, fundamental)
    second_moment = float(start @ ((identity + matrix) @ second_moment_matrix))
    sdrl = float(np.sqrt(max(0.0, second_moment - arl ** 2)))

    # PMF: P(N = t) = ξ Q^{t−1} (I − Q) 1
    vector = start.copy()
    probabilities = []
    cumulative = []

    current = 0.0
    truncated = True
    for _ in range(max_t):
        probability = float(vector @ absorbing_probability)
        probability = min(max(probability, 0.0), 1.0)
        current = min(current + probability, 1.0)
        probabilities.append(probability)
        cumulative.append(current)
        if current >= max_quantile:
            truncated = False
            break
        vector = vector @ matrix

    pmf = np.asarray(probabilities, dtype=float)
    cdf = np.asarray(cumulative, dtype=float)

    percentiles = {
        float(q): _percentile_from_cdf(cdf, q) for q in quantiles
    }
    return arl, sdrl, pmf, cdf, percentiles, truncated


# --------------------------------------------------------------------------- #
#  Публичный интерфейс
# --------------------------------------------------------------------------- #

def cusum_run_length(
    step_values: Sequence[float],
    step_probabilities: Sequence[float],
    k: float,
    h: float,
    *,
    sided: str = 'two',
    max_quantile: float = 0.9999,
) -> RunLengthResult:
    """
    Точное распределение длины серии CUSUM для дискретной статистики.

    Parameters
    ----------
    step_values, step_probabilities : sequence[float]
        Носитель и вероятности статистики подгруппы ``Z_t``.
    k : float
        Референсное значение (``> 0``).
    h : float
        Интервал решения (``> 0``).
    sided : {'upper', 'lower', 'two'}, default='two'
        Односторонняя верхняя/нижняя либо двусторонняя карта.
    max_quantile : float, default=0.9999
        До какого уровня считается PMF (хвост дальше отсекается).

    Returns
    -------
    RunLengthResult
        ``ARL``, ``SDRL``, ``MRL``, перцентили, PMF/CDF.

    Notes
    -----
    Уравнение состояния: ур. 4.9 (SN, стр. 203) / 4.12 (SR, стр. 206).
    Характеристики RL: ур. 3.22–3.24 (стр. 112).
    """
    if k <= 0:
        raise ValueError(f'Референсное значение k должно быть > 0, получено {k}')
    if h <= 0:
        raise ValueError(f'Интервал решения h должно быть > 0, получено {h}')
    if sided not in {'upper', 'lower', 'two'}:
        raise ValueError(
            "sided должен быть 'upper', 'lower' или 'two', "
            f'получено {sided!r}'
        )

    values = np.asarray(step_values, dtype=float)
    probabilities = np.asarray(step_probabilities, dtype=float)

    if values.shape != probabilities.shape:
        raise ValueError('step_values и step_probabilities должны быть одной длины')
    if values.ndim != 1 or values.size == 0:
        raise ValueError('step_values должен быть непустым одномерным массивом')
    if np.any(probabilities < 0):
        raise ValueError('Вероятности не могут быть отрицательными')

    total = float(probabilities.sum())
    if total <= 0:
        raise ValueError('Сумма вероятностей должна быть > 0')
    probabilities = probabilities / total

    mask = probabilities > 0
    values = values[mask]
    probabilities = probabilities[mask]

    # Нижняя ветвь — отражение статистики: Z → −Z.
    if sided == 'lower':
        values = -values

    if sided == 'two':
        states = _reachable_two_sided_states(values, k, h)
        matrix = _transition_matrix_two_sided(
            states, values, probabilities, k, h
        )
        state_array = np.asarray(states, dtype=float)
    else:
        states = _reachable_upper_states(values, k, h)
        matrix = _transition_matrix_upper(states, values, probabilities, k, h)
        state_array = np.asarray(states, dtype=float)

    arl, sdrl, pmf, cdf, percentiles, truncated = _run_length_characteristics(
        matrix, max_quantile=max_quantile
    )

    return RunLengthResult(
        arl=arl,
        sdrl=sdrl,
        mrl=percentiles[0.5],
        percentiles=percentiles,
        pmf=pmf,
        cdf=cdf,
        states=state_array,
        n_states=len(states),
        method='markov',
        truncated=truncated,
        k=float(k),
        h=float(h),
        sided=sided,
        metadata={
            'step_min': float(values.min()),
            'step_max': float(values.max()),
            'step_span': float(values.max() - values.min()),
        },
    )


def cusum_sign_run_length(
    n: int,
    k: float,
    h: float,
    *,
    sided: str = 'two',
    p: float = 0.5,
    max_quantile: float = 0.9999,
) -> RunLengthResult:
    """
    Распределение длины серии CUSUM-SN.

    Parameters
    ----------
    n : int
        Размер подгруппы (``n ≥ 1``).
    k, h : float
        Референсное значение и интервал решения.
    sided : {'upper', 'lower', 'two'}, default='two'
        Тип карты.
    p : float, default=0.5
        ``P(X ≥ μ₀)``; в IC ``p = 0.5``.
    max_quantile : float, default=0.9999
        Уровень усечения хвоста.

    Returns
    -------
    RunLengthResult
        Характеристики RL. Ссылки: ур. 4.9 (стр. 203), ур. 3.22–3.24
        (стр. 112).
    """
    values, probabilities = sign_step_distribution(n, p)
    result = cusum_run_length(
        values, probabilities, k, h, sided=sided, max_quantile=max_quantile
    )
    result.metadata.update({'n': float(n), 'p': float(p), 'statistic': 'SN'})
    return result


def cusum_signed_rank_run_length(
    n: int,
    k: float,
    h: float,
    *,
    sided: str = 'two',
    max_quantile: float = 0.9999,
) -> RunLengthResult:
    """
    Распределение длины серии CUSUM-SR (в IC).

    Parameters
    ----------
    n : int
        Размер подгруппы (``n ≥ 2``).
    k, h : float
        Референсное значение и интервал решения.
    sided : {'upper', 'lower', 'two'}, default='two'
        Тип карты.
    max_quantile : float, default=0.9999
        Уровень усечения хвоста.

    Returns
    -------
    RunLengthResult
        Характеристики RL. Ссылки: ур. 4.12 (стр. 206), ур. 3.22–3.24
        (стр. 112), распределение ``T_n⁺`` — табл. 4.3.
    """
    values, probabilities = signed_rank_step_distribution(n)
    result = cusum_run_length(
        values, probabilities, k, h, sided=sided, max_quantile=max_quantile
    )
    result.metadata.update({'n': float(n), 'statistic': 'SR'})
    return result
