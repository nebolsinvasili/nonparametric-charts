"""
Тесты S контрольной карты Шухарта (карта стандартных отклонений)
по примеру из книги:

В. Н. Клячкин, «Статистические методы в управлении качеством»,
§4.1.3, рис. 4.2 и 4.3 (контрольный листок и карты средних и
стандартных отклонений).

Контролируется содержание хрома в стальных отливках (%).
Каждая подгруппа — 4 измерения, всего 15 подгрупп.

Результаты, приведенные в книге:
    s̄ = 0,087;   B3 = 0 (при n < 6);   B4 = 2,266 (n = 4);
    UCL = 2,266·0,087 = 0,197;   LCL = 0;
на карте стандартных отклонений нет точек, выходящих за границы.
"""

import pandas as pd
import pytest

from src.charts.s_chart import SChart
from tests.conftest import COEFFICIENTS_FILE

# Данные контрольного листка (рис. 4.2): каждая строка — подгруппа (выборка),
# каждый столбец — одно измерение. Размер подгруппы n = 4.
BOOK_DATA = pd.DataFrame(
    [
        [0.74, 0.76, 0.62, 0.73],
        [0.72, 0.74, 0.84, 0.69],
        [0.87, 0.79, 0.70, 0.92],
        [0.78, 0.66, 0.71, 0.74],
        [0.81, 0.66, 0.82, 0.67],
        [0.63, 0.71, 0.68, 0.82],
        [0.63, 0.73, 0.64, 0.80],
        [0.66, 0.68, 0.85, 0.91],
        [0.63, 0.66, 0.62, 0.85],
        [0.85, 0.61, 0.75, 0.77],
        [0.73, 0.65, 0.74, 0.90],
        [0.85, 0.77, 0.65, 0.69],
        [0.67, 0.69, 0.83, 0.62],
        [0.74, 0.73, 0.62, 0.88],
        [0.81, 0.82, 0.69, 0.73],
    ],
    columns=[f"m{i}" for i in range(1, 5)],
)

# Стандартные отклонения s по подгруппам (столбец s контрольного листка).
BOOK_SAMPLE_STDS = [
    0.0629,
    0.0650,
    0.0963,
    0.0506,
    0.0868,
    0.0804,
    0.0804,
    0.1240,
    0.1080,
    0.0998,
    0.1047,
    0.0887,
    0.0900,
    0.1066,
    0.0629,
]

# Итоговые величины из книги.
BOOK_MEAN_STD = 0.08713687867734844  # точное среднее; в книге s̄ = 0,087
BOOK_SBAR_BOOK = 0.087
BOOK_B3 = 0
BOOK_B4 = 2.266  # из src/utils/coefficients.json и табл. П6 (n = 4)
BOOK_UCL = BOOK_B4 * BOOK_MEAN_STD  # ≈ 0.19745 → 0.197 в книге
BOOK_LCL = BOOK_B3 * BOOK_MEAN_STD  # = 0


@pytest.fixture
def chart() -> SChart:
    """S карта по данным книги."""
    return SChart(
        BOOK_DATA,
        sample_size=4,
        coefficients_file=str(COEFFICIENTS_FILE),
    )


def test_book_example_subgroup_stds(chart) -> None:
    """Стандартные отклонения подгрупп совпадают со столбцом s листка."""
    stds = BOOK_DATA.std(axis=1, ddof=1)
    chart.calculate_limits()
    stat = chart.subgroups["statistic"].tolist()
    assert stat == pytest.approx(stds, abs=1e-9)
    assert stat == pytest.approx(BOOK_SAMPLE_STDS, abs=0.0001)


def test_book_example_mean_std(chart) -> None:
    """Среднее стандартных отклонений s̄ соответствует значению книги 0,087."""
    limits = chart.calculate_limits()
    assert limits["CL"] == pytest.approx(BOOK_MEAN_STD, rel=1e-12)
    assert limits["CL"] == pytest.approx(BOOK_SBAR_BOOK, abs=0.001)


def test_book_example_b3_b4_coefficients(chart) -> None:
    """Коэффициенты B3 и B4 для n = 4 соответствуют табл. П6 книги."""
    chart.calculate_limits()
    assert chart.control_limits["B3"] == pytest.approx(BOOK_B3, rel=1e-12)
    assert chart.control_limits["B4"] == pytest.approx(BOOK_B4, rel=1e-12)
    assert chart.get_coefficient("B3") == pytest.approx(BOOK_B3, rel=1e-12)
    assert chart.get_coefficient("B4") == pytest.approx(BOOK_B4, rel=1e-12)


def test_book_example_control_limits(chart) -> None:
    """Контрольные границы совпадают с границами из книги (0.197 и 0)."""
    limits = chart.calculate_limits()
    assert limits["UCL"] == pytest.approx(BOOK_UCL, rel=1e-12)
    assert limits["UCL"] == pytest.approx(0.197, abs=0.001)
    assert limits["LCL"] == pytest.approx(BOOK_LCL, rel=1e-12)
    assert limits["LCL"] == 0


