# src/charts/wilcoxon_distribution.py
"""
Точное распределение статистики Уилкоксона T_n^+ для IC-случая.

Источник: Chakraborti & Graham (2019), Table B, стр. 371-373.

Формат: WILCOXON_DISTRIBUTIONS[n][t] = P(T_n^+ = t)
где t пробегает значения от 0 до n(n+1)/2.

Реализация через динамическое программирование (свёртка):
    T_n^+ = sum_{j=1}^{n} Bernoulli(0.5) * j
Каждое слагаемое принимает значение j с вероятностью 0.5
и 0 с вероятностью 0.5 (независимо).
"""
from __future__ import annotations

import numpy as np


def _build_wilcoxon_pmf(n: int) -> dict:
    """Строит точное распределение T_n^+ через свёртку."""
    max_sum = n * (n + 1) // 2
    pmf = np.zeros(max_sum + 1)
    pmf[0] = 1.0
    for j in range(1, n + 1):
        new_pmf = np.zeros(max_sum + 1)
        new_pmf += 0.5 * pmf          # ранг j не используется
        new_pmf[j:] += 0.5 * pmf[:-j] # ранг j используется
        pmf = new_pmf
    return {t: float(pmf[t]) for t in range(max_sum + 1)}


# Точные распределения для n = 2, ..., 13
WILCOXON_DISTRIBUTIONS = {
    n: _build_wilcoxon_pmf(n) for n in range(2, 14)
}


if __name__ == "__main__":
    # Быстрая проверка
    for n in [4, 5, 10, 13]:
        pmf = WILCOXON_DISTRIBUTIONS[n]
        total = sum(pmf.values())
        mean = sum(t * p for t, p in pmf.items())
        var = sum((t - mean) ** 2 * p for t, p in pmf.items())
        print(f"n = {n:2d}: sum = {total:.6f}, "
              f"E(T) = {mean:.4f} (теор. {n*(n+1)/4:.4f}), "
              f"Var(T) = {var:.4f} (теор. {n*(n+1)*(2*n+1)/24:.4f})")