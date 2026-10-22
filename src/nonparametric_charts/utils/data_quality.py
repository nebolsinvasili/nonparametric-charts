"""
Проверка качества данных перед построением контрольных карт.

Модуль отвечает на три вопроса, которые нужно закрыть до расчёта границ:

1. **Есть ли выбросы?** — правило Тьюки: значение вне интервала
   ``[Q1 − 1.5·IQR; Q3 + 1.5·IQR]`` считается выбросом.
2. **Чем заменить выброс?** — медианой своей подгруппы: размер подгруппы
   ``n`` сохраняется, а уровень ряда не сдвигается к общему центру.
3. **Как описать набор?** — сводка (число подгрупп, пропуски, квантили,
   асимметрия), по которой видно, применима ли знаково-ранговая карта
   (нужна симметрия).

Замечание о месте в расчёте: замена выбросов — это **предобработка**, а не
часть метода карты. Контрольные границы ``±a`` от данных не зависят
(Chakraborti & Graham, 2019, § 4.2.1.1, стр. 190–191), поэтому очистка
меняет только статистики подгрупп, но не саму карту.

Все функции работают с таблицей «строка = подгруппа, столбец = наблюдение»
и не меняют исходный ``DataFrame``.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd

__all__ = [
    'iqr_fences',
    'find_iqr_outliers',
    'replace_outliers_with_subgroup_median',
    'summarize_dataset',
]


def iqr_fences(
    values,
    k: float = 1.5,
) -> Tuple[float, float, float, float]:
    """
    Границы Тьюки для выборки.

    Parameters
    ----------
    values : array-like
        Наблюдения; ``NaN`` игнорируются.
    k : float, default=1.5
        Множитель межквартильного размаха.

    Returns
    -------
    tuple[float, float, float, float]
        ``(lower, upper, q1, q3)`` — нижний и верхний заборы, квартили.
    """
    array = np.asarray(values, dtype=float).ravel()
    array = array[~np.isnan(array)]
    if array.size == 0:
        raise ValueError('Нет наблюдений для расчёта квартилей')

    q1, q3 = np.percentile(array, [25, 75])
    iqr = q3 - q1
    return (
        float(q1 - k * iqr),
        float(q3 + k * iqr),
        float(q1),
        float(q3),
    )


def find_iqr_outliers(
    data: pd.DataFrame,
    k: float = 1.5,
) -> pd.DataFrame:
    """
    Найти выбросы по правилу Тьюки во всей таблице.

    Parameters
    ----------
    data : pandas.DataFrame
        Строка = подгруппа, столбец = наблюдение.
    k : float, default=1.5
        Множитель межквартильного размаха.

    Returns
    -------
    pandas.DataFrame
        Столбцы ``subgroup`` (номер подгруппы с 1), ``column``, ``value``,
        ``lower``, ``upper``. Пустой ``DataFrame`` — выбросов нет.
    """
    lower, upper, _, _ = iqr_fences(data.to_numpy(dtype=float), k=k)
    rows = []
    for position, (_, row) in enumerate(data.iterrows(), start=1):
        for column, value in row.items():
            if pd.isna(value):
                continue
            value = float(value)
            if value < lower or value > upper:
                rows.append({
                    'subgroup': position,
                    'column': column,
                    'value': value,
                    'lower': lower,
                    'upper': upper,
                })

    return pd.DataFrame(
        rows,
        columns=['subgroup', 'column', 'value', 'lower', 'upper'],
    )


def replace_outliers_with_subgroup_median(
    data: pd.DataFrame,
    k: float = 1.5,
    outliers: Optional[pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Заменить выбросы медианой их подгруппы.

    Медиана считается по «чистым» значениям строки, то есть без самих
    выбросов. Если в строке не осталось значений, используется общая
    медиана таблицы.

    Parameters
    ----------
    data : pandas.DataFrame
        Строка = подгруппа, столбец = наблюдение. Исходная таблица не
        изменяется.
    k : float, default=1.5
        Множитель межквартильного размаха.
    outliers : pandas.DataFrame, optional
        Готовая таблица из :func:`find_iqr_outliers`; если не задана,
        выбросы ищутся заново.

    Returns
    -------
    tuple[pandas.DataFrame, pandas.DataFrame]
        Очищенная копия (той же формы, что и вход) и журнал замен со
        столбцами ``subgroup``, ``column``, ``old_value``, ``new_value``.
    """
    cleaned = data.copy()
    if outliers is None:
        outliers = find_iqr_outliers(data, k=k)

    log_columns = ['subgroup', 'column', 'old_value', 'new_value']
    if outliers.empty:
        return cleaned, pd.DataFrame(columns=log_columns)

    global_median = float(np.nanmedian(data.to_numpy(dtype=float)))
    columns = list(data.columns)
    rows = []

    for subgroup, group in outliers.groupby('subgroup', sort=True):
        position = int(subgroup) - 1
        row = data.iloc[position].astype(float)
        dirty = list(group['column'])
        clean_values = row.drop(labels=dirty).dropna()
        replacement = (
            float(clean_values.median())
            if not clean_values.empty
            else global_median
        )

        for column in dirty:
            column_position = columns.index(column)
            old_value = float(data.iat[position, column_position])
            cleaned.iat[position, column_position] = replacement
            rows.append({
                'subgroup': int(subgroup),
                'column': column,
                'old_value': old_value,
                'new_value': replacement,
            })

    return cleaned, pd.DataFrame(rows, columns=log_columns)


def summarize_dataset(data: pd.DataFrame) -> pd.Series:
    """
    Краткая сводка набора для проверки данных.

    Parameters
    ----------
    data : pandas.DataFrame
        Строка = подгруппа, столбец = наблюдение.

    Returns
    -------
    pandas.Series
        Показатели: размер таблицы, пропуски, минимум/квантили/максимум,
        среднее, стандартное отклонение и асимметрия.
    """
    values = data.to_numpy(dtype=float).ravel()
    values = values[~np.isnan(values)]
    if values.size == 0:
        raise ValueError('Нет наблюдений для сводки')

    series = pd.Series(values, dtype=float)
    lower, upper, q1, q3 = iqr_fences(values)

    return pd.Series({
        'подгрупп': int(data.shape[0]),
        'наблюдений в подгруппе (n)': int(data.shape[1]),
        'ячеек всего': int(data.size),
        'пропусков': int(pd.isna(data.to_numpy(dtype=float)).sum()),
        'минимум': float(np.min(values)),
        'Q1': q1,
        'медиана': float(np.median(values)),
        'Q3': q3,
        'максимум': float(np.max(values)),
        'среднее': float(np.mean(values)),
        'стандартное отклонение': float(np.std(values, ddof=1)),
        'асимметрия': float(series.skew()),
        'нижний забор IQR': lower,
        'верхний забор IQR': upper,
    }, name='значение')
