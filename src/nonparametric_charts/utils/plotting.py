"""Вспомогательные функции для построения графиков.

Цвета берутся из единого стиля проекта
(:mod:`nonparametric_charts.utils.plot_style`) — семантические роли вместо
строк вида ``'red'``/``'green'``.
"""
from typing import Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np

from nonparametric_charts.utils.plot_style import (
    ACCENT,
    ALERT,
    INK,
    ZONE_FILL,
    ZONE_LINE,
    apply_minimal_latex_style,
    despine,
    hline,
    math_text,
)


def add_control_lines(ax, cl: float, ucl: float, lcl: float,
                      label_cl: str = 'CL', label_ucl: str = 'UCL',
                      label_lcl: str = 'LCL'):
    """Добавление контрольных линий на график (CL — центр, UCL/LCL — границы)."""
    hline(ax, cl, "center", label=f'{label_cl} = {cl:.3f}')
    hline(ax, ucl, "limit", label=f'{label_ucl} = {ucl:.3f}')
    hline(ax, lcl, "limit", label=f'{label_lcl} = {lcl:.3f}')


def add_zones(ax, cl: float, ucl: float, lcl: float):
    """Добавление зон Вестерн-Электрик (сдержанная серая заливка)."""
    if ucl <= cl or lcl >= cl:
        return

    zone_width = (ucl - cl) / 3

    ax.axhspan(cl + 2*zone_width, ucl, alpha=0.5, color=ZONE_FILL, zorder=0)
    ax.axhspan(lcl, cl - 2*zone_width, alpha=0.5, color=ZONE_FILL, zorder=0)
    ax.axhspan(cl + zone_width, cl + 2*zone_width, alpha=0.5,
               color=ZONE_FILL, zorder=0)
    ax.axhspan(cl - 2*zone_width, cl - zone_width, alpha=0.5,
               color=ZONE_FILL, zorder=0)
    ax.axhspan(cl - zone_width, cl + zone_width, alpha=0.5,
               color=ZONE_FILL, zorder=0)
    for level in (cl + zone_width, cl + 2*zone_width,
                  cl - zone_width, cl - 2*zone_width):
        ax.axhline(level, color=ZONE_LINE, linestyle=":", linewidth=0.8,
                   zorder=1)


def add_values_on_points(ax, x_values: np.ndarray, y_values: np.ndarray,
                         cl: float, ucl: float, lcl: float,
                         value_format: str = '{:.3f}', fontsize: int = 9,
                         offset: tuple = (0, 0.05)):
    """Добавление значений на точки (``ALERT`` — вне границ, иначе ``INK``)."""
    dx, dy = offset

    for x, y in zip(x_values, y_values):
        color = ALERT if (y > ucl or y < lcl) else INK
        ax.text(x + dx, y + dy, value_format.format(y),
                fontsize=fontsize, color=color,
                ha='center', va='bottom' if dy >= 0 else 'top')


def plot_run_length(
    result,
    *,
    ax=None,
    figsize: Tuple[float, float] = (10.0, 5.5),
    title: Optional[str] = None,
    max_t: Optional[int] = None,
    show_cdf: bool = True,
    show_stats: bool = True,
    usetex: bool = True,
    save_path: Optional[str] = None,
) -> Tuple[plt.Figure, plt.Axes]:
    """
    График распределения длины серии (RL).

    PMF рисуется столбиками и точками на левой оси, CDF — ступенчатой
    линией на правой оси. Оформление — единый стиль проекта
    (:func:`apply_minimal_latex_style`).

    Parameters
    ----------
    result : RunLengthResult
        Результат :func:`cusum_run_length` или методов ``run_length()`` карт.
    ax : matplotlib.axes.Axes, optional
        Готовые оси для PMF; при ``None`` создаётся новая фигура.
    figsize : (float, float), default=(10, 5.5)
        Размер фигуры.
    title : str, optional
        Заголовок; по умолчанию — название статистики и характеристики RL.
    max_t : int, optional
        Показать только ``t ≤ max_t`` (полезно при длинном усечённом хвосте).
    show_cdf : bool, default=True
        Рисовать ли CDF на правой оси.
    show_stats : bool, default=True
        Добавлять ли к заголовку строку с ``ARL``/``SDRL``/``MRL``.
    usetex : bool, default=True
        Набирать подписи внешним LaTeX (см. ``plot_style``).
    save_path : str, optional
        Путь для сохранения рисунка (300 dpi, ``bbox='tight'``).

    Returns
    -------
    (matplotlib.figure.Figure, matplotlib.axes.Axes)
        Фигура и левая ось (ось PMF); ось CDF при ``show_cdf=True`` —
        ``fig.axes[1]``.

    Notes
    -----
    Распределение RL — ур. 3.22–3.24 (стр. 112); для CUSUM-карт —
    ур. 4.9/4.12 (стр. 203, 206).
    """
    if result.pmf is None or len(result.pmf) == 0:
        raise ValueError('Пустое распределение длины серии')
    if max_t is not None and max_t < 1:
        raise ValueError(f'max_t должен быть ≥ 1, получено {max_t}')

    apply_minimal_latex_style(usetex=usetex)

    pmf = np.asarray(result.pmf, dtype=float)
    cdf = np.asarray(result.cdf, dtype=float)
    n_points = len(pmf) if max_t is None else min(int(max_t), len(pmf))
    t = np.arange(1, n_points + 1)

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    ax.vlines(t, 0.0, pmf[:n_points], color=ACCENT, linewidth=1.0, zorder=2)
    ax.plot(t, pmf[:n_points], 'o', color=ACCENT, markersize=4.0,
            label=r'$P(N=t)$', zorder=3)
    ax.set_xlabel(r'$t$ (' + math_text('длина серии') + ')')
    ax.set_ylabel(r'$P(N=t)$', color=ACCENT)
    ax.tick_params(axis='y', colors=ACCENT)
    ax.set_xlim(0.5, n_points + 0.5)
    ax.set_ylim(0.0, max(float(pmf[:n_points].max()) * 1.2, 1e-3))

    handles = list(ax.get_lines())
    if show_cdf:
        ax_cdf = ax.twinx()
        ax_cdf.step(t, cdf[:n_points], where='post', color=INK,
                    linewidth=1.2, label=r'$F(t)=P(N \leq t)$', zorder=2)
        ax_cdf.set_ylabel(r'$F(t)$', color=INK)
        ax_cdf.set_ylim(0.0, 1.05)
        despine(ax_cdf)
        handles += list(ax_cdf.get_lines())

    ax.legend(handles, [line.get_label() for line in handles],
              loc='center right')

    if title is None:
        statistic = str(result.metadata.get('statistic', '')).upper()
        prefix = f'CUSUM-{statistic} — ' if statistic in {'SN', 'SR'} else ''
        title = prefix + math_text('распределение длины серии')
    if show_stats:
        title += ('\n'
                  + rf'$\mathrm{{ARL}} = {result.arl:.2f}$, '
                    rf'$\mathrm{{SDRL}} = {result.sdrl:.2f}$, '
                    rf'$\mathrm{{MRL}} = {result.mrl}$')
        if result.truncated:
            title += '  ' + math_text('(хвост отсечён)')
    ax.set_title(title)

    despine(ax)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f'График сохранён: {save_path}')
    return fig, ax
