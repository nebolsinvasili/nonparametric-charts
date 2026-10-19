# Шаблон: новая контрольная карта (`src/nonparametric_charts/charts/<name>_chart.py`)

Не изобретать структуру — заполнять по образцу существующих карт
(`sign_chart.py`, `signed_rank_chart.py`). Перед реализацией — `book-lookup`.
Порядок работы — команда `/new-chart` (`.opencode/commands/new-chart.md`);
рабочий документ карты — `docs/reports/<chart>_plan.md`
(шаблон `.opencode/templates/chart-plan.md`).

```python
"""
<Название карты> Шухарта (<English name>).

<Одно-два предложения: что контролирует, на какой статистике основана.>

Теория (Chakraborti & Graham, 2019, § <раздел>, стр. <a>–<b>):
----------------------------------------------------------------------
<Статистика подгруппы и её распределение в IC.>
<Контрольные границы.>
<Правило сигнала.>
<FAR / ARL / MRL, если применимо.>
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Optional, Tuple, List

try:
    from nonparametric_charts.base.base_chart import BaseControlChart
except ImportError:  # fallback, как в sign_chart.py
    class BaseControlChart:
        def __init__(self, data, sample_size, coefficients_file=None):
            self.data = data
            self.sample_size = sample_size
            self.coefficients_file = coefficients_file


class <Name>Chart(BaseControlChart):
    """<Докстринг с Parameters/Returns, как в соседних картах.>"""

    def __init__(self, data, sample_size, target_value=None,
                 coefficients_file=None):
        super().__init__(data, sample_size, coefficients_file)
        self.chart_type = "<Name>"
        self.color = '#2E86AB'
        # ... параметры метода
        self.subgroups: Optional[pd.DataFrame] = None
        self.control_limits: Optional[Dict] = None
        self.violations: List[Dict] = []

    def calculate_limits(self, **kwargs) -> Dict:
        """Расчёт статистик по подгруппам и контрольных границ."""
        ...
        self._find_violations()
        return self.control_limits

    def _find_violations(self):
        """Поиск нарушений по правилу сигнала (ссылка на ур./стр. книги)."""
        ...

    def plot(self, figsize=(10, 5), save_path=None, title=None,
             show_zones=True, fill_zones=False,
             value_offset=(0, 0.35)) -> Tuple[plt.Figure, plt.Axes]:
        """Построение графика; стиль — rules/plot-style.md."""
        if self.control_limits is None:
            self.calculate_limits()
        fig, ax = plt.subplots(figsize=figsize)
        ...
        return fig, ax

    def get_summary(self) -> Dict:
        """Сводная информация о карте."""
        ...
```

## Чек-лист

- [ ] В докстринге — раздел и печатные страницы книги.
- [ ] Границы/константы сверены с книгой (`book-lookup`).
- [ ] Стиль графика — минималистичный LaTeX (`plot_style`), зоны без заливки.
- [ ] Инварианты API покрыты тестом в `tests/` (без привязки к книге).
- [ ] Пример из книги добавлен в `examples/` (+ `examples/README.md`, `run_all.py`).
- [ ] Обновлены `memory/tasks-completed.md` и (при необходимости)
      `memory/architecture-decisions.md`, `memory/book-map.md`.
