#!/usr/bin/env python3
"""Координаты графиков отчёта о верификации CUSUM (``docs/reports``).

Генерирует макросы ``docs/reports/cusum_macros.tex``:

* OC-кривые (``ARL(δ)``) для номинальных вариантов книги — CUSUM-SN
  (``n=10, k=6, h=4``, рис. 4.5, стр. 234) и CUSUM-SR (``n=10, k=41``,
  ``h=14`` — подобранное под ``ARL_IC=500``; книжное ``h=24`` см.~в
  разделе о расхождении, рис. 4.6, стр. 240);
* ``ARL_IC(h)`` при фиксированном ``k`` — ступенчатая функция для
  дискретной статистики, объясняющая консервативный выбор ``h``
  (``design_h``, §3.2.2, стр. 71).

Источник метода: Chakraborti & Graham (2019), §4.2.2, стр. 202–208;
§4.3.2, стр. 229–243; §3.2.2, стр. 67–72.

Запуск из корня репозитория:
    poetry run python experiments/cusum/06_gen_figdata.py \
        > docs/reports/cusum_macros.tex
"""

from __future__ import annotations

import sys

import numpy as np

sys.path.insert(0, "src")

from nonparametric_charts.utils.run_length import (  # noqa: E402
    cusum_sign_run_length,
    cusum_signed_rank_run_length,
)
from nonparametric_charts.utils.run_length_design import oc_curve  # noqa: E402

DELTAS = np.round(np.arange(0.0, 2.01, 0.25), 2)
SN_DESIGN = (10, 6, 4)
SR_DESIGN = (10, 41, 14)
SN_DISTRIBUTIONS = ('normal', 't', 'laplace', 'logistic', 'uniform', 'gamma')
SR_DISTRIBUTIONS = ('normal', 't', 'laplace', 'logistic', 'uniform')


def coordinates(x: np.ndarray, y: np.ndarray) -> str:
    """Координаты для pgfplots: ``(x,y) (x,y) ...``."""
    return ' '.join(f'({a:.4f},{b:.6f})' for a, b in zip(x, y))


def define(name: str, x: np.ndarray, y: np.ndarray) -> None:
    print(f'\\def\\{name}{{{coordinates(x, y)}}}')


def main() -> int:
    print('% Сгенерировано experiments/cusum/06_gen_figdata.py.')
    print('% Не редактировать вручную: пересобрать командой make cusum.')
    print()

    print('% --- OC-кривые: CUSUM-SN, n=10, k=6, h=4 (рис. 4.5) ---')
    for distribution in SN_DISTRIBUTIONS:
        frame = oc_curve(
            *SN_DESIGN, DELTAS,
            statistic='SN', sided='two', distribution=distribution,
        )
        define(f'ocSN{distribution.capitalize()}', DELTAS,
               frame['arl'].to_numpy())
    print()

    print('% --- OC-кривые: CUSUM-SR, n=10, k=41, h=14 ---')
    for distribution in SR_DISTRIBUTIONS:
        frame = oc_curve(
            SR_DESIGN[0], SR_DESIGN[1], SR_DESIGN[2], DELTAS,
            statistic='SR', sided='two', distribution=distribution,
            n_sim=100_000, seed=20261020,
        )
        define(f'ocSR{distribution.capitalize()}', DELTAS,
               frame['arl'].to_numpy())
    print()

    print('% --- ARL_IC(h): CUSUM-SN, n=10, k=6 ---')
    h_values = np.arange(1, 11, 1.0)
    arl_values = np.array([
        cusum_sign_run_length(10, 6, h, sided='two').arl for h in h_values
    ])
    define('arlHSN', h_values, arl_values)
    print()

    print('% --- ARL_IC(h): CUSUM-SR, n=10, k=41 ---')
    h_values = np.arange(2, 25, 1.0)
    arl_values = np.array([
        cusum_signed_rank_run_length(
            10, 41, h, sided='two', max_quantile=0.5
        ).arl for h in h_values
    ])
    define('arlHSR', h_values, arl_values)
    print()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
