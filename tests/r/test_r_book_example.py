"""
Тесты R контрольной карты Шухарта (карта размахов) по примеру из книги:

В. Н. Клячкин, «Статистические методы в управлении качеством»,
§2.7, рис. 2.3 и 2.13 (карты средних и размахов по контрольному листку).

Контролируется отклонение диаметра вала от номинала (мкм).
Каждые 30 минут берется выборка из 5 деталей, всего 11 подгрупп.

Результаты, приведенные в книге:
    R̄ = 3,45;   D3 = 0;   D4 = 2,115;
    UCL = 2,115·3,45 = 7,30;   LCL = 0;
вывод: выходов за границы нет, процесс не требует регулировки.
"""

import pandas as pd
import pytest

from src.charts.r_chart import RChart
from tests.conftest import COEFFICIENTS_FILE

# Данные контрольного листка (рис. 2.3): каждая строка — подгруппа (выборка),
# каждый столбец — одно измерение в подгруппе. Размер подгруппы n = 5.
BOOK_DATA = pd.DataFrame(
    [
        [2, 3, 2, 5, 3],
        [3, 2, 2, 1, 4],
        [3, 5, 2, 2, 3],
        [4, 2, 1, 3, 5],
        [2, 5, 3, 6, 2],
        [4, 5, 5, 3, 2],
        [2, 3, 3, 5, 4],
        [5, 4, 2, 2, 1],
        [3, 3, 6, 2, 1],
        [2, 4, 4, 3, 5],
        [4, 2, 5, 3, 3],
    ],
    columns=[f"m{i}" for i in range(1, 6)],
)

# Размахи R по подгруппам (строка контрольного листка).
BOOK_SAMPLE_RANGES = [3, 3, 3, 4, 4, 3, 3, 4, 5, 3, 3]

# Итоговые величины из книги.
BOOK_MEAN_RANGE = 38 / 11  # ≈ 3.4545 → 3.45 в книге
BOOK_D3 = 0
BOOK_D4 = 2.114  # из src/utils/coefficients.json (в книге 2,115)
BOOK_D4_BOOK = 2.115
BOOK_UCL = BOOK_D4 * BOOK_MEAN_RANGE  # ≈ 7.3029 → 7.30 в книге
BOOK_LCL = BOOK_D3 * BOOK_MEAN_RANGE  # = 0


@pytest.fixture
def chart() -> RChart:
    """R карта по данным книги."""
    return RChart(
        BOOK_DATA,
        sample_size=5,
        coefficients_file=str(COEFFICIENTS_FILE),
    )


def test_book_example_subgroup_ranges(chart) -> None:
    """Размахи подгрупп совпадают со строкой R контрольного листка."""
    chart.calculate_limits()
    assert chart.subgroups["statistic"].tolist() == pytest.approx(
        BOOK_SAMPLE_RANGES, abs=1e-9
    )


def test_book_example_mean_range(chart) -> None:
    """Средний размах R̄ соответствует значению книги 3,45."""
    limits = chart.calculate_limits()
    assert limits["CL"] == pytest.approx(BOOK_MEAN_RANGE, rel=1e-12)
    assert limits["CL"] == pytest.approx(3.45, abs=0.005)


def test_book_example_d3_d4_coefficients(chart) -> None:
    """Коэффициенты D3 и D4 для n = 5 соответствуют табл. П6 книги."""
    chart.calculate_limits()
    assert chart.control_limits["D3"] == pytest.approx(BOOK_D3, rel=1e-12)
    assert chart.control_limits["D4"] == pytest.approx(BOOK_D4, rel=1e-12)
    assert chart.get_coefficient("D3") == pytest.approx(BOOK_D3, rel=1e-12)
    assert chart.get_coefficient("D4") == pytest.approx(BOOK_D4, rel=1e-12)


def test_book_example_control_limits(chart) -> None:
    """Контрольные границы совпадают с границами из книги (7.30 и 0)."""
    limits = chart.calculate_limits()
    assert limits["UCL"] == pytest.approx(BOOK_UCL, rel=1e-12)
    assert limits["UCL"] == pytest.approx(7.30, abs=0.01)
    assert limits["LCL"] == pytest.approx(BOOK_LCL, rel=1e-12)
    assert limits["LCL"] == 0


