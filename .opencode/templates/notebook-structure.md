# Шаблон ноутбука: анализ контрольной карты

Копируй структуру ниже. Полные правила — `rules/notebook-style.md`. Скрипт-помощник
— навык `notebook-build`. Все ячейки — по-русски; формулы — и в LaTeX, и в коде.

---

## Ячейка 1 (markdown). Заголовок и источник

```markdown
# <Название карты>

**<Краткое описание: для чего карта, что контролирует.>**

Источник: Chakraborti & Graham (2019), § <раздел> «<название>», стр. <a>–<b>.
```

## Ячейка 2 (markdown). Импорты и настройка

## Ячейка 3 (code)

```python
import sys
sys.path.append('..')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from src.utils.plot_style import apply_minimal_latex_style, despine
apply_minimal_latex_style()

from src.utils import DataLoader, DataPreprocessor
```

## Ячейка 4 (code). Данные и коэффициенты

```python
COEFFICIENTS = '../src/utils/coefficients.json'   # ловушка: путь обязателен
data = DataLoader('../data/data.csv').load()
# sample_size = число столбцов (не строк)
```

## Ячейка 5 (markdown). Теория

```markdown
### Постановка задачи
<Обозначения, предположения, ссылка на стр. книги.>

### Статистика
$$ SN_i = n_i^{+} - n_i^{-} = 2T_i - n $$
```

## Ячейка 6 (code). Формула в виде кода

```python
# Реализация формулы выше (тот же смысл, что и в LaTeX):
# SN = 2 * T - n, T ~ BIN(n, 0.5) в IC
```

## Ячейка 7 (markdown). Реализация и разбор кода

```markdown
### Реализация
<Вызов классов/функций из src/.>

### Разбор
<Что делает каждый шаг, какие предположения, что может пойти не так.>
```

## Ячейка 8 (markdown). Графики

## Ячейка 9 (code). Построение

```python
fig, ax = chart.plot(show_zones=True, fill_zones=False)
despine(ax)
plt.show()
```

## Ячейка 10 (markdown). Проверка по книге и итог

```markdown
### Сверка с книгой
<Сравнение численного результата с примером/таблицей; ссылка на стр.>

### Итог
<Выводы; что осталось неясным.>
```
