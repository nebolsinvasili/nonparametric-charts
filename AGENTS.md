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
   `docs/ref/chakraborti_s_graham_ma_nonparametric_statistical_process_co.pdf`
   (Chakraborti & Graham, *Nonparametric Statistical Process Control*, Wiley, 2019).
   В коде, докстрингах и ноутбуках указывать **раздел и печатную страницу**.
   Если в книге неясно — идти в указанный там первоисточник/статью и ссылаться на
   него. Вторичный русский источник: `docs/ref/Klyachkin_...pdf` (В. Н. Клячкин).
   → `rules/sources.md`, навык `book-lookup`.
2. **Графики — минималистичный LaTeX.** Единый стиль через
   `src/nonparametric_charts/utils/plot_style.py::apply_minimal_latex_style()`.
   → `rules/plot-style.md`.
3. **Ноутбук = теория → код → разбор кода → логика → формулы → графики.** Формулы
   давать и в LaTeX-разметке, **и** в виде кода. → `rules/notebook-style.md`,
   навык `notebook-build`, шаблон `templates/notebook-structure.md`.
4. **После каждой задачи** (без отдельного запроса) обновить `.opencode/memory/` и
   предложить шаги по улучшению процесса/снижению токенов. → `/wrap-up`.
5. **Язык общения и оформление кода** — `rules/profile.md`.
6. **Пакет ставится и через `pip`, и через `poetry`.** `nonparametric-charts` —
   устанавливаемый пакет (src-layout, `src/nonparametric_charts/`, ADR-017);
   импорт — `from nonparametric_charts...`. Нельзя ломать ни
   `poetry install`, ни `pip install .`.
7. **Старт нового чата.** Работу начинать только после слова-триггера `СВОДКА`
   от пользователя. Перед началом: проверить установку навыков/MCP/настроек,
   прочитать `.opencode/memory/` и дать краткую сводку сделанного. Если `СВОДКА`
   нет — предупредить и ждать, работу не начинать. → `rules/profile.md`.
8. **Ветки для крупных изменений.** Крупное изменение (новая карта, смена
   архитектуры/пакета, реструктуризация репозитория, новый отчёт, правка
   > ~5 файлов) — только в ветке `<type>/<topic>` от `master`; по завершении
   правок — `merge --no-ff`. Ветку удалять только если она не фиксирует
   старую версию и пользователь не просил её сохранить; иначе оставить.
   При новых правках — новая ветка. Журнал веток —
   `.opencode/memory/branches.md`. → `rules/profile.md`.
9. **README и воспроизводимость.** Каждый новый модуль, опыт, отчёт и
   ноутбук сопровождается README: назначение, алгоритм, команда запуска,
   входы/выходы и ожидаемый результат. Старые версии кода, ветки, worktree
   и артефакты не удаляются без явного разрешения. →
   `README.md`, `experiments/README.md`, `experiments/cusum/README.md`,
   `docs/reports/README.md`, `notebooks/README.md`,
   `.opencode/memory/preferences.md`.

## Навигация

| Что | Где |
| --- | --- |
| Общий обзор и быстрый старт | `README.md` |
| Опыты и окружение | `experiments/README.md` |
| Алгоритмы и запуск CUSUM | `experiments/cusum/README.md` |
| Сборка отчётов | `docs/reports/README.md` |
| Ноутбуки | `notebooks/README.md` |
| Предпочтения пользователя | `.opencode/memory/preferences.md` |
| Технический референс проекта | `.opencode/rules/reference.md` |
| Стиль графиков | `.opencode/rules/plot-style.md` |
| Структура ноутбука | `.opencode/rules/notebook-style.md` |
| Правило первоисточников | `.opencode/rules/sources.md` |
| Профиль общения | `.opencode/rules/profile.md` |
| Архитектурные решения (ADR) | `.opencode/memory/architecture-decisions.md` |
| Карта книги Чакраборти | `.opencode/memory/book-map.md` |
| Журнал задач | `.opencode/memory/tasks-completed.md` |
| Навыки | `.opencode/skills/` (`book-lookup`, `notebook-build`, `style-check`) |
| Шаблоны | `.opencode/templates/` (`new-chart`, `chart-plan`, `notebook-structure`, `report-structure`) |
| Порядок построения новой карты | `.opencode/commands/new-chart.md` |
| Рабочие документы карт (план/досье) | `docs/reports/<chart>_plan.md` |
| Сабагенты | `.opencode/agents/` (`book-checker`, `notebook-writer`) |
| Отчёты (TeX/PDF, сборка) | `docs/reports/` |
| Источники (книги, статьи) | `docs/ref/` |
| Проверка примеров книги (консоль + графики) | `examples/` |
| Эксперименты (R/Python) и инструкции | `experiments/` |
| Тесты кода | `tests/` |
| Ноутбуки быстрого старта под свои данные | `notebooks/` |

## Ключи по проекту (кратко)

- Дерево: `src/nonparametric_charts/base/base_chart.py` (`BaseControlChart`), `src/nonparametric_charts/charts/*`
  (`SignChart`, `SignedRankChart`, ...), `src/nonparametric_charts/utils/*` (`DataLoader`,
  `DataPreprocessor`, `plotting`, `plot_style`).
- Импорты абсолютные: `from nonparametric_charts.{base,charts,utils}. import ...`. Запуск из корня
  репозитория.
- Коэффициенты: `src/nonparametric_charts/utils/coefficients.json` находится автоматически
  (в ноутбуках при необходимости — `'../src/nonparametric_charts/utils/coefficients.json'`) либо
  `NONPARAMETRIC_CHARTS_COEFFICIENTS`. Содержит константы **параметрических** карт; сами
  непараметрические карты их не используют.
- Данные: строка = подгруппа, столбец = измерение, `sample_size` = число столбцов.
- Окружение: Python >= 3.14, установка — `poetry install --with dev` **или**
  `pip install .`; kernel `nonparametric-charts-py`, ноутбуки запускать из `notebooks/`.
- Алиасы запуска: `npc test` (тесты; `--fast` — без `@pytest.mark.slow`,
  `--slow` — только они), `npc examples` (примеры книги),
  `npc experiment {sn|sr|cusum|all}` (опыты). Определены в `[project.scripts]`
  (`src/nonparametric_charts/cli.py`), доступны и через pip, и через poetry.
- Тесты кода: `tests/` — инварианты API (`tests/test_charts.py`) и правило
  выбора `a` (`tests/test_control_constant_selection.py`). Проверка примеров
  книги (консольный вывод + графики) — в `examples/` (см. `examples/README.md`),
  опыты — в `experiments/`, ноутбуки быстрого старта — в `notebooks/`.
