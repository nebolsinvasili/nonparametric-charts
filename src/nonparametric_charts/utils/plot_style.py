"""
Минималистичный LaTeX-стиль графиков.

Единая точка настройки внешнего вида графиков проекта: serif-шрифт и математика
Computer Modern (mathtext), отсутствие «мусора», сдержанная палитра.

Использование
-------------
    from src.utils.plot_style import apply_minimal_latex_style, despine

    apply_minimal_latex_style()
    fig, ax = plt.subplots()
    ...
    despine(ax)

По умолчанию ``usetex=False``: сборка через mathtext не требует внешнего TeX и
корректно работает с кириллицей в обычном тексте (кириллицу нельзя класть в
``$...$``). Включение ``usetex=True`` — только по явной необходимости.
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt

__all__ = [
    "ACCENT",
    "VIOLATION",
    "PALETTE",
    "apply_minimal_latex_style",
    "despine",
]

#: Основной акцентный цвет (совпадает с BaseControlChart.color).
ACCENT: str = "#2E86AB"
#: Цвет нарушений/выбросов.
VIOLATION: str = "#C0392B"
#: Сдержанная палитра для серий/сравнений.
PALETTE: Sequence[str] = (
    "#2E86AB",  # синий
    "#C0392B",  # красный
    "#1E8449",  # зелёный
    "#7D3C98",  # фиолетовый
    "#B9770E",  # тёмно-жёлтый
    "#34495E",  # грифельный
    "#808080",  # серый
)

#: Кандидаты serif-шрифтов (с поддержкой кириллицы — первым).
_DEFAULT_SERIF = (
    "DejaVu Serif",
    "Latin Modern Roman",
    "Computer Modern Roman",
    "CMU Serif",
    "Times New Roman",
    "serif",
)


def apply_minimal_latex_style(
    usetex: bool = False,
    font_serif: Optional[Iterable[str]] = None,
    figsize: Tuple[float, float] = (10.0, 5.0),
) -> None:
    """
    Применить минималистичный LaTeX-стиль к глобальным rcParams matplotlib.

    Parameters
    ----------
    usetex : bool, default=False
        Использовать внешний LaTeX для формул. По умолчанию mathtext
        (Computer Modern), чтобы не тянуть TeX-пакеты и не ломать кириллицу.
    font_serif : iterable of str, optional
        Приоритетный список serif-шрифтов. По умолчанию — с DejaVu Serif.
    figsize : (float, float), default=(10, 5)
        Размер фигуры по умолчанию.
    """
    serif = list(font_serif) if font_serif is not None else list(_DEFAULT_SERIF)

    params = {
        # --- Шрифты и математика ---
        "font.family": "serif",
        "font.serif": serif,
        "mathtext.fontset": "cm",          # Computer Modern для $...$
        "text.usetex": bool(usetex),
        # --- Размеры ---
        "figure.figsize": figsize,
        "figure.dpi": 120,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        # --- Оси и рамки ---
        "axes.edgecolor": "#333333",
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.top": False,
        "ytick.right": False,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "xtick.major.size": 3.0,
        "ytick.major.size": 3.0,
        # --- Линии и маркеры ---
        "lines.linewidth": 1.2,
        "lines.markersize": 4.5,
        "lines.solid_capstyle": "round",
        # --- Легенда ---
        "legend.frameon": False,
        "legend.handlelength": 1.6,
        # --- Сетка (по умолчанию выключена) ---
        "grid.linestyle": ":",
        "grid.linewidth": 0.6,
        "grid.alpha": 0.3,
        # --- Цвет ---
        "axes.prop_cycle": mpl.cycler(color=list(PALETTE)),
    }

    # Оставляем только поддерживаемые в текущей версии matplotlib ключи.
    valid = {k: v for k, v in params.items() if k in mpl.rcParams}
    mpl.rcParams.update(valid)


def despine(
    ax,
    *,
    left: bool = True,
    bottom: bool = True,
) -> None:
    """
    Убрать верхнюю и правую рамки (минимализм), оставив левую и нижнюю.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Оси для оформления.
    left, bottom : bool, default=True
        Оставлять ли соответствующую рамку.
    """
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(left)
    ax.spines["bottom"].set_visible(bottom)
