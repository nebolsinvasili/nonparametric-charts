"""Тесты общих помощников стиля графиков.

Проверяют инварианты ``plot_style``: единый размер маркеров и неизменный
экранный зазор подписей значений (``annotate_values``) — он задаётся в
типографских пунктах и не зависит от масштаба оси.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

from nonparametric_charts.utils.plot_style import (
    DATA_MARKER_SIZE,
    SIGNAL_MARKER_SIZE,
    annotate_values,
)

TO_PX = 100.0 / 72.0  # 1 pt при явно заданном dpi=100


def _vertical_gaps(fig, ax) -> list[float]:
    """Вертикальные смещения подписей от их точек в пикселях."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    gaps = []
    for ann in ax.texts:
        _, point_py = ax.transData.transform(ann.xy)
        bbox = ann.get_window_extent(renderer)
        gaps.append(bbox.y0 - point_py if ann.get_va() == "bottom"
                    else point_py - bbox.y1)
    return gaps


def test_signal_marker_area_is_twice_the_data_marker() -> None:
    assert SIGNAL_MARKER_SIZE == 2 * DATA_MARKER_SIZE ** 2


def test_annotate_values_auto_places_labels_above_and_below() -> None:
    fig, ax = plt.subplots()
    ax.set_xlim(-1, 2)
    ax.set_ylim(-2, 2)
    annotate_values(ax, [0, 1], [1.0, -1.0], offset=(0, 4.0))

    assert [t.get_va() for t in ax.texts] == ["bottom", "top"]
    assert [t.get_text() for t in ax.texts] == ["$1.0$", "$-1.0$"]
    assert all(g > 0 for g in _vertical_gaps(fig, ax))


def test_annotate_values_gap_is_scale_independent() -> None:
    """Один и тот же зазор на осях с разным размахом (4.1 против 4.4)."""
    gaps = []
    for span in (2.0, 20.0):  # |SN| ≤ 1 и |SR| ≤ 10
        fig, ax = plt.subplots(dpi=100)
        ax.set_xlim(0, 2)
        ax.set_ylim(-span, span)
        annotate_values(ax, [1.0], [span / 2], offset=(0, 4.0))
        gaps.append(_vertical_gaps(fig, ax)[0])
        plt.close(fig)

    assert gaps[0] == pytest.approx(gaps[1], abs=0.5)
    assert gaps[0] == pytest.approx(4.0 * TO_PX, abs=0.5)


def test_annotate_values_mask_and_side() -> None:
    fig, ax = plt.subplots()
    ax.set_ylim(-1, 1)
    annotate_values(
        ax, [0, 1, 2], [0.0, -1.0, 0.0],
        side="below", mask=[True, True, False], fmt="{:.0f}",
    )

    assert [t.get_text() for t in ax.texts] == ["$0$", "$-1$"]
    assert all(t.get_va() == "top" for t in ax.texts)
