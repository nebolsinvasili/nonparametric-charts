#!/usr/bin/env python3
"""Параллельный подбор ``(k, h)``: процессы против потоков и чанков.

Эксперимент B этапа 3b.13. Сравниваются:

* последовательный запуск;
* потоки (``ThreadPoolExecutor``) — проверка, отпускает ли GIL линейная
  алгебра ``numpy``/LAPACK;
* процессы (``ProcessPoolExecutor``) с контекстами ``fork``, ``forkserver``
  и ``spawn``;
* чанки по 1 и по 4 случая на задачу;
* два уровня параллелизма: по кандидатам ``k`` внутри ``design_kh``
  (``n_jobs``) и по независимым случаям скана.

Нагрузки:

* **W1** — один подбор ``SN n=14, δ=1, шаг k=0.1`` (мало задач, разная
  стоимость);
* **W2** — скан 8 случаев ``SN``/``SR`` (embarrassingly parallel);
* **W3** — тяжёлый ``SR n=10, шаг k=0.5`` (крупные матрицы ``Q``);
* **W4** — гибрид: процессы по случаям и ``n_jobs=2`` внутри.

Каждый вариант прогоняется ``REPEATS = 5`` раз; берётся медиана, рядом
``[min, max]``. Корректность проверяется сравнением ``(k, h, ARL_IC)`` с
последовательным запуском.

Перед импортом ``numpy`` выставляется ``OMP_NUM_THREADS=1`` (и аналоги):
иначе вложенный BLAS-параллелизм искажает масштабирование.

Источник метода: Chakraborti & Graham (2019), §3.2.2, стр. 67–72;
§4.2.2.3.1, ур. 4.9, стр. 203–204 (марковская цепь — независимые задачи
по ``k``).

Запуск из корня репозитория:
    poetry run python experiments/cusum/09_parallel.py
    NPC_EXPERIMENT_FULL=1 poetry run python experiments/cusum/09_parallel.py
"""

from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import redirect_stdout
from multiprocessing import get_context
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

for _variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                  'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(_variable, '1')

import numpy as np  # noqa: E402

sys.path.insert(0, "src")

