"""Вспомогательные функции для построения графиков.

Цвета берутся из единого стиля проекта
(:mod:`nonparametric_charts.utils.plot_style`) — семантические роли вместо
строк вида ``'red'``/``'green'``.
"""
from typing import Tuple

import matplotlib.pyplot as plt
import numpy as np

from nonparametric_charts.utils.plot_style import (
    ALERT,
    INK,
    ZONE_FILL,
    ZONE_LINE,
    hline,
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
