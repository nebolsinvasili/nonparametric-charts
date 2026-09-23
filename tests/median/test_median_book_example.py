"""
Тесты Me контрольной карты Шухарта (карта медиан) по примеру из книги:

В. Н. Клячкин, «Статистические методы в управлении качеством»,
§4.1.5, пример 4.2, рис. 4.4 и 4.5 (Me-R карты).

Контролируется средний вес упаковки продукта на автоматической линии (г).
Каждый час взвешиваются по 3 упаковки — 20 подгрупп (n = 3).
Медианой при нечетном n является средний член вариационного ряда.

Результаты, приведенные в книге:
    Mē = 504,45;   R̄ = 7,45;   A4 = 1,19 (n = 3);
    UCL = 504,45 + 1,19·7,45 = 513,31;
    LCL = 504,45 − 1,19·7,45 = 495,58;
при n = 3 медиана — второй (средний) элемент вариационного ряда.
"""

import pandas as pd
import pytest

from src.charts.median_chart import MedianChart
from src.charts.xbar_chart import XBarChart
from tests.conftest import COEFFICIENTS_FILE

# Данные контрольного листка (рис. 4.4): каждая строка — подгруппа,
# каждый столбец — одно измерение. Размер подгруппы n = 3.
BOOK_DATA = pd.DataFrame(
    [
        [510, 505, 496],
        [508, 512, 501],
        [499, 501, 504],
        [506, 504, 500],
        [508, 507, 499],
        [500, 504, 504],
        [501, 496, 511],
        [502, 504, 509],
        [507, 510, 501],
        [502, 504, 500],
        [501, 506, 498],
        [496, 499, 503],
        [513, 508, 509],
        [510, 506, 507],
        [504, 505, 508],
        [506, 507, 512],
        [513, 510, 508],
        [504, 506, 500],
        [496, 501, 509],
        [501, 503, 508],
    ],
    columns=[f"m{i}" for i in range(1, 4)],
)

# Медианы Ме и размахи R по подгруппам (колонки контрольного листка).
BOOK_SAMPLE_MEDIANS = [
    505,
    508,
    501,
    504,
    507,
    504,
    501,
    504,
    507,
    502,
    501,
    499,
    509,
    507,
    505,
    507,
    510,
    504,
    501,
    503,
]
BOOK_SAMPLE_RANGES = [
    14,
    11,
    5,
    6,
    9,
    4,
    15,
    7,
    9,
    4,
    8,
    7,
    5,
    4,
    4,
    6,
    5,
    6,
    13,
    7,
]

# Итоговые величины из книги.
BOOK_MEAN_MEDIAN = 504.45  # (505 + 508 + ... + 503) / 20
BOOK_MEAN_RANGE = 7.45  # (14 + 11 + ... + 7) / 20
BOOK_A4 = 1.19
BOOK_UCL = BOOK_MEAN_MEDIAN + BOOK_A4 * BOOK_MEAN_RANGE  # ≈ 513.3155 → 513.31
BOOK_LCL = BOOK_MEAN_MEDIAN - BOOK_A4 * BOOK_MEAN_RANGE  # ≈ 495.5845 → 495.58


@pytest.fixture
def chart() -> MedianChart:
    """Me карта по данным книги."""
    return MedianChart(
        BOOK_DATA,
        sample_size=3,
        coefficients_file=str(COEFFICIENTS_FILE),
    )


def test_book_example_subgroup_medians(chart) -> None:
    """Медианы подгрупп совпадают с колонкой Ме контрольного листка."""
    medians = BOOK_DATA.median(axis=1)
    chart.calculate_limits()
    stat = chart.subgroups["statistic"].tolist()
    assert stat == pytest.approx(medians, abs=1e-9)
    assert stat == pytest.approx(BOOK_SAMPLE_MEDIANS, abs=1e-9)


def test_book_example_subgroup_ranges(chart) -> None:
    """Размахи подгрупп совпадают с колонкой R контрольного листка."""
    chart.calculate_limits()
    ranges = BOOK_DATA.max(axis=1) - BOOK_DATA.min(axis=1)
    assert chart.subgroups["range"].tolist() == pytest.approx(ranges, abs=1e-9)
    assert chart.subgroups["range"].tolist() == pytest.approx(
        BOOK_SAMPLE_RANGES, abs=1e-9
    )


def test_book_example_mean_median_and_mean_range(chart) -> None:
    """Mē и R̄ соответствуют значениям книги 504,45 и 7,45."""
    limits = chart.calculate_limits()
    assert limits["CL"] == pytest.approx(BOOK_MEAN_MEDIAN, rel=1e-12)
    assert limits["mean_range"] == pytest.approx(BOOK_MEAN_RANGE, rel=1e-12)


def test_book_example_a4_coefficient(chart) -> None:
    """Коэффициент A4 для n = 3 равен 1.19 (табл. П6 книги)."""
    chart.calculate_limits()
    assert chart.control_limits["A4"] == pytest.approx(BOOK_A4, rel=1e-12)
    assert chart.get_coefficient("A4") == pytest.approx(BOOK_A4, rel=1e-12)


def test_book_example_control_limits(chart) -> None:
    """Контрольные границы совпадают с границами из книги (513.31 и 495.58)."""
    limits = chart.calculate_limits()
    assert limits["UCL"] == pytest.approx(BOOK_UCL, rel=1e-12)
    assert limits["UCL"] == pytest.approx(513.31, abs=0.01)
    assert limits["LCL"] == pytest.approx(BOOK_LCL, rel=1e-12)
    assert limits["LCL"] == pytest.approx(495.58, abs=0.01)