from nonparametric_charts.utils.plot_style import (  # noqa: E402
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

Spec = Tuple[str, int, float, float]

SCAN: Tuple[Spec, ...] = (
    ('SN', 10, 1.0, 0.1),
    ('SN', 10, 1.5, 0.1),
    ('SN', 14, 1.0, 0.1),
    ('SN', 14, 1.5, 0.1),
    ('SN', 20, 1.0, 0.1),
    ('SN', 20, 1.5, 0.1),
    ('SR', 5, 1.0, 0.5),
    ('SR', 5, 1.5, 0.5),
)
if FULL:
    SCAN += (
        ('SN', 10, 0.5, 0.1),
        ('SN', 10, 2.0, 0.1),
        ('SN', 14, 0.5, 0.1),
        ('SN', 14, 2.0, 0.1),
        ('SR', 10, 1.0, 0.5),
    )

HEAVY: Tuple[Spec, ...] = (
    ('SR', 10, 1.0, 0.5),
    ('SR', 10, 1.5, 0.5),
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


def run_case(spec: Spec) -> Tuple[float, float, float, float]:
    """Один независимый подбор; кэш очищается, чтобы замер был «холодным»."""
    statistic, n, delta, k_step = spec
    clear_run_length_cache()
    result = design_kh(
        n, TARGET, delta, statistic=statistic, sided='two', k_step=k_step,
    )
    return (result.k, result.h, result.arl_ic, result.arl_ooc)


def run_case_hybrid(spec: Spec) -> Tuple[float, float, float, float]:
    """То же, но с параллелизмом по кандидатам ``k`` внутри подбора."""
    statistic, n, delta, k_step = spec
    clear_run_length_cache()
    result = design_kh(
        n, TARGET, delta, statistic=statistic, sided='two', k_step=k_step,
        n_jobs=2,
    )
    return (result.k, result.h, result.arl_ic, result.arl_ooc)


def run_sequential(cases: Sequence[Spec], **_: object) -> List[Tuple]:
    return [run_case(case) for case in cases]


def run_threads(
    cases: Sequence[Spec], workers: int, **_: object
) -> List[Tuple]:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(run_case, cases))


def run_processes(
    cases: Sequence[Spec],
    workers: int,
    context: str = 'fork',
    chunksize: int = 1,
    **_: object,
) -> List[Tuple]:
    with ProcessPoolExecutor(
        max_workers=workers, mp_context=get_context(context)
    ) as pool:
        return list(pool.map(run_case, cases, chunksize=chunksize))


def run_hybrid(
    cases: Sequence[Spec], workers: int, **_: object
) -> List[Tuple]:
    with ProcessPoolExecutor(
        max_workers=workers, mp_context=get_context('fork')
    ) as pool:
        return list(pool.map(run_case_hybrid, cases, chunksize=1))


def time_variant(
    function,
    cases: Sequence[Spec],
    *,
    repeats: int = REPEATS,
    **kwargs: object,
) -> Dict[str, object]:
    """Медиана и размах времени варианта; результат последнего прогона."""
    function(cases, **kwargs)  # прогрев пула
    times: List[float] = []
    result: List[Tuple] = []
    for _ in range(repeats):
        start = time.perf_counter()
        result = function(cases, **kwargs)
        times.append(time.perf_counter() - start)
    return {
        'time': float(np.median(times)),
        'time_min': float(np.min(times)),
        'time_max': float(np.max(times)),
        'result': result,
    }


def check(actual: Sequence[Tuple], expected: Sequence[Tuple]) -> bool:
    """Совпадают ли ``(k, h, ARL_IC)`` с последовательным запуском."""
    return all(
        abs(a[0] - b[0]) < 1e-9
        and abs(a[1] - b[1]) < 1e-9
        and abs(a[2] - b[2]) < 1e-6
        for a, b in zip(actual, expected)
    )


def run_w1() -> List[Dict[str, object]]:
    """W1: параллелизм по кандидатам ``k`` внутри одного ``design_kh``."""
    print('\nW1. Один подбор: SN n=14, δ=1, шаг k=0.1 (n_jobs внутри)')
    header = (
        f"{'воркеров':>9} {'t, с':>8} {'[min,max]':>16} "
        f"{'ускорение':>10} {'k':>6} {'h':>7} {'ARL_IC':>9}"
    )
    print(header)
    print('-' * len(header))
    rows: List[Dict[str, object]] = []
    base: float | None = None
    for workers in (1, 2, 4):
        times: List[float] = []
        result = None
        for _ in range(REPEATS):
            clear_run_length_cache()
            start = time.perf_counter()
            result = design_kh(
                14, TARGET, 1.0, statistic='SN', sided='two',
                k_step=0.1, n_jobs=workers,
            )
            times.append(time.perf_counter() - start)
        assert result is not None
        median = float(np.median(times))
        if base is None:
            base = median
        rows.append({
            'workers': workers, 'time': median,
            'time_min': float(np.min(times)),
            'time_max': float(np.max(times)),
            'speedup': base / median,
            'k': result.k, 'h': result.h, 'arl_ic': result.arl_ic,
        })
        print(
            f"{workers:>9} {median:>8.3f} "
            f"{rows[-1]['time_min']:>7.3f}–{rows[-1]['time_max']:<7.3f} "
            f"{rows[-1]['speedup']:>10.2f} {result.k:>6.2f} "
            f"{result.h:>7.2f} {result.arl_ic:>9.2f}"
        )
    return rows


def run_w2() -> List[Dict[str, object]]:
    """W2: скан случаев — последовательно, потоки, процессы, чанки."""
    print(f'\nW2. Скан {len(SCAN)} случаев (сетка по случаям)')
    header = (
        f"{'вариант':>18} {'воркеров':>9} {'чанк':>5} {'t, с':>8} "
        f"{'[min,max]':>16} {'ускорение':>10} {'эфф.':>6} {'ok':>4}"
    )
    print(header)
    print('-' * len(header))

    sequential = time_variant(run_sequential, SCAN)
    base = float(sequential['time'])
    expected = sequential['result']
    rows: List[Dict[str, object]] = [{
        'variant': 'последовательно', 'workers': 1, 'chunk': 1,
        'time': base, 'time_min': sequential['time_min'],
        'time_max': sequential['time_max'], 'speedup': 1.0,
        'efficiency': 1.0, 'ok': True,
    }]
    print(
        f"{'последовательно':>18} {1:>9} {1:>5} {base:>8.3f} "
        f"{sequential['time_min']:>7.3f}–{sequential['time_max']:<7.3f} "
        f"{1.0:>10.2f} {1.0:>6.2f} {'да':>4}"
    )

    variants = [
        ('потоки', run_threads, {'workers': 4}, 4, 1),
        ('процессы fork', run_processes,
         {'workers': 4, 'context': 'fork', 'chunksize': 1}, 4, 1),
    ]
    if FULL:
        variants += [
            ('процессы fork', run_processes,
             {'workers': 2, 'context': 'fork', 'chunksize': 1}, 2, 1),
            ('процессы fork', run_processes,
             {'workers': 4, 'context': 'fork', 'chunksize': 4}, 4, 4),
            ('процессы forkserver', run_processes,
             {'workers': 4, 'context': 'forkserver', 'chunksize': 1}, 4, 1),
            ('процессы spawn', run_processes,
             {'workers': 4, 'context': 'spawn', 'chunksize': 1}, 4, 1),
        ]

    for label, function, kwargs, workers, chunk in variants:
        measured = time_variant(function, SCAN, **kwargs)
        speedup = base / float(measured['time'])
        ok = check(measured['result'], expected)
        rows.append({
            'variant': label, 'workers': workers, 'chunk': chunk,
            'time': measured['time'], 'time_min': measured['time_min'],
            'time_max': measured['time_max'], 'speedup': speedup,
            'efficiency': speedup / workers, 'ok': ok,
        })
        print(
            f"{label:>18} {workers:>9} {chunk:>5} "
            f"{measured['time']:>8.3f} "
            f"{measured['time_min']:>7.3f}–"
            f"{measured['time_max']:<7.3f} "
            f"{speedup:>10.2f} {speedup / workers:>6.2f} "
            f"{'да' if ok else 'НЕТ':>4}"
        )
    return rows


def run_w3() -> List[Dict[str, object]]:
    """W3: тяжёлые задачи SR — процессы против потоков."""
    print(f'\nW3. Тяжёлый SR (n=10, шаг k=0.5), {len(HEAVY)} случая')
    header = (
        f"{'вариант':>18} {'воркеров':>9} {'t, с':>8} {'[min,max]':>16} "
        f"{'ускорение':>10} {'ok':>4}"
    )
    print(header)
    print('-' * len(header))
    sequential = time_variant(run_sequential, HEAVY)
    base = float(sequential['time'])
    rows: List[Dict[str, object]] = [{
        'variant': 'последовательно', 'workers': 1, 'time': base,
        'time_min': sequential['time_min'],
        'time_max': sequential['time_max'], 'speedup': 1.0, 'ok': True,
    }]
    print(
        f"{'последовательно':>18} {1:>9} {base:>8.3f} "
        f"{sequential['time_min']:>7.3f}–{sequential['time_max']:<7.3f} "
        f"{1.0:>10.2f} {'да':>4}"
    )
    for label, function, kwargs, workers in (
        ('потоки', run_threads, {'workers': 2}, 2),
        ('процессы fork', run_processes,
         {'workers': 2, 'context': 'fork', 'chunksize': 1}, 2),
    ):
        measured = time_variant(function, HEAVY, **kwargs)
        speedup = base / float(measured['time'])
        ok = check(measured['result'], sequential['result'])
        rows.append({
            'variant': label, 'workers': workers, 'time': measured['time'],
            'time_min': measured['time_min'],
            'time_max': measured['time_max'], 'speedup': speedup, 'ok': ok,
        })
        print(
            f"{label:>18} {workers:>9} {measured['time']:>8.3f} "
            f"{measured['time_min']:>7.3f}–{measured['time_max']:<7.3f} "
            f"{speedup:>10.2f} {'да' if ok else 'НЕТ':>4}"
        )
    return rows


def run_w4() -> List[Dict[str, object]]:
    """W4: гибрид — процессы по случаям и ``n_jobs=2`` внутри."""
    print('\nW4. Гибрид: 4 процесса по случаям, внутри n_jobs=2')
    header = (
        f"{'вариант':>18} {'воркеров':>9} {'t, с':>8} "
        f"{'[min,max]':>16} {'ускорение':>10} {'ok':>4}"
    )
    print(header)
    print('-' * len(header))
    sequential = time_variant(run_sequential, SCAN)
    base = float(sequential['time'])
    measured = time_variant(run_hybrid, SCAN, workers=4)
    speedup = base / float(measured['time'])
    ok = check(measured['result'], sequential['result'])
    print(
        f"{'гибрид':>18} {4:>9} {measured['time']:>8.3f} "
        f"{measured['time_min']:>7.3f}–{measured['time_max']:<7.3f} "
        f"{speedup:>10.2f} {'да' if ok else 'НЕТ':>4}"
    )
    return [{
        'variant': 'гибрид', 'workers': 4, 'time': measured['time'],
        'time_min': measured['time_min'], 'time_max': measured['time_max'],
        'speedup': speedup, 'ok': ok,
    }]


def plot_parallel(
    w1: Sequence[Dict[str, object]],
    w2: Sequence[Dict[str, object]],
    w3: Sequence[Dict[str, object]],
) -> Path:
    """Три панели: время, ускорение и тяжёлый SR."""
    import matplotlib.pyplot as plt

    apply_minimal_latex_style()
    figure, axes = plt.subplots(1, 3, figsize=(10.0, 3.4))

    scan = [row for row in w2]
    positions = range(len(scan))
    colors = [PALETTE[index % len(PALETTE)] for index in positions]

    axes[0].bar(positions, [row['time'] for row in scan], color=colors,
                width=0.6)
    axes[0].set_xticks(list(positions))
    axes[0].set_xticklabels(
        [f"{row['variant']}, p={row['workers']}" for row in scan],
        rotation=30, ha='right', fontsize=7,
    )
    axes[0].set_ylabel(math_text('время скана, с'))
    axes[0].set_title(math_text('W2: $8$ случаев'))

    axes[1].bar(positions, [row['speedup'] for row in scan], color=colors,
                width=0.6)
    axes[1].axhline(4.0, linestyle='--', linewidth=0.9, color=INK)
    axes[1].set_xticks(list(positions))
    axes[1].set_xticklabels(
        [f"{row['variant']}, p={row['workers']}" for row in scan],
        rotation=30, ha='right', fontsize=7,
    )
    axes[1].set_ylabel(math_text('ускорение $T_1/T_p$'))
    axes[1].set_title(math_text('W2: ускорение (штрих — идеал p=4)'))

    labels = [f"{row['variant']}, p={row['workers']}" for row in w3]
    axes[2].bar(range(len(w3)), [row['time'] for row in w3],
                color=[PALETTE[i % len(PALETTE)] for i in range(len(w3))],
                width=0.6)
    axes[2].set_xticks(range(len(w3)))
    axes[2].set_xticklabels(labels, rotation=30, ha='right', fontsize=7)
    axes[2].set_ylabel(math_text('время, с'))
    axes[2].set_title(math_text('W3: тяжёлый $SR$'))

    for axis in axes:
        despine(axis)
    figure.tight_layout()

    path = RESULTS / 'cusum_parallel.png'
    figure.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(figure)
    return path


def _run() -> int:
    print('Параллельный подбор (этап 3b.13)')
    print(f'Режим: {"полный" if FULL else "quick"}; '
          f'прогонов на вариант: {REPEATS}; ядер: {os.cpu_count()}')
    w1 = run_w1()
    w2 = run_w2()
    w3 = run_w3()
    w4 = run_w4()

    best = max(
        (
            row for row in w2
            if row['variant'] != 'последовательно' and row['ok']
        ),
        key=lambda row: row['speedup'],
    )
    print(f"\nЛучший вариант W2: {best['variant']}, "
          f"{best['workers']} воркеров, ускорение {best['speedup']:.2f}×")
    print(f"Гибрид W4: ускорение {w4[0]['speedup']:.2f}×")

    path = plot_parallel(w1, w2, w3)
    print(f'\nГрафик: {path.relative_to(ROOT)}')
    return 0


def main() -> int:
    """Печать таблиц параллелизации с записью в файл."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / 'cusum_parallel.txt'
    with path.open('w', encoding='utf-8', buffering=1) as log, \
            redirect_stdout(Tee(sys.stdout, log)):
        code = _run()
    print(f'\nТаблицы сохранены: {path.relative_to(ROOT)}')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
