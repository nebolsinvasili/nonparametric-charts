#!/usr/bin/env python3
"""Разрешение сетки подбора ``(k, h)``: где выгоден мелкий шаг, где крупный.

Два эксперимента:

* **A1 — выгода шага.** Для набора случаев (статистика, ``n``, ``δ``)
  выполняется ``design_kh`` на сетках ``k`` с шагом 1, 0.5 и 0.1 (в полном
  режиме — также 2 и 0.25). Сравниваются отклонение ``ARL_IC`` от номинала,
  ``ARL_OOC`` и время поиска. Мелкий шаг оправдан, когда крупная сетка
  попадает на «плохой» узел ``h``; крупный — когда он уже укладывается в
  допуск, а дробление только увеличивает время.
* **A2 — упор в дискретность.** Для каждого случая собираются достижимые
  значения ``ARL_IC`` на решётке ``(k, h)``; для номинала 500 находится
  ближайшее снизу и сверху, считается разрыв. Лестница ``ARL(h)`` при
  фиксированном ``k`` показывает плато и «перескок» через номинал.

Каждый случай прогоняется ``REPEATS = 5`` раз с очисткой кэша ``ARL``:
для точного марковского расчёта значения ``ARL`` детерминированы
(разброс 0), повторные прогоны нужны для устойчивой оценки времени.

Источник метода: Chakraborti & Graham (2019), §3.2.2, стр. 67–72
(``k`` первым, ``h`` под номинал; ``ARL(h)`` — ступенчатая функция);
§4.2.2, стр. 202–206; §4.3.2, стр. 232–238. Шаг решётки состояний —
``gcd{|Z_t − k|}``, поэтому дробление ``k`` дробит и сетку ``h``.

Запуск из корня репозитория:
    poetry run python experiments/cusum/07_grid_resolution.py
    NPC_EXPERIMENT_FULL=1 poetry run python \\
        experiments/cusum/07_grid_resolution.py
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# Замеры времени — без вложенного BLAS-параллелизма.
for _variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                  'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(_variable, '1')

import numpy as np  # noqa: E402

sys.path.insert(0, "src")

from nonparametric_charts.utils.plot_style import (  # noqa: E402
    ALERT,
    INK,
    PALETTE,
    apply_minimal_latex_style,
    despine,
    math_text,
)
from nonparametric_charts.utils.run_length import (  # noqa: E402
    sign_step_distribution,
    signed_rank_step_distribution,
)
from nonparametric_charts.utils.run_length_design import (  # noqa: E402
    _lattice_step,
    cached_arl,
    clear_run_length_cache,
    design_h,
    design_kh,
)

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "experiments"

REPEATS = 5
TARGET = 500.0
FULL = os.environ.get("NPC_EXPERIMENT_FULL", "0") == "1"

#: (статистика, n, δ, шаги сетки k).
if FULL:
    CASES: Tuple[Tuple[str, int, float, Tuple[float, ...]], ...] = (
        ('SN', 10, 1.0, (2.0, 1.0, 0.5, 0.25, 0.1)),
        ('SN', 10, 1.5, (2.0, 1.0, 0.5, 0.25, 0.1)),
        ('SN', 14, 1.0, (2.0, 1.0, 0.5, 0.25, 0.1)),
        ('SN', 14, 1.5, (2.0, 1.0, 0.5, 0.25, 0.1)),
        ('SN', 20, 1.0, (2.0, 1.0, 0.5, 0.25, 0.1)),
        ('SN', 20, 1.5, (2.0, 1.0, 0.5, 0.25, 0.1)),
        ('SR', 5, 1.0, (2.0, 1.0, 0.5, 0.25, 0.1)),
        ('SR', 10, 1.0, (2.0, 1.0, 0.5)),
    )
else:
    CASES = (
        ('SN', 10, 1.0, (1.0, 0.5, 0.1)),
        ('SN', 10, 1.5, (1.0, 0.5, 0.1)),
        ('SN', 14, 1.0, (1.0, 0.5, 0.1)),
        ('SN', 14, 1.5, (1.0, 0.5, 0.1)),
        ('SR', 5, 1.0, (1.0, 0.5)),
    )

#: Случаи для лестницы ``ARL(h)`` (``k`` на разных решётках).
STAIRCASE = (
    (6.0, 2.0, 'k = 6 (шаг h = 2)'),
    (6.5, 0.5, 'k = 6.5 (шаг h = 0.5)'),
    (6.1, 0.1, 'k = 6.1 (шаг h = 0.1)'),
    (3.6, 0.1, 'k = 3.6 (шаг h = 0.1)'),
)


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


def distribution(statistic: str, n: int) -> Tuple[np.ndarray, np.ndarray]:
    """Распределение статистики в IC."""
    if statistic == 'SN':
        return sign_step_distribution(n)
    return signed_rank_step_distribution(n)


def repeated_design(
    statistic: str,
    n: int,
    delta: float,
    k_step: float,
    repeats: int = REPEATS,
) -> Tuple[object, List[float], float]:
    """``design_kh`` с очисткой кэша перед каждым прогоном.

    Возвращает результат, список времён и время «тёплого» прогона
    (кэш заполнен предыдущим расчётом).
    """
    clear_run_length_cache()
    times: List[float] = []
    result = None
    for _ in range(repeats):
        clear_run_length_cache()
        start = time.perf_counter()
        result = design_kh(
            n, TARGET, delta, statistic=statistic, sided='two',
            k_step=k_step,
        )
        times.append(time.perf_counter() - start)
    assert result is not None

    start = time.perf_counter()
    design_kh(
        n, TARGET, delta, statistic=statistic, sided='two', k_step=k_step,
    )
    warm = time.perf_counter() - start
    return result, times, warm


def verdict(error: float, ooc: float, base_error: float,
            base_ooc: float) -> str:
    """Сравнить шаг с базовым (шаг 1) по точности, OOC и смыслу."""
    if abs(error) + 0.005 < abs(base_error) and ooc <= base_ooc * 1.05:
        return 'мелкий лучше'
    if abs(error) <= abs(base_error) + 0.005:
        return 'крупный лучше'
    return 'спорно'


def run_a1() -> List[Dict[str, object]]:
    """Таблица A1: характеристика каждого случая и шага сетки ``k``."""
    print('\nA1. Подбор (k, h) при разном шаге сетки k '
          f'(номинал ARL_IC = {TARGET:g}, {REPEATS} прогонов)')
    header = (
        f"{'стат':>4} {'n':>3} {'δ':>4} {'шаг k':>6} {'k':>6} {'h':>7} "
        f"{'ARL_IC':>9} {'откл.,%':>8} {'ARL_OOC':>8} "
        f"{'t, с':>7} {'[min,max]':>14} {'вердикт':>15}"
    )
    print(header)
    print('-' * len(header))

    rows: List[Dict[str, object]] = []
    for statistic, n, delta, steps in CASES:
        case_rows: List[Dict[str, object]] = []
        for k_step in steps:
            result, times, warm = repeated_design(
                statistic, n, delta, k_step
            )
            error = (result.arl_ic - TARGET) / TARGET
            case_rows.append({
                'statistic': statistic, 'n': n, 'delta': delta,
                'k_step': k_step, 'k': result.k, 'h': result.h,
                'arl_ic': result.arl_ic, 'error': error,
                'arl_ooc': result.arl_ooc,
                'time': float(np.median(times)),
                'time_min': float(np.min(times)),
                'time_max': float(np.max(times)),
                'time_warm': warm,
                'n_evaluated': result.n_evaluated,
            })

        base = next(
            (row for row in case_rows if row['k_step'] == 1.0), None
        )
        for row in case_rows:
            if base is None or row['k_step'] == 1.0:
                row['verdict'] = 'база'
            else:
                row['verdict'] = verdict(
                    float(row['error']), float(row['arl_ooc']),
                    float(base['error']), float(base['arl_ooc']),
                )
            rows.append(row)
            print(
                f"{statistic:>4} {n:>3} {delta:>4.1f} "
                f"{row['k_step']:>6.2f} "
                f"{row['k']:>6.2f} {row['h']:>7.2f} "
                f"{row['arl_ic']:>9.2f} {100 * float(row['error']):>+8.2f} "
                f"{row['arl_ooc']:>8.3f} "
                f"{row['time']:>7.3f} "
                f"{row['time_min']:>6.3f}–{row['time_max']:<6.3f} "
                f"{row['verdict']:>15}"
            )
        print('-' * len(header))
    return rows


def gap_for_k(
    statistic: str,
    n: int,
    k: float,
    target: float = TARGET,
) -> Optional[Dict[str, float]]:
    """Ближайшие к номиналу узлы ``ARL(h)`` снизу и сверху при данном ``k``."""
    values, probabilities = distribution(statistic, n)
    step = _lattice_step(values, k)
    try:
        below = design_h(
            values, probabilities, target, k,
            sided='two', statistic=statistic, n=n,
            ic_rule='conservative',
        )
    except ValueError:
        return None

    if below.arl > target:
        return {
            'k': k, 'h_below': float('nan'), 'arl_below': float('nan'),
            'h_above': below.h, 'arl_above': below.arl,
            'gap': float('nan'),
        }

    above_h = below.h + step
    above_arl = cached_arl(values, probabilities, k, above_h, sided='two')
    return {
        'k': k, 'h_below': below.h, 'arl_below': below.arl,
        'h_above': above_h, 'arl_above': above_arl,
        'gap': above_arl - below.arl,
    }


def scan_case(
    statistic: str,
    n: int,
    delta: float,
    k_step: float,
) -> Optional[Dict[str, float]]:
    """Лучший (минимальный разрыв) узел среди кандидатов ``k`` дизайна."""
    design = design_kh(
        n, TARGET, delta, statistic=statistic, sided='two', k_step=k_step,
    )
    best: Optional[Dict[str, float]] = None
    for k in design.table['k']:
        if not np.isfinite(k):
            continue
        # Убираем шум представления (6.1000000000000005): у порога h он
        # сдвигает состояние и меняет ARL на десятки единиц.
        gap = gap_for_k(statistic, n, round(float(k), 10))
        if gap is None or not np.isfinite(gap['gap']):
            continue
        if best is None or gap['gap'] < best['gap']:
            best = gap
    if best is None:
        return None
    best['k_step'] = k_step
    best['design_k'] = design.k
    return best


def run_a2() -> List[Dict[str, object]]:
    """Таблица A2: разрыв между достижимыми ``ARL`` вокруг номинала."""
    print('\nA2. Дискретность: ближайшие к номиналу достижимые ARL_IC')
    header = (
        f"{'стат':>4} {'n':>3} {'δ':>4} {'шаг k':>6} "
        f"{'k':>6} {'h↓':>7} {'ARL↓':>9} {'h↑':>7} {'ARL↑':>9} "
        f"{'разрыв':>9} {'t, с':>7}"
    )
    print(header)
    print('-' * len(header))

    rows: List[Dict[str, object]] = []
    for statistic, n, delta, steps in CASES:
        for k_step in steps:
            start = time.perf_counter()
            best: Optional[Dict[str, float]] = None
            for _ in range(REPEATS):
                clear_run_length_cache()
                best = scan_case(statistic, n, delta, k_step)
            elapsed = (time.perf_counter() - start) / REPEATS
            if best is None:
                print(f'{statistic} n={n} δ={delta} шаг={k_step}: '
                      'достижимых узлов нет')
                continue
            row = {
                'statistic': statistic, 'n': n, 'delta': delta,
                'k_step': k_step, **best, 'time': elapsed,
            }
            rows.append(row)
            print(
                f"{statistic:>4} {n:>3} {delta:>4.1f} {k_step:>6.2f} "
                f"{best['k']:>6.2f} {best['h_below']:>7.2f} "
                f"{best['arl_below']:>9.2f} {best['h_above']:>7.2f} "
                f"{best['arl_above']:>9.2f} {best['gap']:>9.2f} "
                f"{elapsed:>7.3f}"
            )
        print('-' * len(header))
    return rows


def plot_a1(rows: Sequence[Dict[str, object]]) -> Path:
    """Три панели: отклонение, ARL_OOC и время от шага сетки ``k``."""
    import matplotlib.pyplot as plt

    apply_minimal_latex_style()
    figure, axes = plt.subplots(1, 3, figsize=(10.0, 3.4))

    cases = []
    for row in rows:
        key = (row['statistic'], row['n'], row['delta'])
        if key not in cases:
            cases.append(key)

    for index, key in enumerate(cases):
        subset = [
            row for row in rows
            if (row['statistic'], row['n'], row['delta']) == key
        ]
        steps = [row['k_step'] for row in subset]
        color = PALETTE[index % len(PALETTE)]
        label = (
            f"{key[0]}, $n={key[1]}$, $\\delta={key[2]:g}$"
        )
        axes[0].plot(steps, [100 * row['error'] for row in subset],
                     marker='o', color=color, label=label)
        axes[1].plot(steps, [row['arl_ooc'] for row in subset],
                     marker='o', color=color, label=label)
        axes[2].plot(steps, [row['time'] for row in subset],
                     marker='o', color=color, label=label)

    axes[0].axhline(0.0, color=INK, linewidth=0.8, linestyle='--')
    axes[0].set_ylabel(math_text('отклонение $ARL_{IC}$, \\%'))
    axes[1].set_ylabel(math_text('$ARL_{OOC}$ при целевом $\\delta$'))
    axes[2].set_ylabel(math_text('время подбора, с'))
    for axis in axes:
        axis.set_xscale('log')
        axis.set_xlabel(math_text('шаг сетки $k$'))
        despine(axis)
    axes[2].set_yscale('log')
    axes[1].legend(frameon=False, fontsize=7)
    axes[2].set_title(math_text('очистка кэша перед прогоном'))

    figure.tight_layout()
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / 'cusum_grid_resolution.png'
    figure.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(figure)
    return path


def staircase(
    k: float,
    h_max: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Значения ``ARL(h)`` на решётке ``h = step·i`` для ``n = 14``."""
    values, probabilities = sign_step_distribution(14)
    step = _lattice_step(values, k)
    hs = np.arange(step, h_max + step / 2, step)
    arls = np.array([
        cached_arl(values, probabilities, k, float(h), sided='two')
        for h in hs
    ])
    return hs, arls


