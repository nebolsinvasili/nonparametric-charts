"""
Тесты X-bar контрольной карты Шухарта по примеру из книги:

В. Н. Клячкин, «Статистические методы в управлении качеством»,
§2.7, рис. 2.3 (контрольный листок для анализа стабильности процесса).

Контролируется отклонение диаметра вала от номинала (мкм).
Каждые 30 минут берется выборка из 5 деталей, всего 11 подгрупп.

Результаты, приведенные в книге:
    x̄̄ = 3,18;   R̄ = 3,45;   A2 = 0,577;
    UCL = 3,18 + 0,577·3,45 = 5,17;
    LCL = 3,18 − 0,577·3,45 = 1,19;
вывод: процесс не требует регулировки (статистически управляемый).
"""

import pandas as pd
import pytest

from src.charts.xbar_chart import XBarChart
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

# Средние x̄ и размахи R по подгруппам (строки контрольного листка).
BOOK_SAMPLE_MEANS = [3, 2.4, 3, 3, 3.6, 3.8, 3.4, 2.8, 3, 3.6, 3.4]
BOOK_SAMPLE_RANGES = [3, 3, 3, 4, 4, 3, 3, 4, 5, 3, 3]

# Итоговые величины из книги.
BOOK_GRAND_MEAN = 35 / 11  # ≈ 3.1818 → 3.18 в книге
BOOK_MEAN_RANGE = 38 / 11  # ≈ 3.4545 → 3.45 в книге
BOOK_A2 = 0.577
BOOK_UCL = BOOK_GRAND_MEAN + BOOK_A2 * BOOK_MEAN_RANGE  # ≈ 5.175 → 5.17
BOOK_LCL = BOOK_GRAND_MEAN - BOOK_A2 * BOOK_MEAN_RANGE  # ≈ 1.189 → 1.19


@pytest.fixture
def chart() -> XBarChart:
    """X-bar карта по данным книги (среднее как центр процесса)."""
    return XBarChart(
        BOOK_DATA,
        sample_size=5,
        center_method="mean",
        coefficients_file=str(COEFFICIENTS_FILE),
    )


def test_book_example_subgroup_means(chart) -> None:
    """Средние подгрупп совпадают со строкой x̄ контрольного листка."""
    limits = chart.calculate_limits()
    assert limits["CL"] is not None
    assert chart.subgroups["statistic"].tolist() == pytest.approx(
        BOOK_SAMPLE_MEANS, abs=1e-9
    )


def test_book_example_subgroup_ranges(chart) -> None:
    """Размахи подгрупп совпадают со строкой R контрольного листка."""
    chart.calculate_limits()
    assert chart.subgroups["range"].tolist() == pytest.approx(
        BOOK_SAMPLE_RANGES, abs=1e-9
    )


def test_book_example_grand_mean_and_mean_range(chart) -> None:
    """Общее среднее x̄̄ и средний размах R̄ соответствуют значениям книги."""
    limits = chart.calculate_limits()
    assert limits["CL"] == pytest.approx(BOOK_GRAND_MEAN, rel=1e-12)
    assert limits["CL"] == pytest.approx(3.18, abs=0.005)
    assert limits["mean_range"] == pytest.approx(BOOK_MEAN_RANGE, rel=1e-12)
    assert limits["mean_range"] == pytest.approx(3.45, abs=0.005)


def test_book_example_a2_coefficient(chart) -> None:
    """Коэффициент A2 для n = 5 равен 0.577 (табл. П6 книги)."""
    chart.calculate_limits()
    assert chart.control_limits["A2"] == pytest.approx(BOOK_A2, rel=1e-12)
    assert chart.get_coefficient("A2") == pytest.approx(BOOK_A2, rel=1e-12)


def test_book_example_control_limits(chart) -> None:
    """Контрольные границы совпадают с границами из книги (5.17 и 1.19)."""
    limits = chart.calculate_limits()
    assert limits["UCL"] == pytest.approx(BOOK_UCL, rel=1e-12)
    assert limits["UCL"] == pytest.approx(5.17, abs=0.01)
    assert limits["LCL"] == pytest.approx(BOOK_LCL, rel=1e-12)
    assert limits["LCL"] == pytest.approx(1.19, abs=0.01)


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
    assert summary["chart_type"] == "X-bar"
    assert summary["sample_size"] == 5
    assert summary["total_subgroups"] == 11
    assert summary["grand_mean"] == pytest.approx(3.18, abs=0.005)
    assert summary["mean_range"] == pytest.approx(3.45, abs=0.005)
    assert summary["points_outside"] == 0
    assert summary["percent_outside"] == 0
    assert summary["violations"] == []
    assert summary["ucl"] == pytest.approx(5.17, abs=0.01)
    assert summary["lcl"] == pytest.approx(1.19, abs=0.01)


