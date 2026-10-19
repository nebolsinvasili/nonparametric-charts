"""
Единый академический LaTeX-стиль графиков.

Единственная точка настройки внешнего вида графиков проекта: serif-шрифт и
математика Computer Modern (mathtext), сдержанная палитра, отсутствие «мусора».
Все карты и примеры **обязаны** брать цвета и размеры отсюда, а не задавать
их строками вида ``'red'``/``'crimson'``.

Семантические роли цвета
------------------------
Вместо «сырых» названий цветов используются роли:

    INK        — текст, оси, тики, основные точки данных;
    ACCENT     — единственный акцент (линия данных);
    ALERT      — нарушения/сигналы (единый красный);
    CENTER     — центральная линия CL;
    LIMIT      — контрольные границы (±a, ±h);
    WARNING    — предупреждающие границы (UWL/LWL);
    ZONE_LINE  — линии границ зон A/B/C;
    ZONE_FILL  — заливка зон (только при ``fill_zones=True``);
    GRID       — сетка.

Использование
-------------
    from nonparametric_charts.utils.plot_style import (
        apply_minimal_latex_style, hline, ACCENT, ALERT, LIMIT, CENTER,
    )

    apply_minimal_latex_style()
    fig, ax = plt.subplots()
    hline(ax, 0, "center", label="CL")
    hline(ax, a, "limit", label=f"UCL = {a}")

По умолчанию ``usetex=True``: все подписи (включая кириллицу) набирает LaTeX
в Computer Modern. Для кириллицы подключены ``T2A``, ``utf8`` и ``babel russian``.
Если TeX в системе недоступен, можно вызвать ``apply_minimal_latex_style(usetex=False)``
— тогда используется mathtext (кириллица рендерится через DejaVu Serif).
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt

__all__ = [
    "INK",
    "ACCENT",
    "ALERT",
    "VIOLATION",
    "CENTER",
    "LIMIT",
    "WARNING",
    "ZONE_LINE",
    "ZONE_FILL",
    "GRID",
    "PALETTE",
    "ROLE_STYLES",
    "DATA_MARKER_SIZE",
    "SIGNAL_MARKER_SIZE",
    "apply_minimal_latex_style",
    "hline",
    "annotate_values",
    "math_text",
    "data_legend",
    "despine",
]

#: Преамбула LaTeX для кириллицы (T2A + babel russian) и ``\text{}``.
_CYRILLIC_PREAMBLE = (
    r"\usepackage[T2A]{fontenc}"
    r"\usepackage[utf8]{inputenc}"
    r"\usepackage[russian]{babel}"
    r"\usepackage{amsmath}"
)

#: Текст, оси, тики, основные точки данных.
INK: str = "#1A1A1A"
#: Основной акцентный цвет (линия данных; совпадает с ``BaseControlChart.color``).
ACCENT: str = "#2E86AB"
#: Нарушения/сигналы — единый сдержанный красный.
ALERT: str = "#B22222"
#: Обратная совместимость: цвет нарушений.
VIOLATION: str = ALERT
#: Центральная линия CL.
CENTER: str = "#808080"
#: Контрольные границы (±a, ±h) — сдержанный кирпичный тон.
LIMIT: str = "#8C4B3F"
#: Предупреждающие границы (UWL/LWL) — светлее границ.
WARNING: str = "#B5857B"
#: Линии границ зон A/B/C.
ZONE_LINE: str = "#B3B3B3"
#: Заливка зон (только при ``fill_zones=True``).
ZONE_FILL: str = "#ECECEC"
#: Сетка.
GRID: str = "#C8C8C8"

#: Базовый размер маркера данных — диаметр в пунктах (``markersize`` у ``plot``).
DATA_MARKER_SIZE: float = 4.0
#: Размер маркера сигнала/нарушения в ``scatter`` — площадь в pt². Вдвое
#: больше площади базового маркера: ``2 * DATA_MARKER_SIZE ** 2`` (диаметр
#: растёт в ``sqrt(2)`` раз).
SIGNAL_MARKER_SIZE: float = 2.0 * DATA_MARKER_SIZE ** 2

#: Сдержанная палитра для серий/сравнений (один акцент + приглушённые тона).
PALETTE: Sequence[str] = (
    "#2E86AB",  # синий (акцент)
    "#B22222",  # красный (alert)
    "#3C6E47",  # зелёный
    "#6A4C93",  # фиолетовый
    "#8A6D1F",  # тёмно-жёлтый
    "#34495E",  # грифельный
    "#7F7F7F",  # серый
)

#: Роль → (цвет, стиль линии, толщина).
ROLE_STYLES: dict[str, Tuple[str, str, float]] = {
    "ink":     (INK,       "-",  1.2),
    "accent":  (ACCENT,    "-",  1.2),
    "alert":   (ALERT,     "-",  1.2),
    "center":  (CENTER,    "-",  1.2),
    "limit":   (LIMIT,     "--", 1.3),
    "warning": (WARNING,   "-.", 1.2),
    "zone":    (ZONE_LINE, ":",  1.0),
    "grid":    (GRID,      ":",  0.6),
}

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
    usetex: bool = True,
    font_serif: Optional[Iterable[str]] = None,
    figsize: Tuple[float, float] = (10.0, 5.0),
) -> None:
    """
    Применить академический LaTeX-стиль к глобальным rcParams matplotlib.

    Parameters
    ----------
    usetex : bool, default=True
        Набирать все подписи внешним LaTeX (Computer Modern, включая
        кириллицу через T2A/babel). ``False`` — mathtext без внешнего TeX
        (кириллица через DejaVu Serif).
    font_serif : iterable of str, optional
        Приоритетный список serif-шрифтов (используется при ``usetex=False``).
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
        "axes.titleweight": "normal",
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
        "legend.frameon": True,
        "legend.facecolor": "white",
        "legend.edgecolor": ZONE_LINE,
        "legend.framealpha": 0.9,
        "legend.fancybox": True,
        "legend.handlelength": 1.6,
        # --- Сетка (по умолчанию выключена) ---
        "grid.color": GRID,
        "grid.linestyle": ":",
        "grid.linewidth": 0.6,
        "grid.alpha": 0.3,
        # --- Цвет ---
        "axes.prop_cycle": mpl.cycler(color=list(PALETTE)),
    }

    # Оставляем только поддерживаемые в текущей версии matplotlib ключи.
    valid = {k: v for k, v in params.items() if k in mpl.rcParams}
    mpl.rcParams.update(valid)

    if usetex:
        mpl.rcParams["text.latex.preamble"] = _CYRILLIC_PREAMBLE


