#!/usr/bin/env python3
"""Время подбора ``(k, h)``: шаг сетки, размер подгруппы, цель и допуск.

Эксперимент A3 этапа 3b.13. Для каждого случая ``design_kh`` выполняется
``REPEATS = 5`` раз с очисткой кэша ``ARL`` («холодный» прогон), затем один
раз без очистки («тёплый»). Точный марковский расчёт детерминирован,
поэтому разброс по времени — единственная измеряемая величина; медиана и
``[min, max]`` показывают устойчивость.

Факторы:

* шаг сетки ``k`` (1, 0.5, 0.1) — как дробление сетки меняет стоимость;
* размер подгруппы ``n`` (10, 14, 20) при шаге 0.1;
* номинальная ``ARL_IC`` (370, 500, 750);
* допуск ``tol`` (5 %, 10 %, 20 %);
* статистика: ``SN`` и (в полном режиме) ``SR``.

Источник метода: Chakraborti & Graham (2019), §3.2.2, стр. 67–72;
§4.2.2, стр. 202–206; §4.3.2, стр. 232–238. Стоимость определяется числом
состояний марковской цепи: с дроблением ``k`` шаг ``gcd{|Z_t − k|}``
уменьшается, а матрица ``Q`` растёт (ур. 4.9, стр. 203–204).

Запуск из корня репозитория:
    poetry run python experiments/cusum/08_search_time.py
    NPC_EXPERIMENT_FULL=1 poetry run python experiments/cusum/08_search_time.py
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

# Замеры времени — без вложенного BLAS-параллелизма.
for _variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                  'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(_variable, '1')

import numpy as np  # noqa: E402

sys.path.insert(0, "src")

from nonparametric_charts.utils.plot_style import (  # noqa: E402
    ACCENT,
    INK,
    PALETTE,
    apply_minimal_latex_style,
    despine,
    math_text,
)
from nonparametric_charts.utils.run_length_design import (  # noqa: E402
    clear_run_length_cache,
    design_kh,
)

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "experiments"

REPEATS = 5
TARGET = 500.0
FULL = os.environ.get("NPC_EXPERIMENT_FULL", "0") == "1"


class Tee:
    """Дублировать вывод в консоль и в файл."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data: str) -> int:
        for stream in self.streams:
            stream.write(data)
        return len(data)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()


def timed_case(
    *,
    statistic: str = 'SN',
    n: int,
    delta: float = 1.0,
    target: float = TARGET,
    k_step: float = 0.1,
    tol: float = 0.10,
) -> Dict[str, object]:
    """Пять «холодных» прогонов и один «тёплый» для одного случая."""
    times: List[float] = []
    result = None
    for _ in range(REPEATS):
        clear_run_length_cache()
        start = time.perf_counter()
        result = design_kh(
            n, target, delta, statistic=statistic, sided='two',
            k_step=k_step, tol=tol,
        )
        times.append(time.perf_counter() - start)
    assert result is not None

    start = time.perf_counter()
    design_kh(
        n, target, delta, statistic=statistic, sided='two',
        k_step=k_step, tol=tol,
    )
    warm = time.perf_counter() - start

    return {
        'statistic': statistic, 'n': n, 'delta': delta, 'target': target,
        'k_step': k_step, 'tol': tol,
        'k': result.k, 'h': result.h, 'arl_ic': result.arl_ic,
        'time': float(np.median(times)),
        'time_min': float(np.min(times)),
        'time_max': float(np.max(times)),
        'time_warm': warm,
        'n_evaluated': result.n_evaluated,
    }


def print_row(row: Dict[str, object]) -> None:
    """Одна строка таблицы времени."""
    print(
        f"{row['statistic']:>4} {row['n']:>3} {row['k_step']:>6.2f} "
        f"{row['target']:>5g} {row['tol']:>5.0%} "
        f"{row['k']:>6.2f} {row['h']:>7.2f} {row['arl_ic']:>9.2f} "
        f"{row['time']:>8.3f} "
        f"{row['time_min']:>7.3f}–{row['time_max']:<7.3f} "
        f"{row['time_warm']:>8.4f} {row['n_evaluated']:>8}"
    )


def run_step_sweep() -> List[Dict[str, object]]:
    """Время от шага сетки ``k`` (SN, δ=1)."""
    print('\nA3.1. Время от шага сетки k (SN, δ=1, ARL_IC=500)')
    header = (
        f"{'стат':>4} {'n':>3} {'шаг k':>6} {'цель':>5} {'tol':>5} "
        f"{'k':>6} {'h':>7} {'ARL_IC':>9} {'t, с':>8} "
        f"{'[min,max]':>16} {'тёпл.,с':>8} {'вычисл.':>8}"
    )
    print(header)
    print('-' * len(header))
    rows: List[Dict[str, object]] = []
    nodes = (10, 14, 20) if FULL else (10, 14)
    steps = (1.0, 0.5, 0.25, 0.1) if FULL else (1.0, 0.5, 0.1)
    for n in nodes:
        for k_step in steps:
            row = timed_case(n=n, k_step=k_step)
            rows.append(row)
            print_row(row)
        print('-' * len(header))
    return rows


