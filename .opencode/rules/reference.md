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
автоматически по пути `src/nonparametric_charts/utils/coefficients.json` (см. ниже). См. ADR-001.

## Дерево исходников

```
src/
  nonparametric_charts/       # импортируемый пакет (имя дистрибутива — nonparametric-charts)
    __init__.py               # публичный API: SignChart, SignedRankChart, CusumSignChart, CusumSignedRankChart, BaseControlChart
    base/
      base_chart.py           # BaseControlChart — абстрактный базовый класс
    charts/
      sign_chart.py           # SignChart — знаковая карта
      signed_rank_chart.py    # SignedRankChart — знаково-ранговая карта
      cusum_sign_chart.py     # CusumSignChart — CUSUM по знакам (CUSUM-SN)
      cusum_signed_rank_chart.py  # CusumSignedRankChart — CUSUM по знаковым рангам (CUSUM-SR)
      wilcoxon_distribution.py
    utils/
      data_loader.py          # DataLoader — загрузка CSV (разделители, кодировки, запятые)
      data_preprocessor.py    # DataPreprocessor, DataPipeline
      statistics.py           # общие статистики: sign_*, signed_rank_*
      plotting.py             # вспомогательные функции построения графиков
      plot_style.py           # минималистичный LaTeX-стиль (rcParams, палитра, despine)
      coefficients.json       # коэффициенты Шухарта по n
```

Раскладка — стандартная **src-layout**: `src` — корень исходников, пакет —
`nonparametric_charts`. Импорты абсолютные: `from nonparametric_charts.base...`,
`from nonparametric_charts.charts...`, `from nonparametric_charts.utils...`. Проект
ставится и через `poetry install`, и через `pip install .` (см. ADR-017). Запуск —
из корня репозитория; тесты и ноутбуки дополнительно добавляют `src` в `sys.path`,
чтобы работать и без установки.

## Каталог `docs/`

```
docs/
  ref/                        # источники: книги, статьи (только для чтения)
    chakraborti_*.pdf         # первоисточник (Chakraborti & Graham, 2019)
    Klyachkin_*.pdf           # вторичный русский источник
    1-s2.0-*.pdf              # статья
  reports/                    # отчёты и всё, что их собирает
    sn_verification.tex/.pdf  # отчёт о верификации знаковой карты
    sr_verification.tex/.pdf  # отчёт о верификации знаково-ранговой карты
    sr_macros.tex             # генерируемые макросы графиков SR
    Makefile                  # сборка pdflatex (cd docs/reports && make)
    build/                    # вспомогательные файлы сборки (.gitignore)
    scripts/                  # генераторы координат/таблиц
```

- Сборка отчётов: `cd docs/reports && make` (движок `pdflatex`, T2A + babel).
- Пути внутри отчётов и опытов задаются **от корня репозитория**.

## Организация репозитория (разделение ответственности)

```
src/            # код библиотеки (пакет nonparametric_charts)
tests/          # ТЕСТЫ КОДА (pytest) — инварианты API, без привязки к книге
examples/       # ПРОВЕРКА ПРИМЕРОВ книги: консольный вывод + графики (results/examples/)
experiments/    # ЭКСПЕРИМЕНТЫ (R/Python) и инструкции; питают отчёты
notebooks/      # .ipynb для быстрой загрузки своих данных и построения карты
docs/ref/       # источники (книги, статьи)
docs/reports/   # TeX/PDF-отчёты и сборка
results/        # сгенерированные артефакты (tests/, examples/) — .gitignore
```

- Проверка примеров: `poetry run python examples/run_all.py` (или по одному).
- Тесты кода: `pytest` (каталог `tests/`).
- Опыты: `experiments/{sn,sr}/`, инструкции — `experiments/00_ENVIRONMENT.txt`.
- Алиасы запуска (entry point `npc`, `[project.scripts]`): `npc test`,
  `npc examples`, `npc experiment {sn|sr|all}`; реализация — `src/nonparametric_charts/cli.py`.

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

- Python >= 3.14 (`.python-version` 3.14.6). Проект — устанавливаемый пакет
  `nonparametric-charts` (импорт `nonparametric_charts`, src-layout, ADR-017).
- Установка — **и через poetry, и через pip**:
  - `poetry install --with dev`; активация окружения: `poetry env activate`;
  - `pip install .` (или `pip install -e .`), зависимости — из `[project]`
    (`pip wheel .` тоже работает, сборка через `poetry-core`).
- Jupyter-kernel: `nonparametric-charts-py`
  (`poetry run python -m ipykernel install --user --name nonparametric-charts-py`).
- **Запуск из корня репозитория**. Ноутбуки — из `notebooks/` (добавляют `../src`
  в `sys.path`); тесты добавляют `src` в `sys.path` через `conftest.py`.
- Тесты: `pytest`, `testpaths=["tests"]`, `python_files="test_*.py"`.
  Установлен `pytest-sugar` (красивый вывод: прогресс-бар, галочки); в
  `addopts` — `-ra --durations=10` (сводка по пропущенным и 10 самых медленных).
  Один файл = один набор инвариантов API: `tests/test_charts.py` (границы,
  статистики, правило сигнала, графики) и правило выбора `a` —
  `tests/test_control_constant_selection.py`. Проверка примеров книги —
  `examples/` (консоль + графики в `results/examples/`).
- `.env`, `config/` — пустые заглушки.

## Коэффициенты Шухарта

`BaseControlChart._load_coefficients` перебирает несколько путей, среди которых
есть `src/nonparametric_charts/utils/coefficients.json`, вычисленный от `__file__` — поэтому файл
находится автоматически независимо от текущего каталога. Явный
`coefficients_file` / `NONPARAMETRIC_CHARTS_COEFFICIENTS` нужны лишь для нестандартного пути.
Для непараметрических карт значения коэффициентов не используются.
