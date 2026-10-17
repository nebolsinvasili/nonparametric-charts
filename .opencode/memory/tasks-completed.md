# Журнал завершённых задач

Краткая история сделанного: дата, задача, что изменилось. Помогает не предлагать
заново уже сделанное/откаченное и быстро искать старые решения.

**Политика:** записи старше 30–60 дней переносить в `archive/tasks-YYYY.md`, чтобы
файл не разрастался и не «шумел» в контексте. Заведя запись, не забывай про
`architecture-decisions.md`, если решение архитектурное.

## Формат записи

```
### YYYY-MM-DD — Краткое название
- Что сделано: ...
- Затронуто: пути/файлы
- Проверка: команда/тест
```

---

### 2026-10-17 — Настройка агента под проект (по статье про Claude Code)

- Что сделано: `AGENTS.md` переписан как слой навигации + жёсткие правила;
  создана структура `.opencode/` — `rules/`, `memory/`, `skills/`, `templates/`,
  `agents/`, команда `wrap-up`; добавлен модуль стиля `src/utils/plot_style.py`;
  `instructions` подключены в `.opencode/opencode.json`.
- Затронуто: `AGENTS.md`, `.opencode/**`, `src/utils/plot_style.py`,
  `src/base/base_chart.py`, `src/utils/plotting.py`.
- Проверка: `poetry run python -c "from src.utils.plot_style import apply_minimal_latex_style"`.

### 2026-10-17 — Приведение проекта к непараметрическому виду + тесты по примерам книги

- Что сделано:
  - `AGENTS.md`/`pyproject.toml`/`rules/reference.md`: описание проекта —
    непараметрические (distribution-free) одномерные карты, а не «многомерные».
  - Исправлен расчёт `a` в `SignChart` и `SignedRankChart`: наименьшее достижимое
    значение (перебор снизу вверх, чётность `n`/`S`), fallback — максимум (`n`/`S`).
    См. ADR-007.
  - Удалён `src/charts/signed_rank_chartTTT.py` — дубликат старого `SignRankChart`.
    См. ADR-009.
  - Тесты переписаны по примерам книги: `tests/sign/` (4.1–4.3),
    `tests/signed_rank/` (4.4–4.5), `tests/test_control_constant_selection.py`;
    удалены параметрические тесты (`median/r/s/xbar`) и старый знаковый тест;
    фикстура `results_dir` сохраняет карты в `results/tests/`. См. ADR-008.
- Затронуто: `AGENTS.md`, `pyproject.toml`, `.opencode/rules/reference.md`,
  `.opencode/memory/*`, `src/charts/sign_chart.py`,
  `src/charts/signed_rank_chart.py`, `tests/**`.
- Проверка: `pytest` (не выполнен — нет сети для установки pandas/scipy/matplotlib;
  константы `a` сверены чистым Python-скриптом: sign n=1,8,10,14,16 → 1,8,10,12,14;
  SR n=4 → 10).

### 2026-10-17 — Единое имя `nonparametric-charts` (переименование ShCC → nonparametric-charts)

- Что сделано: имя проекта приведено к `nonparametric-charts` во всех местах —
  `pyproject.toml` (`name`), `AGENTS.md`, `.opencode/rules/reference.md`,
  `.opencode/memory/architecture-decisions.md`,
  `.opencode/skills/notebook-build/SKILL.md`, `tests/conftest.py`. Env-переменная
  `SHCC_COEFFICIENTS` → `NONPARAMETRIC_CHARTS_COEFFICIENTS`
  (`src/base/base_chart.py`). Kernel `shcc-py` → `nonparametric-charts-py`.
  В `notebooks/signed_rank_chart_analysis.ipynb` исправлен устаревший сохранённый
  вывод (`~/Projects/nparametric-charts` → `~/repo/nonparametric-charts`).
  Локальный каталог переименован `noparametric-charts` → `nonparametric-charts`,
  `git remote set-url` обновлён. См. ADR-010.
- Затронуто: `pyproject.toml`, `AGENTS.md`, `.opencode/**`, `src/base/base_chart.py`,
  `tests/conftest.py`, `notebooks/signed_rank_chart_analysis.ipynb`.
- Проверка: `grep -rni shcc` → пусто; `py_compile` base_chart.py/conftest.py — OK;
  JSON ноутбуков валиден. Репозиторий на GitHub нужно переименовать вручную.

### 2026-10-17 — Красивый вывод тестов (pytest-sugar)

- Что сделано: добавлен dev-зависимость `pytest-sugar` (`poetry add --group dev`);
  в `pyproject.toml` `[tool.pytest.ini_options]` добавлен
  `addopts = "-ra --durations=10"`. Прогон: 75 passed.
- Затронуто: `pyproject.toml`, `.opencode/rules/reference.md`.
- Проверка: `poetry run pytest` в псевдо-TTY — прогресс-бар, галочки,
  `Results (7.5s): 75 passed`, блок `slowest 10 durations`.

### 2026-10-17 — Подписи зон Вестерн-Электрик в единицах σ