def math_text(text: str) -> str:
    """
    Обернуть произвольный (в т.ч. кириллический) текст в math-режим.

    При ``usetex=True`` — ``\\text{...}`` (T2A + babel russian), при
    ``usetex=False`` — ``\\mathrm{...}`` (mathtext, кириллица через DejaVu
    Serif). Так все подписи, включая русские, набираются как формулы.
    """
    if mpl.rcParams.get("text.usetex", False):
        return r"$\text{" + text + r"}$"
    escaped = text.replace(" ", r"\ ")
    return r"$\mathrm{" + escaped + r"}$"


def hline(
    ax,
    y: float,
    role: str = "limit",
    *,
    label: Optional[str] = None,
    lw: Optional[float] = None,
    alpha: float = 1.0,
    zorder: float = 1,
):
    """
    Горизонтальная линия в стиле роли.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Оси графика.
    y : float
        Уровень линии.
    role : {'ink', 'accent', 'alert', 'center', 'limit', 'warning', 'zone', 'grid'}
        Семантическая роль (цвет, стиль и толщина из ``ROLE_STYLES``).
    label : str, optional
        Подпись для легенды.
    lw : float, optional
        Переопределить толщину.
    alpha : float, default=1.0
        Прозрачность.
    zorder : float, default=1
        Порядок отрисовки.
    """
    color, linestyle, width = ROLE_STYLES[role]
    return ax.axhline(
        y=y,
        color=color,
        linestyle=linestyle,
        linewidth=lw if lw is not None else width,
        alpha=alpha,
        label=label,
        zorder=zorder,
    )


def annotate_values(
    ax,
    x: Sequence[float],
    y: Sequence[float],
    *,
    mask: Optional[Sequence[bool]] = None,
    side: str = "auto",
    offset: Tuple[float, float] = (0, 4.0),
    fmt: str = "{:.1f}",
    fontsize: int = 9,
    color: str = INK,
) -> None:
    """
    Подписать значения точек в едином стиле проекта.

    Подпись набирается в math-режиме (``$...$``) и ставится от точки со
    смещением **в типографских пунктах** (``textcoords='offset points'``),
    поэтому зазор одинаков на любой карте, независимо от масштаба оси.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Оси графика.
    x, y : sequence of float
        Координаты подписываемых точек.
    mask : sequence of bool, optional
        Какие точки подписывать (по умолчанию — все).
    side : {'auto', 'above', 'below'}, default='auto'
        Куда ставить подпись: ``'auto'`` — над точкой при ``y >= 0`` и под ней
        иначе; ``'above'``/``'below'`` — всегда в одну сторону.
    offset : (float, float), default=(0, 4.0)
        Смещение в пунктах: ``dx`` по горизонтали, ``dy`` по вертикали
        (знак выбирается по ``side``/``y``).
    fmt : str, default='{:.1f}'
        Формат значения (без обрамляющих ``$``).
    fontsize : int, default=9
        Размер шрифта подписи.
    color : str, default=INK
        Цвет подписи.
    """
    dx, dy = offset
    mask_seq = None if mask is None else list(mask)

    for i, (xi, yi) in enumerate(zip(x, y)):
        if mask_seq is not None and not bool(mask_seq[i]):
            continue
        if side == "auto":
            above = float(yi) >= 0
        else:
            above = side == "above"
        ax.annotate(
            f"${fmt.format(yi)}$",
            xy=(xi, yi),
            xytext=(dx, dy if above else -dy),
            textcoords="offset points",
            fontsize=fontsize,
            color=color,
            ha="center",
            va="bottom" if above else "top",
        )


def data_legend(
    ax,
    lines: Sequence[str],
    *,
    loc: str = "upper right",
    bbox_to_anchor: Tuple[float, float] = (0.99, 0.99),
    **kwargs,
):
    """
    Блок данных в стиле легенды (без маркеров).

    Использует те же rcParams, что и легенда серий: рамка, фон, шрифт и
    отступы совпадают. Возвращает добавленную легенду (она регистрируется
    как artist, поэтому следующая ``ax.legend(...)`` её не заменит).
    """
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle

    handles = [Line2D([], [], linestyle="none") for _ in lines]
    legend = ax.legend(
        handles,
        list(lines),
        loc=loc,
        bbox_to_anchor=bbox_to_anchor,
        handlelength=0.0,
        handletextpad=0.0,
        borderaxespad=0.0,
        **kwargs,
    )
    ax.add_artist(legend)

    # Прозрачная «занятая» область в правом верхнем углу: ``loc='best'``
    # учитывает патчи и не ставит легенду серий поверх блока данных.
    ax.add_patch(
        Rectangle(
            (0.56, 0.76), 0.44, 0.24,
            transform=ax.transAxes,
            facecolor="none",
            edgecolor="none",
            linewidth=0.0,
        )
    )
    return legend


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