def test_center_method_median_uses_robust_center() -> None:
    """Робастный метод (медиана) дает другие границы, чем среднее."""
    mean_chart = XBarChart(
        BOOK_DATA,
        sample_size=5,
        center_method="mean",
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    median_chart = XBarChart(
        BOOK_DATA,
        sample_size=5,
        center_method="median",
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    mean_limits = mean_chart.calculate_limits()
    median_limits = median_chart.calculate_limits()

    assert median_limits["center_method"] == "median"
    assert median_limits["CL"] != pytest.approx(mean_limits["CL"], abs=1e-9)
    assert median_limits["UCL"] != pytest.approx(mean_limits["UCL"], abs=1e-9)
    assert median_limits["LCL"] != pytest.approx(mean_limits["LCL"], abs=1e-9)


def test_invalid_center_method_raises_value_error() -> None:
    """Неизвестный метод расчета центра отклоняется с ошибкой ValueError."""
    with pytest.raises(ValueError, match="center_method"):
        XBarChart(
            BOOK_DATA,
            sample_size=5,
            center_method="mode",
            coefficients_file=str(COEFFICIENTS_FILE),
        )


def test_class_matches_manual_calculation(chart) -> None:
    """Результаты класса совпадают с независимым ручным расчётом на pandas."""
    # Независимый ручной расчёт по формулам книги.
    means = BOOK_DATA.mean(axis=1)
    ranges = BOOK_DATA.max(axis=1) - BOOK_DATA.min(axis=1)
    grand_mean = means.mean()
    mean_range = ranges.mean()
    a2 = 0.577  # для n = 5
    manual_ucl = grand_mean + a2 * mean_range
    manual_lcl = grand_mean - a2 * mean_range
    outside_flags = (means > manual_ucl) | (means < manual_lcl)
    manual_outside = set((means.index + 1)[outside_flags])

    limits = chart.calculate_limits()

    assert limits["CL"] == pytest.approx(grand_mean, rel=1e-9)
    assert limits["mean_range"] == pytest.approx(mean_range, rel=1e-9)
    assert limits["UCL"] == pytest.approx(manual_ucl, rel=1e-9)
    assert limits["LCL"] == pytest.approx(manual_lcl, rel=1e-9)
    outside = chart.subgroups["subgroup"][chart.subgroups["outside"]]
    assert set(outside) == manual_outside


def test_subgroups_dataframe_structure(chart) -> None:
    """DataFrame подгрупп класса содержит нужные колонки и нумерацию 1..11."""
    chart.calculate_limits()
    expected_columns = ["subgroup", "statistic", "range", "outside"]
    assert list(chart.subgroups.columns) == expected_columns
    assert chart.subgroups["subgroup"].tolist() == list(range(1, 12))
    assert chart.subgroups["outside"].dtype == bool


def test_get_control_limits_calculates_lazily() -> None:
    """get_control_limits() запускает расчёт, если границы ещё не посчитаны."""
    chart = XBarChart(
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
    chart = XBarChart(
        BOOK_DATA,
        sample_size=5,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    summary = chart.get_summary()
    assert summary["total_subgroups"] == 11
    assert "UCL" in summary or chart.control_limits is not None


def test_get_data_returns_copy(chart) -> None:
    """get_data() копирует подгруппы и не меняет состояние класса."""
    chart.calculate_limits()
    data = chart.get_data()
    assert data.equals(chart.subgroups)
    data.loc[0, "statistic"] = -999  # изменение копии не влияет на класс
    assert chart.subgroups.loc[0, "statistic"] != -999


def test_plot_saves_to_path(chart, tmp_path) -> None:
    """plot(save_path=...) сохраняет изображение по указанному пути."""
    target = tmp_path / "xbar_book.png"
    fig, ax = chart.plot(save_path=str(target), show_values=False)
    assert target.exists()
    assert target.stat().st_size > 0
    assert fig is not None and ax is not None
