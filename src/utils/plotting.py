"""Вспомогательные функции для построения графиков"""
import matplotlib.pyplot as plt
import numpy as np
from typing import Tuple


def add_control_lines(ax, cl: float, ucl: float, lcl: float,
                      label_cl: str = 'CL', label_ucl: str = 'UCL',
                      label_lcl: str = 'LCL'):
    """Добавление контрольных линий на график"""
    ax.axhline(y=cl, color='green', linestyle='-',
               linewidth=2, label=f'{label_cl} = {cl:.3f}')
    ax.axhline(y=ucl, color='red', linestyle='--',
               linewidth=2, label=f'{label_ucl} = {ucl:.3f}')
    ax.axhline(y=lcl, color='red', linestyle='--',
               linewidth=2, label=f'{label_lcl} = {lcl:.3f}')


def add_zones(ax, cl: float, ucl: float, lcl: float):
    """Добавление зон Вестерн-Электрик"""
    if ucl <= cl or lcl >= cl:
        return
    
    zone_width = (ucl - cl) / 3
    
    ax.axhspan(cl + 2*zone_width, ucl, alpha=0.1, color='yellow', label='Зона A')
    ax.axhspan(lcl, cl - 2*zone_width, alpha=0.1, color='yellow')
    ax.axhspan(cl + zone_width, cl + 2*zone_width, alpha=0.1, color='orange', label='Зона B')
    ax.axhspan(cl - 2*zone_width, cl - zone_width, alpha=0.1, color='orange')
    ax.axhspan(cl - zone_width, cl + zone_width, alpha=0.1, color='lightgreen', label='Зона C')


def add_values_on_points(ax, x_values: np.ndarray, y_values: np.ndarray,
                         cl: float, ucl: float, lcl: float,
                         value_format: str = '{:.3f}', fontsize: int = 9,
                         offset: tuple = (0, 0.05)):
    """Добавление значений на точки"""
    dx, dy = offset
    zone_width = (ucl - cl) / 3 if ucl > cl else 1
    
    for x, y in zip(x_values, y_values):
        if y > ucl or y < lcl:
            color = 'red'
            weight = 'bold'
        elif y > cl + 2*zone_width or y < cl - 2*zone_width:
            color = 'darkorange'
            weight = 'bold'
        elif y > cl + zone_width or y < cl - zone_width:
            color = 'orange'
            weight = 'normal'
        else:
            color = 'darkgreen'
            weight = 'normal'
        
        ax.text(x + dx, y + dy, value_format.format(y),
                fontsize=fontsize, color=color, fontweight=weight,
                ha='center', va='bottom' if dy >= 0 else 'top',
                bbox=dict(boxstyle='round,pad=0.2',
                         facecolor='white', edgecolor='none', alpha=0.7))