def test_book_example_process_in_control(chart) -> None:
    """Ни одна точка не выходит за границы — процесс не требует регулировки."""
    chart.calculate_limits()
    assert chart.subgroups["outside"].sum() == 0
    assert chart.violations == []


def test_book_example_plot_returns_figure_and_axes(chart) -> None:
    """Построение карты возвращает фигуру и оси без ошибок."""
    fig, ax = chart.plot()
    assert fig is not None
    assert ax is not None
    assert len(ax.get_lines()) >= 4  # данные + CL + UCL + LCL


def test_book_example_summary(chart) -> None:
    """Сводка карты содержит корректные метаданные и книжный результат."""
    summary = chart.get_summary()
    assert summary["chart_type"] == "Median"
    assert summary["sample_size"] == 3
    assert summary["total_subgroups"] == 20
    assert summary["mean_median"] == pytest.approx(504.45, rel=1e-9)
    assert summary["mean_range"] == pytest.approx(7.45, rel=1e-9)
    assert summary["points_outside"] == 0
    assert summary["percent_outside"] == 0
    assert summary["violations"] == []
    assert summary["ucl"] == pytest.approx(513.31, abs=0.01)
    assert summary["lcl"] == pytest.approx(495.58, abs=0.01)
    assert summary["min_median"] == 499.0
    assert summary["max_median"] == 510.0


def test_class_matches_manual_calculation(chart) -> None:
    """Результаты класса совпадают с независимым ручным расчётом на pandas."""
    # Независимый ручной расчёт по формулам книги.
    medians = BOOK_DATA.median(axis=1)
    ranges = BOOK_DATA.max(axis=1) - BOOK_DATA.min(axis=1)
    mean_median = medians.mean()
    mean_range = ranges.mean()
    a4 = 1.19  # для n = 3
    manual_ucl = mean_median + a4 * mean_range
    manual_lcl = mean_median - a4 * mean_range

    limits = chart.calculate_limits()

    assert limits["CL"] == pytest.approx(mean_median, rel=1e-9)
    assert limits["mean_range"] == pytest.approx(mean_range, rel=1e-9)
    assert limits["UCL"] == pytest.approx(manual_ucl, rel=1e-9)
    assert limits["LCL"] == pytest.approx(manual_lcl, rel=1e-9)
    outside_flags = (medians > manual_ucl) | (medians < manual_lcl)
    manual_outside = set((medians.index + 1)[outside_flags])
    outside = chart.subgroups["subgroup"][chart.subgroups["outside"]]
    assert set(outside) == manual_outside


def test_subgroups_dataframe_structure(chart) -> None:
    """DataFrame подгрупп класса содержит нужные колонки и нумерацию 1..20."""
    chart.calculate_limits()
    expected_columns = ["subgroup", "statistic", "range", "outside"]
    assert list(chart.subgroups.columns) == expected_columns
    assert chart.subgroups["subgroup"].tolist() == list(range(1, 21))
    assert chart.subgroups["outside"].dtype == bool


def test_get_data_returns_copy(chart) -> None:
    """get_data() копирует подгруппы и не меняет состояние класса."""
    chart.calculate_limits()
    data = chart.get_data()
    assert data.equals(chart.subgroups)
    data.loc[0, "statistic"] = -999  # изменение копии не влияет на класс
    assert chart.subgroups.loc[0, "statistic"] != -999


def test_get_control_limits_calculates_lazily() -> None:
    """get_control_limits() запускает расчёт, если границы ещё не посчитаны."""
    chart = MedianChart(
        BOOK_DATA,
        sample_size=3,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    assert chart.control_limits is None
    limits = chart.get_control_limits()
    assert limits["UCL"] == pytest.approx(BOOK_UCL, rel=1e-9)
    assert chart.control_limits is not None


def test_get_summary_calculates_lazily() -> None:
    """get_summary() запускает расчёт, если границы ещё не посчитаны."""
    chart = MedianChart(
        BOOK_DATA,
        sample_size=3,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    summary = chart.get_summary()
    assert summary["total_subgroups"] == 20
    assert "UCL" in summary or chart.control_limits is not None


def test_plot_saves_to_path(chart, tmp_path) -> None:
    """plot(save_path=...) сохраняет изображение по указанному пути."""
    target = tmp_path / "me_book.png"
    fig, ax = chart.plot(save_path=str(target), show_values=False)
    assert target.exists()
    assert target.stat().st_size > 0
    assert fig is not None and ax is not None


def test_median_is_robust_center() -> None:
    """Медиана робастна к выбросам: центр карты медиан устойчивее X-bar."""
    # В одной подгруппе два аномально больших значения.
    data = pd.DataFrame([[1.0, 2.0, 100.0], [3.0, 4.0, 5.0]])
    me_chart = MedianChart(
        data,
        sample_size=3,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    xbar_chart = XBarChart(
        data,
        sample_size=3,
        center_method="mean",
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    me_limits = me_chart.calculate_limits()
    xbar_limits = xbar_chart.calculate_limits()

    assert me_chart.subgroups["statistic"].tolist() == [2.0, 4.0]
    assert abs(me_limits["CL"] - 3.0) < 1e-9  # (2 + 4) / 2
    assert xbar_limits["CL"] > 17  # среднее сильно смещено выбросом


def test_data_csv_robust_median_no_violations() -> None:
    """На data.csv медианная карта робастна и не даёт ложных нарушений."""
    df = pd.read_csv("data/data.csv")
    chart = MedianChart(
        df,
        sample_size=14,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    summary = chart.get_summary()
    assert summary["total_subgroups"] == 10
    assert summary["A4"] == pytest.approx(0.399, rel=1e-9)
    assert summary["points_outside"] == 0
    assert summary["violations"] == []
    assert summary["lcl"] < summary["mean_median"] < summary["ucl"]
