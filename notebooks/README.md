# Ноутбуки

Три учебных ноутбука по картам:

| Файл | Карта | Содержание |
| --- | --- | --- |
| `sign_chart_analysis.ipynb` | Shewhart-SN | теория, границы, примеры, графики |
| `signed_rank_chart_analysis.ipynb` | Shewhart-SR | знаковые ранги, точное распределение |
| `cusum_analysis.ipynb` | CUSUM-SN/SR | RL, матрица `Q`, OC, подбор `(k, h)` |

Ноутбуки — **учебные**: они показывают формулы и код, а не заменяют тесты.
Проверка API — `tests/`, примеры книги — `examples/`.

## Запуск

```bash
cd notebooks
jupyter lab
```

Важно: ноутбуки добавляют `../src` в `sys.path`, поэтому запускать их нужно
**из каталога `notebooks/`**. При запуске из корня репозитория импорт может
взять установленную версию пакета или не найти `src`.

Если пакет установлен (`poetry install` / `pip install .`), путь `../src`
всё равно указывает на локальную версию — это удобно для разработки.

### Kernel

Выберите kernel окружения, в котором установлены зависимости:

- Poetry: `poetry run python -m ipykernel install --user --name nonparametric-charts-py`;
- либо kernel `.venv` из проекта;
- в текущих файлах metadata может указывать `python3` — это нормально,
  если в этом kernel доступны `numpy`, `pandas`, `scipy`, `matplotlib`.

Проверка из notebook:

```python
import sys
print(sys.executable)
import nonparametric_charts
print(nonparametric_charts.__file__)
```

Путь должен указывать на `src/nonparametric_charts` (при запуске из
`notebooks/`) либо на установленный пакет.

## Полный прогон

В Jupyter: `Kernel → Restart & Run All`.

Или из командной строки:

```bash
cd notebooks
jupyter nbconvert --to notebook --execute cusum_analysis.ipynb \
    --output /tmp/cusum_analysis_executed.ipynb
```

Ожидаемо: все ячейки выполняются без ошибок. Предупреждения `findfont` или
`LaTeX` не критичны, если графики строятся; ошибки импорта — критичны.

## Структура ноутбука

Каждый ноутбук следует каркасу:

1. постановка и источник (раздел/страница книги);
2. теория и формулы в LaTeX;
3. реализация на Python;
4. разбор кода;
5. проверка на примере;
6. графики;
7. выводы и ограничения.

Для CUSUM дополнительно: точный марковский RL, OC-кривые, подбор `h` и
`(k, h)`, сравнение с simulation.

## Результаты и артефакты

Ноутбуки могут сохранять графики в `results/` (каталог gitignored) или
показывать их inline. Исполненные копии не коммитятся; коммитится исходный
ноутбук с очищенными выходами, если это принято в текущей задаче.

Перед коммитом:

```bash
jupyter nbconvert --clear-output --inplace notebooks/*.ipynb
```

Не удаляйте outputs, если они нужны для проверки в конкретной задаче;
уточните ожидаемый формат.

## Проверка стиля

Графики должны использовать `apply_minimal_latex_style()` и палитру проекта
(`ACCENT`, `INK`, `PALETTE`, ...). Проверка соответствия каркасу и стилю —
навык `style-check`:

```bash
# из корня репозитория
poetry run python -c "from nonparametric_charts.utils.plot_style import apply_minimal_latex_style; apply_minimal_latex_style()"
```

Если график выглядит иначе, чем в отчёте, проверьте:

- вызван ли `apply_minimal_latex_style()`;
- не переопределены ли `rcParams` после вызова;
- используется ли `usetex` (в проекте — нет, стиль через mathtext).

## Частые проблемы

**`ModuleNotFoundError: nonparametric_charts`** — запустите Jupyter из
`notebooks/` или установите пакет.

**`FileNotFoundError` для данных** — проверьте относительный путь; ноутбуки
рассчитаны на `cwd = notebooks/`.

**Kernel не видит зависимости** — выберите kernel Poetry-окружения или
установите `ipykernel` в нужное окружение.

**Долгий CUSUM-ноутбук** — точный RL при больших `ARL` может считаться
секунды; это ожидаемо. Для быстрой проверки уменьшите `max_t`/сетку, но не
меняйте формулы.

**Графики без кириллицы** — проверьте шрифты и `apply_minimal_latex_style()`;
в проекте подписи на русском, поэтому нужен шрифт с кириллицей.

## Ссылки

- `README.md` — установка и быстрый старт.
- `experiments/cusum/README.md` — алгоритмы CUSUM подробно.
- `.opencode/rules/notebook-style.md` — требования к структуре.
- `.opencode/templates/notebook-structure.md` — шаблон.
