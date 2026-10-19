#!/usr/bin/env python3
"""Производительность марковского расчёта RL CUSUM (этап 3b.9).

Разбивает время расчёта на фазы и показывает, как стоимость растёт с ``n``:

* построение пространства состояний (ур. 4.9/4.12, стр. 203–206);
* построение матрицы переходов ``Q``;
* решение системы ``(I − Q)⁻¹`` и развёртка PMF (ур. 3.22–3.24, стр. 112).

Реперные дизайны — ``n = 10`` и ``n = 20``: рис. 4.5 (CUSUM-SN,
``k = 6, h = 4``) и рис. 4.6 (CUSUM-SR, ``k = 41, h = 24``). Для SR
PMF усекается по медиане: ``ARL``/число состояний от усечения не зависят,
а развёртка хвоста при ``ARL ≈ 80 600`` занимает секунды.

Запуск из корня репозитория:
    poetry run python experiments/cusum/04_performance.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")

from nonparametric_charts.utils.plot_style import (  # noqa: E402
    ACCENT,
    PALETTE,
    apply_minimal_latex_style,
    despine,
    math_text,
)
from nonparametric_charts.utils.run_length import (  # noqa: E402
    _prepare_step_distribution,
    _reachable_two_sided_states,
    _reachable_upper_states,
    _run_length_characteristics,
    _transition_matrix_two_sided,
    _transition_matrix_upper,
    sign_step_distribution,
    signed_rank_step_distribution,
)

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "experiments"

REPEATS = 3
SWEEP_N = (5, 10, 15, 20, 25, 30)
SN_DESIGN = (6, 4)            # рис. 4.5: n = 10, k = 6, h = 4
SR_DESIGN = (41, 24)          # рис. 4.6: n = 10, k = 41, h = 24


def phase_timings(
    statistic: str, n: int, k: float, h: float, sided: str,
    max_quantile: float = 0.5,
) -> dict[str, float]:
    """Один расчёт с замером фаз; берётся минимум из ``REPEATS`` прогонов."""
    values, probabilities = (
        sign_step_distribution(n)
        if statistic == 'SN'
        else signed_rank_step_distribution(n)
    )

    best: dict[str, float] | None = None
    for _ in range(REPEATS):
        start = time.perf_counter()
        steps, weights = _prepare_step_distribution(
            values, probabilities, sided
        )
        if sided == 'two':
            states = _reachable_two_sided_states(steps, k, h)
        else:
            states = _reachable_upper_states(steps, k, h)
        states_done = time.perf_counter()

        if sided == 'two':
            matrix = _transition_matrix_two_sided(states, steps, weights, k, h)
        else:
            matrix = _transition_matrix_upper(states, steps, weights, k, h)
        matrix_done = time.perf_counter()

        arl, _, pmf, _, _, _ = _run_length_characteristics(
            matrix, max_quantile=max_quantile
        )
        solved = time.perf_counter()

        sample = {
            'states': float(len(states)),
            'state_time': states_done - start,
            'matrix_time': matrix_done - states_done,
            'solve_time': solved - matrix_done,
            'total_time': solved - start,
            'arl': float(arl),
            'pmf_length': float(pmf.size),
        }
        if best is None or sample['total_time'] < best['total_time']:
            best = sample

    assert best is not None
    return best


def print_design_table() -> list[dict[str, float]]:
    """Таблица по реперным дизайнам ``n = 10, 20``."""
    rows = []
    print('\nРеперные дизайны (минимальное время из '
          f'{REPEATS} прогонов, PMF усечена по медиане):')
    header = (
        f"{'статистика':>10} {'n':>3} {'k':>4} {'h':>4} {'карта':>7} "
        f"{'состояний':>9} {'Q, мс':>8} {'solve, мс':>10} "
        f"{'всего, мс':>10} {'ARL':>12}"
    )
    print(header)
    print('-' * len(header))

    for statistic in ('SN', 'SR'):
        k, h = SN_DESIGN if statistic == 'SN' else SR_DESIGN
        for n in (10, 20):
            for sided, label in (('upper', 'верх.'), ('two', 'двустор.')):
                timings = phase_timings(statistic, n, k, h, sided)
                timings.update({
                    'statistic': statistic, 'n': float(n), 'k': k, 'h': h,
                    'sided': sided,
                })
                rows.append(timings)
                print(
                    f"{statistic:>10} {n:>3} {k:>4g} {h:>4g} {label:>7} "
                    f"{int(timings['states']):>9} "
                    f"{1e3 * timings['matrix_time']:>8.2f} "
                    f"{1e3 * timings['solve_time']:>10.2f} "
                    f"{1e3 * timings['total_time']:>10.2f} "
                    f"{timings['arl']:>12.2f}"
                )
    return rows


def sweep_costs() -> dict[str, dict[str, np.ndarray]]:
    """Стоимость двустороннего расчёта при росте ``n``.

    Параметры карты масштабируются с ``n``: при фиксированных ``k``/``h``
    малые подгруппы вообще не могут дать сигнал (``max|Z| < k``).
    Для ``SN`` взято ``k = h ≈ n/4``, для ``SR`` — доли размаха
    ``n(n+1)/2``. Цель — сравнить рост стоимости, а не конкретный дизайн.
    """
    result: dict[str, dict[str, np.ndarray]] = {}
    for statistic in ('SN', 'SR'):
        totals, states = [], []
        for n in SWEEP_N:
            if statistic == 'SN':
                k = float(max(1, n // 4))
                h = float(max(2, n // 4))
            else:
                maximum = n * (n + 1) / 2
                k = float(max(2, round(0.2 * maximum)))
                h = float(max(4, round(0.4 * maximum)))
            timings = phase_timings(statistic, n, k, h, 'two')
            totals.append(timings['total_time'])
            states.append(timings['states'])
        result[statistic] = {
            'time': np.array(totals),
            'states': np.array(states),
        }
    return result


def plot_costs(costs: dict[str, dict[str, np.ndarray]]) -> Path:
    """Две панели: время и число состояний от ``n``."""
    import matplotlib.pyplot as plt

    apply_minimal_latex_style()
    figure, axes = plt.subplots(1, 2, figsize=(7.2, 3.1))

    colors = {'SN': ACCENT, 'SR': PALETTE[1]}
    labels = {'SN': 'CUSUM-SN', 'SR': 'CUSUM-SR'}

    for statistic in ('SN', 'SR'):
        axes[0].plot(
            SWEEP_N, 1e3 * costs[statistic]['time'],
            marker='o', color=colors[statistic], label=labels[statistic],
        )
        axes[1].plot(
            SWEEP_N, costs[statistic]['states'],
            marker='o', color=colors[statistic], label=labels[statistic],
        )

    axes[0].set_yscale('log')
    axes[0].set_xlabel(math_text('размер подгруппы $n$'))
    axes[0].set_ylabel(math_text('время расчёта, мс'))
    axes[0].set_title(math_text('двусторонняя карта, усечение по медиане'))
    axes[1].set_xlabel(math_text('размер подгруппы $n$'))
    axes[1].set_ylabel(math_text('непоглощающих состояний'))
    axes[1].set_title(math_text('размер матрицы $Q$'))

    for axis in axes:
        axis.legend(frameon=False)
        despine(axis)

    figure.tight_layout()
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / 'cusum_performance.png'
    figure.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(figure)
    return path


def main() -> int:
    print('Производительность марковского расчёта RL CUSUM')
    print('Источник: Chakraborti & Graham (2019), §4.2.2, стр. 202–208; '
          'ур. 3.22–3.24, стр. 112')
    print('Реперы: рис. 4.5 (SN, n=10, k=6, h=4), '
          'рис. 4.6 (SR, n=10, k=41, h=24)')

    print_design_table()
    costs = sweep_costs()

    print('\nРост стоимости по n (двусторонняя карта):')
    print(f"{'n':>3} {'SN, мс':>9} {'SN, сост.':>10} "
          f"{'SR, мс':>9} {'SR, сост.':>10}")
    for index, n in enumerate(SWEEP_N):
        print(
            f"{n:>3} "
            f"{1e3 * costs['SN']['time'][index]:>9.2f} "
            f"{int(costs['SN']['states'][index]):>10} "
            f"{1e3 * costs['SR']['time'][index]:>9.2f} "
            f"{int(costs['SR']['states'][index]):>10}"
        )

    path = plot_costs(costs)
    print('\nВывод: основное время — развёртка PMF (пропорциональна ARL), '
          'а не решение системы: матрица Q мала (единицы-десятки состояний). '
          'Для SN состояния — решётка значений SN (шаг 2) до h, поэтому при '
          'фиксированном h их число не зависит от n (в реперном дизайне '
          '2–3). Для SR размах статистики n(n+1)/2 растёт как n², и число '
          'состояний растёт линейно по n, а вместе с ним — время '
          'построения Q.')
    print(f'\nГрафик сохранён: {path.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