def run_target_sweep() -> List[Dict[str, object]]:
    """Время от номинала ``ARL_IC`` и допуска ``tol``."""
    print('\nA3.2. Время от номинала ARL_IC (SN n=14, шаг k=0.1)')
    header = (
        f"{'стат':>4} {'n':>3} {'шаг k':>6} {'цель':>5} {'tol':>5} "
        f"{'k':>6} {'h':>7} {'ARL_IC':>9} {'t, с':>8} "
        f"{'[min,max]':>16} {'тёпл.,с':>8} {'вычисл.':>8}"
    )
    print(header)
    print('-' * len(header))
    rows: List[Dict[str, object]] = []
    targets = (370.0, 500.0, 750.0)
    for target in targets:
        row = timed_case(n=14, target=target, k_step=0.1)
        rows.append(row)
        print_row(row)
    print('-' * len(header))

    print('\nA3.3. Время от допуска tol (SN n=14, δ=1, шаг k=0.1)')
    print(header)
    print('-' * len(header))
    for tol in (0.05, 0.10, 0.20):
        row = timed_case(n=14, tol=tol, k_step=0.1)
        rows.append(row)
        print_row(row)
    print('-' * len(header))
    return rows


def run_sr_sweep() -> List[Dict[str, object]]:
    """Время для SR (в полном режиме — и ``n=10``)."""
    print('\nA3.4. Время для CUSUM-SR (δ=1, ARL_IC=500)')
    header = (
        f"{'стат':>4} {'n':>3} {'шаг k':>6} {'цель':>5} {'tol':>5} "
        f"{'k':>6} {'h':>7} {'ARL_IC':>9} {'t, с':>8} "
        f"{'[min,max]':>16} {'тёпл.,с':>8} {'вычисл.':>8}"
    )
    print(header)
    print('-' * len(header))
    rows: List[Dict[str, object]] = []
    cases: Tuple[Tuple[int, float], ...] = (
        ((5, 1.0), (5, 0.5), (10, 0.5)) if FULL else ((5, 1.0), (5, 0.5))
    )
    for n, k_step in cases:
        row = timed_case(statistic='SR', n=n, k_step=k_step)
        rows.append(row)
        print_row(row)
    print('-' * len(header))
    return rows


def plot_times(
    step_rows: Sequence[Dict[str, object]],
    target_rows: Sequence[Dict[str, object]],
) -> Path:
    """Три панели: время от шага, от ``n`` и от номинала/допуска."""
    import matplotlib.pyplot as plt

    apply_minimal_latex_style()
    figure, axes = plt.subplots(1, 3, figsize=(10.0, 3.3))

    nodes = sorted({row['n'] for row in step_rows})
    for index, n in enumerate(nodes):
        subset = [row for row in step_rows if row['n'] == n]
        axes[0].plot(
            [row['k_step'] for row in subset],
            [row['time'] for row in subset],
            marker='o', color=PALETTE[index % len(PALETTE)],
            label=f'$n={n}$',
        )
    axes[0].set_xscale('log')
    axes[0].set_yscale('log')
    axes[0].set_xlabel(math_text('шаг сетки $k$'))
    axes[0].set_ylabel(math_text('время подбора, с'))
    axes[0].set_title(math_text('SN, $\\delta=1$'))
    axes[0].legend(frameon=False)

    fine = [row for row in step_rows if row['k_step'] == min(
        row['k_step'] for row in step_rows
    )]
    coarse = [row for row in step_rows if row['k_step'] == max(
        row['k_step'] for row in step_rows
    )]
    axes[1].plot([row['n'] for row in coarse],
                 [row['time'] for row in coarse],
                 marker='o', color=INK, label=math_text('шаг 1'))
    axes[1].plot([row['n'] for row in fine],
                 [row['time'] for row in fine],
                 marker='s', color=ACCENT, label=math_text('мелкий шаг'))
    axes[1].set_xscale('log')
    axes[1].set_yscale('log')
    axes[1].set_xlabel(math_text('размер подгруппы $n$'))
    axes[1].set_ylabel(math_text('время подбора, с'))
    axes[1].set_title(math_text('рост стоимости по $n$'))
    axes[1].legend(frameon=False)

    labels = [
        f"{row['target']:g} / {100 * row['tol']:.0f}\\%"
        for row in target_rows
    ]
    values = [row['time'] for row in target_rows]
    axes[2].bar(range(len(values)), values, color=PALETTE[2], width=0.6)
    axes[2].set_xticks(range(len(values)))
    axes[2].set_xticklabels(labels, rotation=45, ha='right', fontsize=7)
    axes[2].set_yscale('log')
    axes[2].set_ylabel(math_text('время подбора, с'))
    axes[2].set_title(math_text('цель/tol, $n=14$'))

    for axis in axes:
        despine(axis)
    figure.tight_layout()

    path = RESULTS / 'cusum_search_time.png'
    figure.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(figure)
    return path


def _run() -> int:
    print('Время поиска параметров (этап 3b.13)')
    print(f'Режим: {"полный" if FULL else "quick"}; '
          f'прогонов на случай: {REPEATS}')
    step_rows = run_step_sweep()
    target_rows = run_target_sweep()
    run_sr_sweep()

    path = plot_times(step_rows, target_rows)
    print(f'\nГрафик: {path.relative_to(ROOT)}')
    return 0


def main() -> int:
    """Печать таблиц времени с записью в файл."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / 'cusum_search_time.txt'
    with path.open('w', encoding='utf-8', buffering=1) as log, \
            redirect_stdout(Tee(sys.stdout, log)):
        code = _run()
    print(f'\nТаблицы сохранены: {path.relative_to(ROOT)}')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
