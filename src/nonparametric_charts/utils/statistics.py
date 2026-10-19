"""
Общие статистики непараметрических контрольных карт.

Модуль выносит расчёт статистик подгруппы, используемых несколькими картами,
чтобы не дублировать логику:

- знаковая статистика — Шухарт-`SignChart` и `CUSUM-SN`;
- знаково-ранговая статистика — Шухарт-`SignedRankChart` и `CUSUM-SR`.

Знаковая статистика подгруппы:

    SN = n⁺ − n⁻ = 2T − n,   T = n⁺ ~ BIN(n, 0.5) в IC

(Chakraborti & Graham, 2019, § 4.2.1.1, стр. 189–190).

Знаково-ранговая статистика подгруппы:

    SR = Σ_{j=1}^{n} sign(X_j − μ₀) · R_j,   R_j = rank(|X_j − μ₀|)

(Chakraborti & Graham, 2019, § 4.2.1.2, стр. 196–197);
равносильно ``SR = 2 T_n⁺ − n(n+1)/2``.
"""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
from scipy import stats


def sign_counts(values, target_value: float) -> Tuple[int, int, int]:
    """
    Число наблюдений выше, ниже и равных ``target_value``.

    Parameters
    ----------
    values : array-like
        Наблюдения одной подгруппы. Значения ``NaN`` игнорируются.
    target_value : float
        Целевое значение μ₀.

    Returns
    -------
    tuple[int, int, int]
        ``(n⁺, n⁻, n⁰)`` — количество наблюдений ``> μ₀``, ``< μ₀`` и ``= μ₀``.
    """
    arr = np.asarray(values, dtype=float).ravel()
    arr = arr[~np.isnan(arr)]
    positive = int(np.sum(arr > target_value))
    negative = int(np.sum(arr < target_value))
    zero = int(arr.size - positive - negative)
    return positive, negative, zero


def sign_statistic(values, target_value: float) -> int:
    """
    Знаковая статистика подгруппы ``SN = n⁺ − n⁻``.

    Parameters
    ----------
    values : array-like
        Наблюдения одной подгруппы (``NaN`` игнорируются).
    target_value : float
        Целевое значение μ₀.

    Returns
    -------
    int
        Значение ``SN`` в диапазоне ``−n…n``.
    """
    positive, negative, _ = sign_counts(values, target_value)
    return positive - negative


def signed_rank_details(values, target_value: float) -> Dict[str, float]:
    """
    Подробный расчёт знаково-ранговой статистики подгруппы.

    Шаги (Chakraborti & Graham, 2019, § 4.2.1.2, стр. 196–197):
        1. отбросить ``NaN``; 2. отклонения ``d_j = X_j − μ₀``;
        3. исключить нулевые отклонения (теоретически их быть не должно);
        4. ранжировать ``|d_j|`` (метод ``average`` — при связках);
        5. ``SR = Σ sign(d_j) · R_j``.

    Parameters
    ----------
    values : array-like
        Наблюдения одной подгруппы (``NaN`` игнорируются).
    target_value : float
        Целевое значение μ₀.

    Returns
    -------
    dict
        ``n_used``, ``positive``, ``negative``, ``zero``, ``sr``,
        ``sum_pos_ranks``, ``sum_neg_ranks`` и ``T_plus`` (классическая
        статистика знаковых рангов Уилкоксона ``T_n⁺``).
    """
    arr = np.asarray(values, dtype=float).ravel()
    arr = arr[~np.isnan(arr)]
    n = arr.size

    if n == 0:
        return {'n_used': 0, 'positive': 0, 'negative': 0, 'zero': 0,
                'sr': 0.0, 'sum_pos_ranks': 0.0, 'sum_neg_ranks': 0.0,
                'T_plus': 0.0}

    deviations = arr - target_value
    mask_nonzero = deviations != 0
    deviations_nz = deviations[mask_nonzero]
    n_eff = deviations_nz.size

    if n_eff == 0:
        return {'n_used': 0, 'positive': 0, 'negative': 0, 'zero': n,
                'sr': 0.0, 'sum_pos_ranks': 0.0, 'sum_neg_ranks': 0.0,
                'T_plus': 0.0}

    ranks = stats.rankdata(np.abs(deviations_nz), method='average')
    signs = np.sign(deviations_nz)
    signed_ranks = signs * ranks

    sum_pos = float(np.sum(ranks[signs > 0])) if np.any(signs > 0) else 0.0
    sum_neg = float(np.sum(ranks[signs < 0])) if np.any(signs < 0) else 0.0

    return {
        'n_used': n_eff,
        'positive': int(np.sum(signs > 0)),
        'negative': int(np.sum(signs < 0)),
        'zero': int(n - n_eff),
        'sr': float(np.sum(signed_ranks)),
        'sum_pos_ranks': sum_pos,
        'sum_neg_ranks': sum_neg,
        'T_plus': sum_pos,
    }


def signed_rank_statistic(values, target_value: float) -> float:
    """
    Знаково-ранговая статистика подгруппы ``SR = Σ sign(X_j − μ₀)·R_j``.

    Parameters
    ----------
    values : array-like
        Наблюдения одной подгруппы (``NaN`` игнорируются).
    target_value : float
        Целевое значение μ₀.

    Returns
    -------
    float
        Значение ``SR`` в диапазоне ``−S…S``, ``S = n(n+1)/2``.
    """
    return signed_rank_details(values, target_value)['sr']
