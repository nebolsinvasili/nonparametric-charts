# AGENTS.md

"nonparametric-charts" — Python-библиотека непараметрических (distribution-free) контрольных карт
Шухарта по **одномерным** (univariate) данным процесса: знаковая карта (`SignChart`)
и знаково-ранговая карта (`SignedRankChart`). Параметрические карты (`XBar`, `R`,
`S`, `Median`) живут в соседнем репозитории `../parametric-charts` — здесь их нет.
Код, комментарии, докстринги и подписи на графиках — **на русском**, так и
оставлять. Исследовательский репозиторий: `poetry.lock` генерируется и игнорируется.

> Этот файл — **только указатели и жёсткие правила**. Всё, что длиннее трёх строк,
> живёт в `.opencode/rules/`, `.opencode/memory/`, `.opencode/skills/`,
> `.opencode/templates/`. Не раздувать этот файл.

## Жёсткие правила (не нарушать)

1. **Первоисточник — книга Чакраборти.** Любая формула, константа, правило сигнала
   или трактовка метода сначала сверяется с
   `docs/chakraborti_s_graham_ma_nonparametric_statistical_process_co.pdf`
   (Chakraborti & Graham, *Nonparametric Statistical Process Control*, Wiley, 2019).
   В коде, докстрингах и ноутбуках указывать **раздел и печатную страницу**.
   Если в книге неясно — идти в указанный там первоисточник/статью и ссылаться на
   него. Вторичный русский источник: `docs/Klyachkin_...pdf` (В. Н. Клячкин).
   → `rules/sources.md`, навык `book-lookup`.
2. **Графики — минималистичный LaTeX.** Единый стиль через
   `src/utils/plot_style.py::apply_minimal_latex_style()`.
   → `rules/plot-style.md`.
3. **Ноутбук = теория → код → разбор кода → логика → формулы → графики.** Формулы
   давать и в LaTeX-разметке, **и** в виде кода. → `rules/notebook-style.md`,
   навык `notebook-build`, шаблон `templates/notebook-structure.md`.
4. **После каждой задачи** (без отдельного запроса) обновить `.opencode/memory/` и
   предложить шаги по улучшению процесса/снижению токенов. → `/wrap-up`.
5. **Язык общения и оформление кода** — `rules/profile.md`.

## Навигация

| Что | Где |
| --- | --- |
| Технический референс проекта | `.opencode/rules/reference.md` |
| Стиль графиков | `.opencode/rules/plot-style.md` |
| Структура ноутбука | `.opencode/rules/notebook-style.md` |
| Правило первоисточников | `.opencode/rules/sources.md` |
| Профиль общения | `.opencode/rules/profile.md` |
| Архитектурные решения (ADR) | `.opencode/memory/architecture-decisions.md` |
| Карта книги Чакраборти | `.opencode/memory/book-map.md` |
| Журнал задач | `.opencode/memory/tasks-completed.md` |
| Навыки | `.opencode/skills/` (`book-lookup`, `notebook-build`, `style-check`) |
| Шаблоны | `.opencode/templates/` |
| Сабагенты | `.opencode/agents/` (`book-checker`, `notebook-writer`) |

## Ключи по проекту (кратко)

- Дерево: `src/base/base_chart.py` (`BaseControlChart`), `src/charts/*`
  (`SignChart`, `SignedRankChart`, ...), `src/utils/*` (`DataLoader`,
  `DataPreprocessor`, `plotting`, `plot_style`).
- Импорты абсолютные: `from src.{base,charts,utils}. import ...`. Запуск из корня
  репозитория.
- Коэффициенты: `src/utils/coefficients.json` находится автоматически
  (в ноутбуках при необходимости — `'../src/utils/coefficients.json'`) либо
  `NONPARAMETRIC_CHARTS_COEFFICIENTS`. Содержит константы **параметрических** карт; сами
  непараметрические карты их не используют.
- Данные: строка = подгруппа, столбец = измерение, `sample_size` = число столбцов.
- Окружение: Python >= 3.14, `poetry install --with dev`, kernel `nonparametric-charts-py`,
  ноутбуки запускать из `notebooks/`.
- Тесты — по примерам книги (один файл = один пример): `tests/sign/`
  (примеры 4.1–4.3), `tests/signed_rank/` (примеры 4.4–4.5), плюс
  `tests/test_control_constant_selection.py` (правило выбора `a`).
  Построенные в тестах карты сохраняются в `results/tests/` с номером примера.
