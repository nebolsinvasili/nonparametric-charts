"""
Пример 4.5 — знако-ранговая карта Шухарта (Shewhart-SR) с правилом серий
«2 из 2».

Источник
--------
Chakraborti, S. and Graham, M.A. (2019). *Nonparametric Statistical
Process Control*. John Wiley & Sons.
Раздел 4.3.1, пример 4.5, стр. 228–229, рисунок 4.13.

Что показывает пример
---------------------
Используются те же данные, что и в примере 4.4 (таблица 4.7a). Карта
дополняется улучшенным правилом «2 из 2»: сигнал подаётся, когда две
подряд идущие точки лежат на UWL/LWL или за ними (либо одна точка на
UCL/LCL). Предупреждающие границы заданы как

    UWL = +6,   LWL = −6   (при UCL/LCL = ±10).

Объяснение
----------
Значения SR_i = [2, −10, 10, −8, −2, 2, 10, −2, −8, −8, 10, 6, −8, 4,
−2, 0, 2, 10, −6, −2]. Правило «2 из 2» срабатывает на парах:

    (9, 10):  SR = −8, −8  (обе ≤ LWL = −6),
    (11, 12): SR = 10, 6   (обе ≥ UWL = +6).

Поэтому процесс объявляется OOC и требуется поиск назначенных причин.
Кроме того, подгруппа 2 (SR = −10) уже даёт одноточечный сигнал на LCL.

Замечание. Предупреждающие границы обычно подбирают по номинальному
ARL_IC; здесь (как и в книге) они заданы равными ±6 для иллюстрации.
"""

import pandas as pd
import pytest

from src.charts.signed_rank_chart import SignedRankChart

# Таблица 4.7a(a): 20 подгрупп по n = 4 (те же данные, что в примере 4.4).
DATA = [
    [-0.39, 0.03, 0.25, 0.30],
    [-0.61, -1.32, -2.84, -0.07],
    [2.04, 0.40, 0.54, 1.12],
    [-0.51, -1.63, 0.28, -0.96],
    [-0.20, -0.01, -0.21, 0.82],
    [2.03, 0.70, -1.21, -0.26],
    [0.64, 1.48, 0.91, 1.23],
    [0.19, -2.74, -0.85, 1.25],
    [-0.51, -1.77, -1.69, 0.24],
    [-0.84, -0.71, -0.82, 0.19],
    [0.29, 0.47, 0.04, 0.39],
    [0.38, 2.18, 1.24, -0.80],
    [-0.86, 0.61, -0.70, -1.13],
    [-0.31, 1.09, -0.43, 0.69],
    [0.42, 1.35, -0.51, -1.80],
    [0.39, -0.65, 1.57, -0.60],
    [1.31, -0.59, -0.21, 0.22],
    [0.64, 0.27, 0.26, 0.08],
    [-0.33, -0.49, 0.38, -1.54],
    [-0.48, -0.54, 1.73, -1.00],
]

SR_BOOK = [2, -10, 10, -8, -2, 2, 10, -2, -8, -8,
           10, 6, -8, 4, -2, 0, 2, 10, -6, -2]

UCL, LCL = 10, -10
UWL, LWL = 6, -6

# Книжные сигналы «2 из 2» (стр. 229).
TWO_OF_TWO_BOOK = [(9, 10), (11, 12)]


def _two_of_two(values: list[int], uwl: int, lwl: int) -> list[tuple[int, int]]:
    """Пары подряд идущих точек (1-based) на UWL/LWL или за ними."""
    hits = []
    for i in range(1, len(values)):
        a, b = values[i - 1], values[i]
        if (a >= uwl and b >= uwl) or (a <= lwl and b <= lwl):
            hits.append((i, i + 1))
    return hits


@pytest.fixture
def chart() -> SignedRankChart:
    return SignedRankChart(pd.DataFrame(DATA, columns=["x1", "x2", "x3", "x4"]),
                           sample_size=4, target_value=0.0)


def test_example_4_5_book_sr_statistics(chart) -> None:
    """Значения SR_i совпадают с таблицей 4.7b(c)."""
    chart.calculate_limits()
    assert chart.subgroups["sr"].tolist() == pytest.approx(SR_BOOK)


def test_example_4_5_two_of_two_signals(chart) -> None:
    """Правило «2 из 2» срабатывает на парах (9, 10) и (11, 12)."""
    chart.calculate_limits()
    sr = chart.subgroups["sr"].tolist()
    assert _two_of_two(sr, UWL, LWL) == TWO_OF_TWO_BOOK


def test_example_4_5_single_point_signal(chart) -> None:
    """Подгруппа 2 (SR = −10) даёт одноточечный сигнал на LCL."""
    chart.calculate_limits()
    assert 2 in [v["subgroup"] for v in chart.violations]


def test_example_4_5_plot_saved(chart, results_dir) -> None:
    """Карта с предупреждающими границами ±6 сохраняется с номером примера."""
    chart.calculate_limits()
    path = results_dir / "example_4_5_shewhart_sr_runs_2of2.png"

    fig, ax = chart.plot()
    ax.axhline(UWL, color='darkorange', linestyle='-.', linewidth=1.5,
               label=f'UWL = +{UWL}')
    ax.axhline(LWL, color='darkorange', linestyle='-.', linewidth=1.5,
               label=f'LWL = −{abs(LWL)}')
    ax.legend(loc='upper left', fontsize=9, ncol=2)
    fig.savefig(path, dpi=300, bbox_inches='tight')

    assert path.exists()