- Что сделано: подписи зон на картах `SignChart`/`SignedRankChart` переведены на
  русский и выражены через σ (σ = a/3, т.к. контрольная граница a = 3σ):
  «Зона C (0…1σ)», «Зона B (1σ…2σ)», «Зона A (2σ…3σ)»; в легенде —
  «Граница зоны B (1σ)», «Граница зоны A (2σ)». Заодно убран наклон верхней
  подписи на инфоблок (инфоблок сжат до 3 строк, «Зона C» смещена с линии CL).
  Те же подписи в неиспользуемых `plotting.add_zones` и `BaseControlChart._add_zones`.
- Затронуто: `src/charts/sign_chart.py`, `src/charts/signed_rank_chart.py`,
  `src/utils/plotting.py`, `src/base/base_chart.py`.
- Проверка: `pytest -q` — 75 passed; графики `results/tests/example_4_{2,4}_*.png`
  перестроены и просмотрены (наложений подписей нет).

> Оговорка: подписи «через σ» — это соглашение `σ = a/3` (разметка), а не оценка
> истинного `SD` статистики (`SD(SN)=√n`, `SD(SR)=√(n(n+1)(2n+1)/6)`); см. ADR-011.

### 2026-10-17 — Ноутбуки пересобраны: без примеров, с проверкой возможностей и теории

- Что сделано: оба ноутбука (`notebooks/sign_chart_analysis.ipynb`,
  `notebooks/signed_rank_chart_analysis.ipynb`) пересобраны по каркасу:
  - убраны разделы с численными примерами книги (4.1–4.5) — теперь они только в
    `tests/sign/`, `tests/signed_rank/`; в шапке ноутбука — ссылка на тесты;
  - вместо локальных ре-реализаций — раздел «Возможности класса» с реальным
    публичным API (`calculate_limits`, `compare_approaches`, `get_sn_table`/
    `get_sr_table`, `get_sign_matrix`/`get_signed_rank_matrix`,
    `calculate_sign_test`/`calculate_signed_rank_test`, `get_violations`,
    `get_summary`, `plot`, `plot_comparison`); данные — через
    `DataLoader`/`DataPreprocessor`;
  - добавлен раздел «Проверка теории»: моменты `SN`/`SR`/`T+` пересчитаны
    независимо и сверены с табл. 4.1 (стр. 193) и табл. 4.3 (стр. 200);
    добавлены capability-check инварианты карты;
  - для SR — раздел проверки симметрии (обязательное условие).
- Найдено при сверке: книга для n=13 печатает `FAR=0.002`, `ARL=500`, что
  получается из округления хвоста `P(T13+ ≥ 86)=0.0012207 → 0.001` (табл. B);
  точные значения — `FAR=0.002441`, `ARL≈410`. Отражено в ноутбуке.
- Затронуто: `notebooks/*.ipynb` (сгенерированы скриптом
  `/tmp/opencode/build_notebooks.py`, затем исполнены `nbconvert --execute`).
- Проверка: оба ноутбука исполнены без ошибок (`jupyter nbconvert --execute`),
  инварианты карт — все `[OK]`.

### 2026-10-17 — TeX-отчёты по границам SN и SR (+ разбор отчёта с таблицей UCL)

- Что сделано: два самодостаточных документа в `docs/`:
  - `sn_bounds_theory.tex` — теория Shewhart-SN, вывод `a`
    (§4.2.1.1, стр. 189–196), формула хвоста, примеры (n=1,5,10,20),
    таблица `n=1..20`, 3 графика (pgfplots), код;
  - `sr_bounds_theory.tex` — теория Shewhart-SR (§4.2.1.2, стр. 196–202),
    чётность `SR ≡ S (mod 2)`, точное распределение перебором `2^n`,
    примеры (n=4,5,13), таблица `n=2..20`, 3 графика, код;
    плюс отдельный раздел «Разбор предоставленного отчёта» с таблицей 2:
    показано, что статистика/распределение совпадают, а расхождение —
    в критерии (`Pr(ψ≥UCL)≈0.05` против `FAR₀/2=0.00135`, ~37×) и в
    трактовке одностороннего хвоста как FAR двусторонней карты (занижение
    вдвое). Разобран `n=14` (книжное `a=91` против `UCL=53`).
  - `docs/Makefile` — сборка `pdflatex` (T2A + babel russian); вспомогательные
    файлы складываются в `docs/build/`, готовые PDF копируются в `docs/`.
    Цель `make clean` удаляет только `build/` и два собственных PDF и
    **не трогает** исходные PDF (`chakraborti_*.pdf`, `Klyachkin_*.pdf`).
    (Первый вариант `clean` с `rm -f *.pdf` случайно удалил эти
    первоисточники; восстановлены `git restore -- docs/`, цель переписана.)
- Решение по графике: пользователь выбрал pgfplots (самодостаточно, без
  внешних картинок) и сборку Makefile; движок — `pdflatex` (XeLaTeX в
  окружении без собранного формата `xelatex.fmt`; кириллица через T2A).
  Графики — минималистичный LaTeX-стиль (без сетки, тонкие линии, один
  акцент), координаты зашиты макросами `\def` (сгенерированы Python).
- Оговорка про код: `listings` под pdflatex не переваривает кириллицу в
  листингах, поэтому код в документах приведён с англоязычными
  комментариями, а пояснения — в тексте.
- Затронуто: `docs/sn_bounds_theory.tex`, `docs/sr_bounds_theory.tex`,
  `docs/Makefile`, `docs/*.pdf`.
- Проверка: `make` собирает оба PDF без ошибок и без `Overfull`.