def test_book_example_manual_rounding_matches_book(chart) -> None:
    """Округлённый расчёт как в книге: 2,266·0,087 = 0,197; LCL = 0."""
    limits = chart.calculate_limits()
    manual_ucl = BOOK_B4 * BOOK_SBAR_BOOK  # 2.266 * 0.087
    assert manual_ucl == pytest.approx(0.197, abs=0.0005)
    assert limits["UCL"] == pytest.approx(manual_ucl, abs=0.001)


def test_book_example_process_in_control(chart) -> None:
    """Ни одна точка не выходит за границы — процесс управляем."""
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
    assert summary["chart_type"] == "S"
    assert summary["sample_size"] == 4
    assert summary["total_subgroups"] == 15
    assert summary["mean_std"] == pytest.approx(0.087, abs=0.001)
    assert summary["points_outside"] == 0
    assert summary["percent_outside"] == 0
    assert summary["violations"] == []
    assert summary["ucl"] == pytest.approx(0.197, abs=0.001)
    assert summary["lcl"] == 0
    assert summary["max_std"] == pytest.approx(0.124, abs=0.002)
    assert summary["min_std"] == pytest.approx(0.051, abs=0.002)


def test_class_matches_manual_calculation(chart) -> None:
    """Результаты класса совпадают с независимым ручным расчётом на pandas."""
    # Независимый ручной расчёт по формулам книги.
    stds = BOOK_DATA.std(axis=1, ddof=1)
    mean_std = stds.mean()
    b3 = 0  # для n = 4 (табл. П6)
    b4 = 2.266
    manual_ucl = b4 * mean_std
    manual_lcl = b3 * mean_std

    limits = chart.calculate_limits()

    assert limits["CL"] == pytest.approx(mean_std, rel=1e-9)
    assert limits["UCL"] == pytest.approx(manual_ucl, rel=1e-9)
    assert limits["LCL"] == pytest.approx(manual_lcl, rel=1e-9)
    outside_flags = (stds > manual_ucl) | (stds < manual_lcl)
    manual_outside = set((stds.index + 1)[outside_flags])
    outside = chart.subgroups["subgroup"][chart.subgroups["outside"]]
    assert set(outside) == manual_outside


def test_subgroups_dataframe_structure(chart) -> None:
    """DataFrame подгрупп класса содержит нужные колонки и нумерацию 1..15."""
    chart.calculate_limits()
    expected_columns = ["subgroup", "statistic", "outside"]
    assert list(chart.subgroups.columns) == expected_columns
    assert chart.subgroups["subgroup"].tolist() == list(range(1, 16))
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
    chart = SChart(
        BOOK_DATA,
        sample_size=4,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    assert chart.control_limits is None
    limits = chart.get_control_limits()
    assert limits["UCL"] == pytest.approx(BOOK_UCL, rel=1e-9)
    assert chart.control_limits is not None


def test_get_summary_calculates_lazily() -> None:
    """get_summary() запускает расчёт, если границы ещё не посчитаны."""
    chart = SChart(
        BOOK_DATA,
        sample_size=4,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    summary = chart.get_summary()
    assert summary["total_subgroups"] == 15
    assert "UCL" in summary or chart.control_limits is not None


def test_plot_saves_to_path(chart, tmp_path) -> None:
    """plot(save_path=...) сохраняет изображение по указанному пути."""
    target = tmp_path / "s_book.png"
    fig, ax = chart.plot(save_path=str(target), show_values=False)
    assert target.exists()
    assert target.stat().st_size > 0
    assert fig is not None and ax is not None


def test_lcl_zero_for_small_subgroup_size() -> None:
    """При n ≤ 5 нижняя граница S-карты равна нулю (B3 = 0)."""
    for n in (2, 3, 4, 5):
        chart = SChart(
            BOOK_DATA,
            sample_size=n,
            coefficients_file=str(COEFFICIENTS_FILE),
        )
        limits = chart.calculate_limits()
        assert limits["LCL"] == 0
        assert limits["B3"] == 0


def test_data_csv_detects_violations() -> None:
    """На data.csv S-карта находит те же 5 нарушений, что и R-карта."""
    df = pd.read_csv("data/data.csv")
    chart = SChart(
        df,
        sample_size=14,
        coefficients_file=str(COEFFICIENTS_FILE),
    )
    summary = chart.get_summary()
    assert summary["total_subgroups"] == 10
    assert summary["B4"] == pytest.approx(1.594, rel=1e-9)
    assert summary["B3"] == pytest.approx(0.406, rel=1e-9)
    assert summary["lcl"] > 0  # при n = 14 нижняя граница ненулевая
    assert summary["points_outside"] == 5
    assert [v["subgroup"] for v in summary["violations"]] == [1, 3, 5, 6, 10]