def plot_a2(rows: Sequence[Dict[str, object]]) -> Path:
    """Две панели: разрыв от шага и лестница ``ARL(h)``."""
    import matplotlib.pyplot as plt

    apply_minimal_latex_style()
    figure, axes = plt.subplots(1, 2, figsize=(10.0, 3.6))

    cases = []
    for row in rows:
        key = (row['statistic'], row['n'], row['delta'])
        if key not in cases:
            cases.append(key)

    for index, key in enumerate(cases):
        subset = [
            row for row in rows
            if (row['statistic'], row['n'], row['delta']) == key
        ]
        axes[0].plot(
            [row['k_step'] for row in subset],
            [row['gap'] for row in subset],
            marker='o', color=PALETTE[index % len(PALETTE)],
            label=f"{key[0]}, $n={key[1]}$, $\\delta={key[2]:g}$",
        )
    axes[0].set_xscale('log')
    axes[0].set_yscale('log')
    axes[0].set_xlabel(math_text('шаг сетки $k$'))
    axes[0].set_ylabel(math_text('разрыв $ARL_\\uparrow - ARL_\\downarrow$'))
    axes[0].set_title(math_text('разрыв вокруг номинала 500'))
    axes[0].legend(frameon=False, fontsize=7)
    despine(axes[0])

    for index, (k, _, label) in enumerate(STAIRCASE):
        hs, arls = staircase(k, 12.0)
        axes[1].plot(
            hs, arls, marker='o', markersize=2.5,
            color=PALETTE[index % len(PALETTE)], label=math_text(label),
        )
    axes[1].axhline(TARGET, color=ALERT, linestyle='--', linewidth=1.0,
                    label=math_text(f'номинал {TARGET:g}'))
    axes[1].set_yscale('log')
    axes[1].set_ylim(20, 5000)
    axes[1].set_xlabel(math_text('интервал решения $h$'))
    axes[1].set_ylabel(math_text('$ARL_{IC}(h)$'))
    axes[1].set_title(math_text('CUSUM-SN, $n=14$: плато и перескок'))
    axes[1].legend(frameon=False, fontsize=7)
    despine(axes[1])

    figure.tight_layout()
    path = RESULTS / 'cusum_discreteness.png'
    figure.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(figure)
    return path


def _run() -> int:
    print('Разрешение сетки подбора (этап 3b.13)')
    print(f'Режим: {"полный" if FULL else "quick"}; '
          f'прогонов на случай: {REPEATS}')
    rows_a1 = run_a1()
    rows_a2 = run_a2()

    path_a1 = plot_a1(rows_a1)
    path_a2 = plot_a2(rows_a2)
    print(f'\nГрафики: {path_a1.relative_to(ROOT)}, '
          f'{path_a2.relative_to(ROOT)}')
    return 0


def main() -> int:
    """Печать таблиц A1/A2 с записью в файл."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / 'cusum_grid_resolution.txt'
    with path.open('w', encoding='utf-8', buffering=1) as log, \
            redirect_stdout(Tee(sys.stdout, log)):
        code = _run()
    print(f'\nТаблицы сохранены: {path.relative_to(ROOT)}')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
