#!/usr/bin/env python3
"""Эксперимент: точное распределение SR под сдвигом против Монте-Карло.

Проверяет целесообразность точного численного интегрирования
(``signed_rank_step_distribution_exact``) вместо симуляции для малых ``n``:

* ошибка распределения и ARL относительно точного эталона;
* разброс ARL по seed'ам Монте-Карло;
* время расчёта в зависимости от ``n`` и ``n_sim``.

Источник постановки: Chakraborti & Graham (2019), §4.2.2.4, стр. 206–208;
нулевое распределение ``T⁺`` — табл. 4.3. Численный метод — порядковые
статистики ``|X|`` (вывод в докстринге точной функции).

Запуск из корня репозитория:
    poetry run python experiments/cusum/02_sr_exact_vs_mc.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")

from nonparametric_charts.utils.run_length import (  # noqa: E402
    cusum_run_length,
)
from nonparametric_charts.utils.run_length_design import (  # noqa: E402
    signed_rank_step_distribution_shift,
)
from nonparametric_charts.utils.plot_style import (  # noqa: E402
    ACCENT,
    INK,
    PALETTE,
    apply_minimal_latex_style,
    despine,
)

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "experiments"

DELTA = 0.25
N_VALUES = (4, 6, 10, 20, 30)
N_SIM_VALUES = (5_000, 20_000, 100_000, 400_000)
SEEDS = (11, 22, 33, 44, 55)


def full_distribution(values: np.ndarray, probabilities: np.ndarray,
                      n: int) -> np.ndarray:
    """Разложить распределение ``SR`` на полный носитель ``−S…S``."""
    size = n * (n + 1) // 2 + 1
    full = np.zeros(size, dtype=float)
    indices = np.rint((values + n * (n + 1) / 2.0) / 2.0).astype(int)
    full[indices] = probabilities
    return full


def arl(values: np.ndarray, probabilities: np.ndarray,
        n: int) -> float:
    """ARL карты SR с умеренными ``k`` и ``h`` (для сравнения методов).

    ``k`` и ``h`` — доли от максимального ``SR``; при ``δ = 0.25`` это даёт
    ARL порядка 6–50, где ошибка распределения заметна.
    """
    maximum = n * (n + 1) / 2
    k = float(max(2, round(0.3 * maximum)))
    h = float(max(4, round(0.8 * maximum)))
    return cusum_run_length(
        values, probabilities, k, h, sided='two', max_quantile=0.5
    ).arl


def main() -> int:
    print('SR под сдвигом: точная квадратура vs Монте-Карло')
    print('Источник: Chakraborti & Graham (2019), §4.2.2.4, стр. 206–208')
    print(
        f'δ = {DELTA:g}, карта двусторонняя, '
        'k = 0.3·max(SR), h = 0.8·max(SR)'
    )

    header = (
        f"{'n':>3} {'n_sim':>8} {'max|Δp|':>10} {'|ΔARL|':>10} "
        f"{'ARL MC':>10} {'t MC, s':>9}"
    )
    print('\n' + header)
    print('-' * len(header))

    exact_cache: dict[int, tuple[np.ndarray, np.ndarray, float]] = {}
    for n in N_VALUES:
        started = time.perf_counter()
        exact_values, exact_probabilities = (
            signed_rank_step_distribution_shift(
                n, DELTA, 'normal', method='exact'
            )
        )
        exact_time = time.perf_counter() - started
        exact_cache[n] = (
            exact_values, exact_probabilities, exact_time
        )
        exact_arl = arl(exact_values, exact_probabilities, n)
        exact_full = full_distribution(
            exact_values, exact_probabilities, n
        )

        for n_sim in N_SIM_VALUES:
            started = time.perf_counter()
            mc_values, mc_probabilities = (
                signed_rank_step_distribution_shift(
                    n, DELTA, 'normal',
                    method='monte_carlo', n_sim=n_sim, seed=20261019,
                )
            )
            mc_time = time.perf_counter() - started
            mc_full = full_distribution(mc_values, mc_probabilities, n)
            mc_arl = arl(mc_values, mc_probabilities, n)
            difference = np.max(np.abs(mc_full - exact_full))
            print(
                f'{n:3d} {n_sim:8d} {difference:10.2e} '
                f'{abs(mc_arl - exact_arl):10.2e} {mc_arl:10.4f} '
                f'{mc_time:9.4f}'
            )

    print('\nВремя точной квадратуры:')
    for n, (_, _, elapsed) in exact_cache.items():
        print(f'  n = {n:2d}: {elapsed:.4f} с')

    print('\nСходимость квадратуры (n = 20): max|Δp| к сетке 16 001')
    reference_values, reference_probabilities = (
        signed_rank_step_distribution_shift(
            20, DELTA, 'normal', method='exact', quadrature_points=16_001,
        )
    )
    reference_full = full_distribution(
        reference_values, reference_probabilities, 20
    )
    for points in (501, 1_001, 2_001, 4_001, 8_001):
        values, probabilities = signed_rank_step_distribution_shift(
            20, DELTA, 'normal', method='exact',
            quadrature_points=points,
        )
        full = full_distribution(values, probabilities, 20)
        print(
            f'  {points:5d} узлов: '
            f'{np.max(np.abs(full - reference_full)):.2e}'
        )

    print('\nРазброс ARL Монте-Карло по seed (n = 10, n_sim = 20 000):')
    exact_values, exact_probabilities, _ = exact_cache[10]
    exact_arl = arl(exact_values, exact_probabilities, 10)
    mc_arls = []
    for seed in SEEDS:
        values, probabilities = signed_rank_step_distribution_shift(
            10, DELTA, 'normal',
            method='monte_carlo', n_sim=20_000, seed=seed,
        )
        mc_arls.append(arl(values, probabilities, 10))
    print(f'  exact = {exact_arl:.6f}')
    print(
        f'  MC: min = {min(mc_arls):.6f}, max = {max(mc_arls):.6f}, '
        f'std = {np.std(mc_arls):.6f}'
    )

    import matplotlib.pyplot as plt

    apply_minimal_latex_style()
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.6))

    # Слева: ошибка Монте-Карло убывает как 1/√n_sim.
    for index, n in enumerate((4, 10, 20)):
        exact_values, exact_probabilities, _ = exact_cache[n]
        exact_full = full_distribution(
            exact_values, exact_probabilities, n
        )
        errors = []
        for n_sim in N_SIM_VALUES:
            values, probabilities = signed_rank_step_distribution_shift(
                n, DELTA, 'normal',
                method='monte_carlo', n_sim=n_sim, seed=20261019,
            )
            mc_full = full_distribution(values, probabilities, n)
            errors.append(np.max(np.abs(mc_full - exact_full)))
        axes[0].loglog(
            N_SIM_VALUES, errors, marker='o', markersize=3,
            color=ACCENT if index == 0 else PALETTE[index],
            linewidth=1.0, label=rf'$n = {n}$',
        )
    reference = 1.0 / np.sqrt(np.asarray(N_SIM_VALUES, dtype=float))
    axes[0].loglog(
        N_SIM_VALUES, reference, linestyle='--', color=INK,
        linewidth=0.8, label=r'$1/\sqrt{n_{\mathrm{sim}}}$',
    )
    axes[0].set_xlabel(r'$n_{\mathrm{sim}}$')
    axes[0].set_ylabel(r'$\max_s |\hat p_s - p_s|$')
    axes[0].set_title('Ошибка распределения SR', color=INK)
    axes[0].legend(fontsize=8, frameon=False)
    despine(axes[0])

    # Справа: время точной квадратуры растёт с n, MC — от n_sim.
    exact_times = [exact_cache[n][2] for n in N_VALUES]
    axes[1].plot(
        N_VALUES, exact_times, marker='o', markersize=3,
        color=ACCENT, linewidth=1.0, label='точная квадратура',
    )
    mc_times = []
    for n in N_VALUES:
        started = time.perf_counter()
        signed_rank_step_distribution_shift(
            n, DELTA, 'normal',
            method='monte_carlo', n_sim=100_000, seed=20261019,
        )
        mc_times.append(time.perf_counter() - started)
    axes[1].plot(
        N_VALUES, mc_times, marker='s', markersize=3,
        color=INK, linewidth=1.0,
        label=r'Монте-Карло, $n_{\mathrm{sim}} = 10^5$',
    )
    axes[1].set_xlabel(r'$n$')
    axes[1].set_ylabel(r'время, с')
    axes[1].set_title('Время расчёта', color=INK)
    axes[1].legend(fontsize=8, frameon=False)
    despine(axes[1])

    figure.tight_layout()
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / 'cusum_sr_exact_vs_mc.png'
    figure.savefig(path, dpi=200)
    plt.close(figure)
    print(f'\nГрафик сохранён: {path.relative_to(ROOT)}')
    print(
        '\nВывод: для n ≤ 20 точная квадратура даёт ошибку ~1e-8…1e-9 за '
        'доли секунды; Монте-Карло с 10^5 подгрупп — ~1e-3. При n > 20 '
        'по умолчанию остаётся Монте-Карло (method="auto").'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
