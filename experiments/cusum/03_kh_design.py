#!/usr/bin/env python3
"""Совместный дизайн ``(k, h)`` CUSUM-SN и CUSUM-SR.

Печатает таблицы дизайнов под номинальный ``ARL_IC`` (370 и 500) и целевой
сдвиг ``δ``: для каждого ``k`` из решётки статистики подбирается ``h`` так,
чтобы достигался номинал, а оптимальной считается пара с минимальным
``ARL_OOC`` (при сетке ``δ`` — минимакс). Строит две панели ``ARL_OOC(k)``,
аналогичные рис. 3.2 книги (параметрический CUSUM): видно, что слишком
большое ``k`` резко ухудшает обнаружение малых сдвигов, а слишком малое —
крупных.

Источник: Chakraborti & Graham (2019), §3.2.2, стр. 67–72 (``k = δ/2``,
минимум ``ARL_OOC`` при фиксированном ``ARL_IC``; табл. 3.1);
§4.2.2, стр. 202–206; §4.3.2, стр. 232–233, 236–238. Таблица ``(h, k)`` для
``n = 10`` — Amin, Reynolds & Bakir (1995), табл. 5.

Запуск из корня репозитория:
    poetry run python experiments/cusum/03_kh_design.py
"""

from __future__ import annotations

import sys
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")

from nonparametric_charts.utils.run_length_design import (  # noqa: E402
    design_sign_h,
    design_sign_kh,
    design_signed_rank_kh,
)
from nonparametric_charts.utils.plot_style import (  # noqa: E402
    INK,
    PALETTE,
    apply_minimal_latex_style,
    despine,
    math_text,
)

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "experiments"

SN_DESIGN_N = (10, 15, 20)
SR_DESIGN_N = (5, 10)
TARGETS = (370.0, 500.0)
SN_DELTAS = (0.5, 1.0, 1.5, 2.0)
SR_DELTAS = (0.5, 1.0, 1.5)
# Для SN пространство состояний мало, поэтому сетку k можно расширить вниз:
# на грубой решётке малое k иногда единственное, дающее ARL_IC вблизи номинала.
SN_K_FRACTIONS = (0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0)


def print_design_table(statistic: str, n: int, target: float) -> None:
    """Напечатать строку дизайна для каждого целевого сдвига ``δ``."""
    deltas = SN_DELTAS if statistic == 'SN' else SR_DELTAS
    print(f'\n{statistic}: n={n}, ARL_IC={target:g}')
    header = (
        f'{"delta":>6}  {"k":>6}  {"h":>6}  {"ARL_IC":>9}  '
        f'{"err_ic":>7}  {"ARL_OOC":>9}'
    )
    print(header)
    print('-' * len(header))
    for delta in deltas:
        if statistic == 'SN':
            result = design_sign_kh(
                n, target, delta, sided='two',
                k_fractions=SN_K_FRACTIONS,
            )
        else:
            result = design_signed_rank_kh(n, target, delta, sided='two')
        print(
            f'{delta:6.2f}  {result.k:6.2f}  {result.h:6.2f}  '
            f'{result.arl_ic:9.2f}  {result.relative_error_ic:6.1%}  '
            f'{result.arl_ooc:9.2f}'
        )


def ooc_vs_k(
    statistic: str,
    n: int,
    target: float,
    k_values: np.ndarray,
    deltas: tuple[float, ...],
) -> dict[float, np.ndarray]:
    """``ARL_OOC(k)`` для каждого ``δ`` по общей сетке ``k``."""
    curves: dict[float, np.ndarray] = {}
    for delta in deltas:
        values: list[float] = []
        for k in k_values:
            if statistic == 'SN':
                result = design_sign_kh(
                    n, target, delta, k_values=[float(k)], tol=1.0,
                )
            else:
                result = design_signed_rank_kh(
                    n, target, delta, k_values=[float(k)], tol=1.0,
                )
            values.append(result.arl_ooc)
        curves[delta] = np.asarray(values)
    return curves


