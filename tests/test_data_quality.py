"""Тесты проверки качества данных (``utils/data_quality.py``)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nonparametric_charts.utils.data_quality import (
    find_iqr_outliers,
    iqr_fences,
    replace_outliers_with_subgroup_median,
    summarize_dataset,
    winsorize_outliers,
)


def _frame(rows: list[list[float]]) -> pd.DataFrame:
    """DataFrame с колонками x1..xn (строка = подгруппа)."""
    n = len(rows[0])
    return pd.DataFrame(rows, columns=[f'x{i}' for i in range(1, n + 1)])


def test_iqr_fences_match_quantiles() -> None:
    """Заборы Тьюки = Q1 − 1.5·IQR и Q3 + 1.5·IQR."""
    values = [1, 2, 3, 4, 5, 6, 7, 8, 100]
    lower, upper, q1, q3 = iqr_fences(values)

    assert q1 == pytest.approx(np.percentile(values, 25))
    assert q3 == pytest.approx(np.percentile(values, 75))
    assert lower == pytest.approx(q1 - 1.5 * (q3 - q1))
    assert upper == pytest.approx(q3 + 1.5 * (q3 - q1))


def test_find_iqr_outliers_marks_large_value() -> None:
    """Выброс попадает в таблицу с номером подгруппы и столбцом."""
    data = _frame([
        [1.0, 2.0, 3.0, 4.0],
        [2.0, 3.0, 4.0, 5.0],
        [3.0, 4.0, 5.0, 100.0],
    ])
    outliers = find_iqr_outliers(data)

    assert len(outliers) == 1
    assert outliers.iloc[0]['subgroup'] == 3
    assert outliers.iloc[0]['column'] == 'x4'
    assert outliers.iloc[0]['value'] == pytest.approx(100.0)


def test_find_iqr_outliers_empty_table_has_columns() -> None:
    """Без выбросов возвращается пустая таблица с ожидаемыми колонками."""
    data = _frame([[1.0, 2.0], [2.0, 3.0], [3.0, 4.0]])
    outliers = find_iqr_outliers(data)

    assert outliers.empty
    assert list(outliers.columns) == [
        'subgroup', 'column', 'value', 'lower', 'upper'
    ]


def test_replacement_uses_subgroup_median_and_keeps_shape() -> None:
    """Выброс заменяется медианой своей подгруппы, форма сохраняется."""
    data = _frame([
        [1.0, 2.0, 3.0, 4.0],
        [1.0, 2.0, 3.0, 100.0],
        [1.0, 2.0, 3.0, 4.0],
        [1.0, 2.0, 3.0, 4.0],
        [1.0, 2.0, 3.0, 4.0],
    ])
    cleaned, log = replace_outliers_with_subgroup_median(data)

    assert cleaned.shape == data.shape
    # Чистые значения второй подгруппы: 1, 2, 3 → медиана 2.
    assert cleaned.iloc[1]['x4'] == pytest.approx(2.0)
    assert data.iloc[1]['x4'] == pytest.approx(100.0)   # исходник не изменён
    assert len(log) == 1
    assert log.iloc[0]['old_value'] == pytest.approx(100.0)
    assert log.iloc[0]['new_value'] == pytest.approx(2.0)


def test_replacement_without_outliers_returns_copy() -> None:
    """Без выбросов данные не меняются, журнал пуст."""
    data = _frame([[1.0, 2.0], [2.0, 3.0], [3.0, 4.0]])
    cleaned, log = replace_outliers_with_subgroup_median(data)

    pd.testing.assert_frame_equal(cleaned, data)
    assert log.empty


def test_replacement_falls_back_to_global_median() -> None:
    """Если вся подгруппа — выбросы, берётся общая медиана."""
    data = _frame([
        [1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0],
        [50.0, 60.0, 70.0, 80.0],
    ])
    cleaned, log = replace_outliers_with_subgroup_median(data)

    assert len(log) == 4
    assert np.allclose(cleaned.iloc[5].to_numpy(dtype=float), 1.0)


def test_summarize_dataset_reports_outlier_fences() -> None:
    """Сводка содержит размеры, пропуски и заборы IQR."""
    data = _frame([[1.0, np.nan], [2.0, 3.0], [3.0, 4.0]])
    summary = summarize_dataset(data)

    assert summary['подгрупп'] == 3
    assert summary['наблюдений в подгруппе (n)'] == 2
    assert summary['пропусков'] == 1
    assert summary['нижний забор IQR'] < summary['верхний забор IQR']


def test_winsorize_clamps_to_fences_and_keeps_shape() -> None:
    """Винзоризация поджимает выбросы к заборам, форма сохраняется."""
    data = _frame([
        [-100.0, 2.0, 3.0],
        [4.0, 5.0, 6.0],
        [1.0, 5.0, 100.0],
    ])
    lower, upper, _, _ = iqr_fences(data.to_numpy(dtype=float))
    cleaned, journal = winsorize_outliers(data)

    assert cleaned.shape == data.shape
    assert cleaned.iloc[0]['x1'] == pytest.approx(lower)
    assert cleaned.iloc[2]['x3'] == pytest.approx(upper)
    assert data.iloc[0]['x1'] == pytest.approx(-100.0)
    assert cleaned.iloc[1]['x2'] == pytest.approx(5.0)
    assert len(journal) == 2


def test_winsorize_keeps_values_on_fence() -> None:
    """Значения ровно на заборе не считаются выбросами."""
    data = _frame([[1.0, 2.0], [2.0, 3.0], [3.0, 4.0]])
    lower, upper, _, _ = iqr_fences(data.to_numpy(dtype=float))
    frame = _frame([[lower, 2.0], [2.0, 3.0], [3.0, upper]])
    cleaned, journal = winsorize_outliers(frame)

    pd.testing.assert_frame_equal(cleaned, frame)
    assert journal.empty


def test_winsorize_sorts_journal_by_subgroup() -> None:
    """Журнал изменений упорядочен по номеру подгруппы."""
    data = _frame([
        [1.0, 100.0],
        [2.0, 2.0],
        [100.0, 3.0],
        [3.0, 4.0],
        [4.0, 5.0],
        [5.0, 6.0],
        [6.0, 7.0],
    ])
    _, journal = winsorize_outliers(data)

    assert journal['subgroup'].tolist() == sorted(journal['subgroup'].tolist())
    assert len(journal) == 2


def test_winsorize_without_outliers_returns_copy() -> None:
    """Без выбросов данные не меняются, журнал пуст."""
    data = _frame([[1.0, 2.0], [2.0, 3.0], [3.0, 4.0]])
    cleaned, journal = winsorize_outliers(data)

    pd.testing.assert_frame_equal(cleaned, data)
    assert journal.empty
