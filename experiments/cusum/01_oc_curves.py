#!/usr/bin/env python3
"""OC-кривые CUSUM-SN и CUSUM-SR: ``ARL(δ)`` для разных распределений.

Считает и печатает таблицы ``ARL`` по сетке сдвигов ``δ`` для распределений
normal, ``t``, Laplace, logistic, uniform (для SR — симметричные), а также
gamma (только SN: знаковая карта не требует симметрии). Строит две панели:

* CUSUM-SN по примеру 4.8 (``n=5, k=1, h=4``, верхняя);
* CUSUM-SR по примеру 4.10 (``n=4, k=2, h=6``, верхняя).

Источник: Chakraborti & Graham (2019), §4.2.2, стр. 202–208. Рис. 4.5
(стр. 204) и рис. 4.6 (стр. 207) — SAS-выводы распределения RL для
дизайнов `n=10, k=6, h=4` и `n=10, k=41, h=24`; OC-кривые ниже считаются
нашей реализацией. При ``δ=0`` ARL не зависит от распределения.

Запуск из корня репозитория:
    poetry run python experiments/cusum/01_oc_curves.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")

from nonparametric_charts.utils.run_length_design import oc_curve  # noqa: E402
from nonparametric_charts.utils.plot_style import (  # noqa: E402
    ACCENT,
    INK,
    PALETTE,
    apply_minimal_latex_style,
    despine,
    math_text,
)

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "experiments"

DELTAS = np.round(np.arange(0.0, 3.01, 0.25), 2)
SN_DISTRIBUTIONS = ('normal', 't', 'laplace', 'logistic', 'uniform', 'gamma')
SR_DISTRIBUTIONS = ('normal', 't', 'laplace', 'logistic', 'uniform')


def compute(curves: dict[str, np.ndarray], label: str) -> None:
    """Напечатать таблицу ``ARL(δ)``."""
    print(f'\n{label}')
    header = 'delta  ' + '  '.join(f'{name:>9}' for name in curves)
    print(header)
    print('-' * len(header))
    for index, delta in enumerate(DELTAS):
        values = '  '.join(
            f'{curve[index]:9.3f}' for curve in curves.values()
        )
        print(f'{delta:5.2f}  {values}')


def main() -> int:
    print('OC-кривые CUSUM: ARL(δ)')
    print('Источник: Chakraborti & Graham (2019), §4.2.2, стр. 202–208')

    sn_curves = {
        distribution: oc_curve(
            5, 1, 4, DELTAS,
            statistic='SN', sided='upper', distribution=distribution,
        )['arl'].to_numpy()
        for distribution in SN_DISTRIBUTIONS
    }
    compute(sn_curves, 'CUSUM-SN: n=5, k=1, h=4 (пример 4.8)')

    sr_curves = {
        distribution: oc_curve(
            4, 2, 6, DELTAS,
            statistic='SR', sided='upper', distribution=distribution,
            n_sim=100_000, seed=20261019,
        )['arl'].to_numpy()
        for distribution in SR_DISTRIBUTIONS
    }
    compute(sr_curves, 'CUSUM-SR: n=4, k=2, h=6 (пример 4.10)')

    ic_values = [curve[0] for curve in sn_curves.values()]
    print(
        '\nIC-проверка: ARL(0) по SN = '
        f'{ic_values[0]:.6f}; разброс по распределениям = '
        f'{max(ic_values) - min(ic_values):.1e}'
    )

    import matplotlib.pyplot as plt

    apply_minimal_latex_style()
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)

    for ax, curves, title in (
        (axes[0], sn_curves, 'CUSUM-SN'),
        (axes[1], sr_curves, 'CUSUM-SR'),
    ):
        for index, (name, curve) in enumerate(curves.items()):
            color = ACCENT if index == 0 else PALETTE[index % len(PALETTE)]
            ax.plot(
                DELTAS, curve, color=color, linewidth=1.1,
                marker='o', markersize=2.5, label=name,
            )
        ax.set_yscale('log')
        ax.set_xlabel(
            r'$\delta$ (' + math_text('сдвиг в единицах') + r' $\sigma$)'
        )
        ax.set_title(title, color=INK)
        ax.axhline(1.0, color=INK, linewidth=0.8, linestyle=':')
        despine(ax)
        ax.legend(fontsize=8, frameon=False, ncol=2)

    axes[0].set_ylabel(r'$\mathrm{ARL}(\delta)$')
    figure.tight_layout()

    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / 'cusum_oc_curves.png'
    figure.savefig(path, dpi=200)
    plt.close(figure)
    print(f'\nГрафик сохранён: {path.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