def plot_panels(panels: list[tuple[str, float, np.ndarray, dict]]) -> Path:
    """Две панели ``ARL_OOC(k)`` (по образцу рис. 3.2 книги)."""
    import matplotlib.pyplot as plt

    apply_minimal_latex_style()
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.8))

    for ax, (title, target, k_values, curves) in zip(axes, panels):
        for index, (delta, curve) in enumerate(curves.items()):
            color = PALETTE[index % len(PALETTE)]
            ax.plot(
                k_values, curve, color=color, linewidth=1.1,
                marker='o', markersize=3,
                label=r'$\delta=' + f'{delta:g}' + r'$',
            )
        ax.set_yscale('log')
        ax.set_xlabel(r'$k$ (' + math_text('референсное значение') + ')')
        ax.set_title(
            title + ', ' + r'$\mathrm{ARL}_{IC}=' + f'{target:g}' + r'$',
            color=INK,
        )
        despine(ax)
        ax.legend(fontsize=8, frameon=False, ncol=2)

    axes[0].set_ylabel(r'$\mathrm{ARL}_{OOC}(k)$')
    figure.tight_layout()

    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / 'cusum_kh_design.png'
    figure.savefig(path, dpi=200)
    plt.close(figure)
    return path


def main() -> int:
    """Печать таблиц дизайна с одновременной записью в файл."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / 'cusum_kh_design.txt'
    with path.open('w', encoding='utf-8') as log, \
            redirect_stdout(Tee(sys.stdout, log)):
        code = _run()
    print(f'\nТаблицы сохранены: {path.relative_to(ROOT)}')
    return code


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


def _run() -> int:
    print('Совместный дизайн (k, h) CUSUM: ARL_OOC при номинальном ARL_IC')
    print('Источник: Chakraborti & Graham (2019), §3.2.2, стр. 67–72; '
          '§4.3.2, стр. 232–238')

    for n in SN_DESIGN_N:
        for target in TARGETS:
            print_design_table('SN', n, target)

    for n in SR_DESIGN_N:
        for target in TARGETS:
            print_design_table('SR', n, target)

    print('\nСверка с рис. 4.5 (n=10, k=6, двусторонняя, цель 500):')
    figure_4_5 = design_sign_h(10, 500, 6, sided='two')
    print(
        f'  h={figure_4_5.h:g}, ARL_IC={figure_4_5.arl:.2f} '
        f'(в книге 454.24) — используется при '
        f'k=6; совместный дизайн для δ=1: см. таблицу выше'
    )

    print('\nМинимакс-дизайн по сетке сдвигов (SN, n=10, ARL_IC=500):')
    minimax = design_sign_kh(
        10, 500, SN_DELTAS, sided='two', k_fractions=SN_K_FRACTIONS,
    )
    print(
        f'  k={minimax.k:g}, h={minimax.h:g}, ARL_IC={minimax.arl_ic:.2f}, '
        'ARL_OOC по δ: '
        + ', '.join(
            f'{delta:g}→{value:.2f}'
            for delta, value in sorted(minimax.ooc_by_delta.items())
        )
    )

    sn_k = np.arange(2, 10, 1.0)   # 2…9 < max|SN| = 10
    sr_k = np.arange(2, 15, 2.0)   # 2…14 < max|SR| = 15
    panels = [
        (
            'CUSUM-SN, n=10',
            500.0,
            sn_k,
            ooc_vs_k('SN', 10, 500.0, sn_k, SN_DELTAS),
        ),
        (
            'CUSUM-SR, n=5',
            500.0,
            sr_k,
            ooc_vs_k('SR', 5, 500.0, sr_k, SR_DELTAS),
        ),
    ]
    path = plot_panels(panels)

    print('\nВывод: для каждого δ существует своё k, минимизирующее '
          'ARL_OOC; при неизвестном размере сдвига малое k безопаснее '
          '(книга, §3.2.2, стр. 71). На грубой решётке SN/SR номинал '
          'ARL_IC часто недостижим точно: правило книги консервативное '
          '(ARL_IC ≤ номинала), поэтому err_ic — это «недобор» снизу.')
    print(f'\nГрафик сохранён: {path.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
