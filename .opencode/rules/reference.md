# Технический референс проекта

Фоновое знание об архитектуре. Краткие указатели — в `AGENTS.md`; здесь детали.

## Назначение

`nonparametric-charts` — библиотека непараметрических (distribution-free) контрольных карт Шухарта
по одномерным (univariate) данным: `SignChart` (знаковая) и `SignedRankChart`
(знаково-ранговая). Параметрические карты (`XBar`, `R`, `S`, `Median`) — в соседнем
репозитории `../parametric-charts`, здесь их нет.

`coefficients.json` (коэффициенты `A2/D3/D4/B3/B4/c4/...`) — это константы
**параметрических** карт; собственно непараметрические карты их не используют.
Файл грузится `BaseControlChart.__init__` для единообразия, но находится
автоматически по пути `src/utils/coefficients.json` (см. ниже). См. ADR-001.

## Дерево исходников

```
src/
  base/base_chart.py        # BaseControlChart — абстрактный базовый класс
  charts/
    sign_chart.py           # SignChart — знаковая карта
    signed_rank_chart.py    # SignedRankChart — знаково-ранговая карта
    wilcoxon_distribution.py
  utils/
    data_loader.py          # DataLoader — загрузка CSV (разделители, кодировки, запятые)
    data_preprocessor.py    # DataPreprocessor, DataPipeline
    plotting.py             # вспомогательные функции построения графиков
    plot_style.py           # минималистичный LaTeX-стиль (rcParams, палитра, despine)
    coefficients.json       # коэффициенты Шухарта по n
```

`src/__init__.py` нет. Пакеты подключаются абсолютно от корня: `from src.base...`,
`from src.charts...`, `from src.utils...`.

## `BaseControlChart`

- `__init__(data, sample_size, coefficients_file=None)` — грузит коэффициенты и
  вызывает `_setup_style()` (стиль графиков).
- Абстрактные методы: `calculate_limits(**kwargs)`, `plot(**kwargs)`,
  `get_summary()`.
- Общие: `get_data()`, `get_control_limits()`, `get_violations()`,
  `check_western_electric_rules()`.
- `self.color` — акцентный цвет карты (сейчас `#2E86AB`).

## Данные

- Вход — `pd.DataFrame`: строка = подгруппа, столбец = измерение.
  `sample_size` = число столбцов (не строк).
- `data/data.csv` — пример (14 столбцов, n=14).
- `DataLoader` авто-определяет разделитель/кодировку и чинит десятичные запятые.
- `DataPreprocessor` авто-убирает ведущий индексный столбец 1..N.

## Окружение и запуск

- Python >= 3.14 (`.python-version` 3.14.6). Зависимости — Poetry
  (`[tool.poetry] package-mode = false`: нет пакета `nonparametric-charts`, нет `import nonparametric_charts`).
- Установка: `poetry install --with dev`; активация окружения: `poetry env activate`.
- Jupyter-kernel: `nonparametric-charts-py`
  (`poetry run python -m ipykernel install --user --name nonparametric-charts-py`).
- **Запуск из корня репозитория** (корень на `sys.path`). Ноутбуки — из `notebooks/`.
- Тесты: `pytest`, `testpaths=["tests"]`, `python_files="test_*.py"`.
  Установлен `pytest-sugar` (красивый вывод: прогресс-бар, галочки); в
  `addopts` — `-ra --durations=10` (сводка по пропущенным и 10 самых медленных).
  Один файл = один пример из книги: `tests/sign/` (примеры 4.1–4.3),
  `tests/signed_rank/` (примеры 4.4–4.5), правило выбора `a` —
  `tests/test_control_constant_selection.py`. Карты сохраняются в
  `results/tests/` (каталог в `.gitignore`).
- `.env`, `config/` — пустые заглушки.

## Коэффициенты Шухарта

`BaseControlChart._load_coefficients` перебирает несколько путей, среди которых
есть `src/utils/coefficients.json`, вычисленный от `__file__` — поэтому файл
находится автоматически независимо от текущего каталога. Явный
`coefficients_file` / `NONPARAMETRIC_CHARTS_COEFFICIENTS` нужны лишь для нестандартного пути.
Для непараметрических карт значения коэффициентов не используются.