def test_book_example_manual_rounding_matches_book(chart) -> None:
    """Округлённый расчёт как в книге: 2,115·3,45 = 7,30; LCL = 0."""
    limits = chart.calculate_limits()
    r_bar = round(limits["CL"], 2)  # 3.45
    manual_ucl = BOOK_D4_BOOK * r_bar
    assert manual_ucl == pytest.approx(7.30, abs=0.005)
    assert limits["UCL"] == pytest.approx(manual_ucl, abs=0.01)


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
    assert summary["chart_type"] == "R"
    assert summary["sample_size"] == 5
    assert summary["total_subgroups"] == 11
    assert summary["mean_range"] == pytest.approx(3.45, abs=0.005)
    assert summary["points_outside"] == 0
    assert summary["percent_outside"] == 0
    assert summary["violations"] == []
    assert summary["ucl"] == pytest.approx(7.30, abs=0.01)
    assert summary["lcl"] == 0
    assert summary["max_range"] == 5
    assert summary["min_range"] == 3


def test_class_matches_manual_calculation(chart) -> None:
    """Результаты класса совпадают с независимым ручным расчётом на pandas."""
    # Независимый ручной расчёт по формулам книги.
    ranges = BOOK_DATA.max(axis=1) - BOOK_DATA.min(axis=1)
    mean_range = ranges.mean()
    d3 = 0  # для n = 5 (табл. П6)
    d4 = 2.114
    manual_ucl = d4 * mean_range
    manual_lcl = d3 * mean_range

    limits = chart.calculate_limits()

    assert limits["CL"] == pytest.approx(mean_range, rel=1e-9)
    assert limits["UCL"] == pytest.approx(manual_ucl, rel=1e-9)
    assert limits["LCL"] == pytest.approx(manual_lcl, rel=1e-9)
    outside_flags = (ranges > manual_ucl) | (ranges < manual_lcl)
    manual_outside = set((ranges.index + 1)[outside_flags])
    outside = chart.subgroups["subgroup"][chart.subgroups["outside"]]
    assert set(outside) == manual_outside


def test_subgroups_dataframe_structure(chart) -> None:
    """DataFrame подгрупп класса содержит нужные колонки и нумерацию 1..11."""
    chart.calculate_limits()
    expected_columns = ["subgroup", "statistic", "outside"]
    assert list(chart.subgroups.columns) == expected_columns
    assert chart.subgroups["subgroup"].tolist() == list(range(1, 12))
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
    chart = RChart(
        BOOK_DATA,
        sample_size=5,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    assert chart.control_limits is None
    limits = chart.get_control_limits()
    assert limits["UCL"] == pytest.approx(BOOK_UCL, rel=1e-9)
    assert chart.control_limits is not None


def test_get_summary_calculates_lazily() -> None:
    """get_summary() запускает расчёт, если границы ещё не посчитаны."""
    chart = RChart(
        BOOK_DATA,
        sample_size=5,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    summary = chart.get_summary()
    assert summary["total_subgroups"] == 11
    assert "UCL" in summary or chart.control_limits is not None


def test_plot_saves_to_path(chart, tmp_path) -> None:
    """plot(save_path=...) сохраняет изображение по указанному пути."""
    target = tmp_path / "r_book.png"
    fig, ax = chart.plot(save_path=str(target), show_values=False)
    assert target.exists()
    assert target.stat().st_size > 0
    assert fig is not None and ax is not None


def test_lcl_zero_for_small_subgroup_size() -> None:
    """При n < 7 нижняя граница карты размахов равна нулю (D3 = 0)."""
    for n in (2, 3, 4, 5, 6):
        chart = RChart(
            BOOK_DATA,
            sample_size=n,
            coefficients_file=str(COEFFICIENTS_FILE),
        )
        limits = chart.calculate_limits()
        assert limits["LCL"] == 0
        assert limits["D3"] == 0


def test_data_csv_detects_violations() -> None:
    """На data.csv карта размахов находит 5 нарушений."""
    df = pd.read_csv("data/data.csv")
    chart = RChart(
        df,
        sample_size=14,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    summary = chart.get_summary()
    assert summary["total_subgroups"] == 10
    assert summary["D4"] == pytest.approx(1.672, rel=1e-9)
    assert summary["D3"] == pytest.approx(0.328, rel=1e-9)
    assert summary["lcl"] > 0  # при n = 14 нижняя граница ненулевая
    assert summary["points_outside"] == 5
    assert [v["subgroup"] for v in summary["violations"]] == [1, 3, 5, 6, 10]
