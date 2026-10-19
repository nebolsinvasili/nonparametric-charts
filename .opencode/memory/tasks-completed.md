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
  `agents/`, команда `wrap-up`; добавлен модуль стиля `src/nonparametric_charts/utils/plot_style.py`;
  `instructions` подключены в `.opencode/opencode.json`.
- Затронуто: `AGENTS.md`, `.opencode/**`, `src/nonparametric_charts/utils/plot_style.py`,
  `src/nonparametric_charts/base/base_chart.py`, `src/nonparametric_charts/utils/plotting.py`.
- Проверка: `poetry run python -c "from nonparametric_charts.utils.plot_style import apply_minimal_latex_style"`.

### 2026-10-17 — Приведение проекта к непараметрическому виду + тесты по примерам книги

- Что сделано:
  - `AGENTS.md`/`pyproject.toml`/`rules/reference.md`: описание проекта —
    непараметрические (distribution-free) одномерные карты, а не «многомерные».
  - Исправлен расчёт `a` в `SignChart` и `SignedRankChart`: наименьшее достижимое
    значение (перебор снизу вверх, чётность `n`/`S`), fallback — максимум (`n`/`S`).
    См. ADR-007.
  - Удалён `src/nonparametric_charts/charts/signed_rank_chartTTT.py` — дубликат старого `SignRankChart`.
    См. ADR-009.
  - Тесты переписаны по примерам книги: `tests/sign/` (4.1–4.3),
    `tests/signed_rank/` (4.4–4.5), `tests/test_control_constant_selection.py`;
    удалены параметрические тесты (`median/r/s/xbar`) и старый знаковый тест;
    фикстура `results_dir` сохраняет карты в `results/tests/`. См. ADR-008.
- Затронуто: `AGENTS.md`, `pyproject.toml`, `.opencode/rules/reference.md`,
  `.opencode/memory/*`, `src/nonparametric_charts/charts/sign_chart.py`,
  `src/nonparametric_charts/charts/signed_rank_chart.py`, `tests/**`.
- Проверка: `pytest` (не выполнен — нет сети для установки pandas/scipy/matplotlib;
  константы `a` сверены чистым Python-скриптом: sign n=1,8,10,14,16 → 1,8,10,12,14;
  SR n=4 → 10).

### 2026-10-17 — Единое имя `nonparametric-charts` (переименование ShCC → nonparametric-charts)

- Что сделано: имя проекта приведено к `nonparametric-charts` во всех местах —
  `pyproject.toml` (`name`), `AGENTS.md`, `.opencode/rules/reference.md`,
  `.opencode/memory/architecture-decisions.md`,
  `.opencode/skills/notebook-build/SKILL.md`, `tests/conftest.py`. Env-переменная
  `SHCC_COEFFICIENTS` → `NONPARAMETRIC_CHARTS_COEFFICIENTS`
  (`src/nonparametric_charts/base/base_chart.py`). Kernel `shcc-py` → `nonparametric-charts-py`.
  В `notebooks/signed_rank_chart_analysis.ipynb` исправлен устаревший сохранённый
  вывод (`~/Projects/nparametric-charts` → `~/repo/nonparametric-charts`).
  Локальный каталог переименован `noparametric-charts` → `nonparametric-charts`,
  `git remote set-url` обновлён. См. ADR-010.
- Затронуто: `pyproject.toml`, `AGENTS.md`, `.opencode/**`, `src/nonparametric_charts/base/base_chart.py`,
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
- Затронуто: `src/nonparametric_charts/charts/sign_chart.py`, `src/nonparametric_charts/charts/signed_rank_chart.py`,
  `src/nonparametric_charts/utils/plotting.py`, `src/nonparametric_charts/base/base_chart.py`.
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
    файлы складываются в `docs/reports/build/`, готовые PDF копируются в `docs/`.
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

### 2026-10-17 — Разделы «Режимы выбора константы a» в отчётах SN и SR

- Что сделано: в оба TeX-отчёта добавлен раздел «Режимы выбора константы a»
  (после «Расчёт a», перед примерами/итогами):
  - обзорная таблица трёх режимов (`conservative`/`symmetric`/`nearest`);
  - формулы (уравнения для `a_cons`, `a_sym`, `a_near`, `P(|S|≥a)=2P(S≥a)`);
  - листинг кода трёх `_calc_a_*` + `compare_approaches`;
  - таблица сравнения режимов (`SN: n=1..20`, `SR: n=2..20`) с колонкой
    «чётность» (достижимо ли `a_near`);
  - пример `n=14` с кандидатами по режимам (SN: 12/14/10 и 7/9;
    SR: 91/93/89 и 62/60) + FAR/ARL;
  - два графика: критерий `nearest` (`P(|SN|≥a)`/`P(|SR|≥a)` и линия α)
    и сравнение режимов `a(n)`;
  - подраздел «Замечания по режимам».
- Ключевые выводы, зафиксированные в документах:
  - `symmetric` **тождественно** `conservative` для всех n (фактически
    два режима, а не три);
  - `nearest` для всех n возвращает **недостижимое** значение (чужой
    чётности), т.к. перебирает все целые без учёта чётности:
    SN n=14 → 7 (эквивалент 8), SR n=14 → 62 (эквивалент 63).
- Инструмент: `docs/reports/scripts/gen_coords.py` — детерминированный генератор
  координат/строк таблиц (то, что предлагалось ранее). Координаты
  по-прежнему зашиты макросами `\def` в сами `.tex` (документы
  самодостаточны).
- Добавлено в преамбулы: `\DeclareMathOperator*{\argmin}{arg\,min}`.
- Затронуто: `docs/sn_bounds_theory.tex`, `docs/sr_bounds_theory.tex`,
  `docs/reports/scripts/gen_coords.py` (новый), `docs/*.pdf`.
- Проверка: `make` → SN 9 стр., SR 11 стр., без ошибок и без `Overfull`;
  страницы с новыми таблицами/графиками просмотрены.

### 2026-10-18 — Отчёт о верификации SN-карты и сверка с R (npSPC, qcr)

- Что сделано: создан новый отчёт `docs/reports/sn_verification.tex` (9 стр.) строго по
  девяти пунктам плана пользователя: цель и задачи; математический базис;
  архитектура; обзор R-реализаций; сравнительная оценка; перекрёстный опыт;
  результаты и рекомендации; заключение; приложения. Первый в проекте отчёт со
  списком сокращений; англицизмы в прозе вычищены (код и имена пакетов —
  в исходном написании).
- Среда R установлена **без прав суперпользователя**: `micromamba` (Arch, sudo
  по паролю) → conda-forge `r-base` 4.6.1 в `/tmp/opencode/renv`.
  Пакет `npSPC` (нет в CRAN; репозиторий `CER-UFBA/npSPC`, функция
  `shewhart_sn`) собран из исходников. `qcr` 1.4 — из исходников; его
  обязательная зависимость `fda.usc` в conda-forge отсутствует, но собрана из
  скачанных исходников CRAN (загрузки через `install.packages` срывались,
  помог `curl` + `R CMD INSTALL`; для Фортрана поставлен conda `gfortran`).
- Ключевые результаты сверки:
  - `shewhart_sn` трактует `far` как **односторонний** порог: цель
    `P(T≥q)<far`. Поэтому при `far=0.0027` его границы совпадают с книжными
    всюду, кроме `n=13,16,19` (там они ниже: 11 vs 13, 12 vs 14, 13 vs 15), а
    фактический ЧЛТ доходит до ≈0.0054. При `far=0.00135` правило npSPC даёт
    ровно книжные границы при всех проверенных `n`.
  - Перекрёстная проверка на **одних** данных (`n=16`, `m=3000`, сдвиг с
    2001-й подгруппы): значения `SN` и метки сигналов совпали полностью; до
    сдвига npSPC дал 14 ложных тревог на 2000 подгрупп, наша граница — 1.
  - Опыт Монте-Карло (500 000 подгрупп) подтвердил точную биномиальную
    теорию.
  - Самодельная реализация с нормальной аппроксимацией `ceiling(z√n)`
    занижает границы (при `n=16` даёт 12 вместо 14) и завышает ЧЛТ.
  - В `qcr` классической знаковой карты нет: непараметрические функции
    `npqcs.*` многомерны и основаны на глубине данных; проверочный вызов
    `npqcs.r` прошёл.
- Новые файлы: `docs/reports/sn_verification.tex`/`.pdf`,
  `docs/reports/experiments/{sn_analysis.py, cross_validation.R, cross_check.py,
  custom_sign_chart.R, qcr_check.R, gen_figdata.py}`.
- Правки: `docs/Makefile` (+ цель `snver`, + `sn_verification.pdf`),
  `.gitignore` (+ `docs/reports/experiments/data_cross*.csv`).
- Проверка: `make` → три PDF (SN 9, SR 11, сверка 9), без ошибок и без
  `Overfull`; исходные PDF (`chakraborti_*`, `Klyachkin_*`) целы.
- Замечание: `notebooks/sign_chart_analysis.ipynb` и
  `docs/ref/1-s2.0-...pdf` — не мои изменения этой задачи, не трогал.

### 2026-10-18 — Отчёт SN-верификации: методы `a`, эксперимент по режимам, переименование

- Согласование обозначений: `c_value` → `a_value`, `_calculate_c_value` →
  `_calculate_a_value`, ключ `control_limits['c_value']` → `['a_value']` — в
  `src/nonparametric_charts/charts/sign_chart.py`, `src/nonparametric_charts/charts/signed_rank_chart.py`, трёх тестах,
  обоих ноутбуках и в `docs/reports/sn_verification.tex` («исправь параметры в коде»).
- В `docs/reports/sn_verification.tex`:
  - перенесён и адаптирован раздел «Методы выбора константы `a`» (из удалённого
    `sn_bounds_theory.tex`): формулы `a_cons` (eq:acons), `a_sym=a_cons`
    (eq:asym), `a_near` (eq:anear), точный хвост (eq:sntail); таблица режимов
    `n=1..20`; графики `a(n)`, достигнутый `FAR(n)`, критерий `nearest` при
    `n=14`; листинг трёх `_calc_a_*`;
  - разграничены «точный расчёт» (замкнутая биномиальная формула) и «численный
    эксперимент» (Монте-Карло, `N=500000`, стандартная ошибка ≤0.0007);
  - добавлен подраздел «Сводный эксперимент по методам» (`n=13,16,19`) с
    таблицами и выводом «что лучше»;
  - «Преимущества» и «Направления развития» — сплошным текстом (без списков);
  - «Независимые реализации» → «Реализации средствами базового R» + пояснение;
  - исправлено `ALR_0`→`ARL_0`; нормировка через `ARL_0=1/FAR_0≈370`.
- Сводный эксперимент (одни данные, `m=3000`, сдвиг с 2001-й, +1 SD):
  `conservative`=`symmetric`; `npSPC` при `far=0.00135` совпадает с нашим
  правилом при всех трёх `n`; при `far=0.0027` границы ниже (ложных тревог на
  `n=16`: 6 против 2); `nearest` (`α=0.05`) дал 136 ложных тревог — в СУП
  непригоден. Пакет вызывается через `shewhart_sn`, границы извлекаются
  перехватом внутреннего `plot_chart` (функция возвращает только ARL).
- Новые файлы: `docs/reports/experiments/modes_experiment.py`,
  `docs/reports/experiments/mode_comparison.R`, txt-инструкции
  `docs/reports/experiments/00_ENVIRONMENT.txt` и `01..06_*.txt` (установка R и
  пошаговое воспроизведение каждого опыта).
- Удалён `docs/sn_bounds_theory.tex`/`.pdf` (содержание перенесено). Обновлены
  `docs/Makefile` (`TARGETS`, цели `sr`/`snver`), `docs/reports/scripts/gen_coords.py`,
  `.gitignore` (`data_modes_*.csv`, `modes_*.csv`).
- Проверка: `poetry run pytest -q` → 75 passed; `make` → SR 11, верификация
  15 стр., без ошибок и без `Overfull`; исходные PDF целы.

### 2026-10-18 — Режим `symmetric` = нормальная аппроксимация; отчёт и опыты SR

- **ADR-012.** Переопределён `_calc_a_symmetric` как нормальная аппроксимация
  сразу в обеих картах: `a₀=⌈z_{1−FAR₀/2}·SD⌉` (`SD(SN)=√n`,
  `SD(SR)=√(n(n+1)(2n+1)/6)`), подъём до достижимой чётности, зажим `a≤n`/`a≤S`.
  Идентификатор `approach='symmetric'` и обратная совместимость сохранены;
  подпись — «Симметричный (нормальная аппроксимация)» (`APPROACH_LABELS`).
  Обновлены докстринги модулей/классов/методов обеих карт.
- **SR:** `_sr_distribution` переведён с перебора `2^n` на ДП-свёртку
  (`O(n·S)`, эквивалент перечисления) — распределение доступно при `n≳30`,
  тесты ускорились (119 passed, ~8.8 с).
- **Тесты:** `tests/test_control_constant_selection.py` — разделены
  «консервативный» и «нормальная аппроксимация», добавлены проверки
  `symmetric` для SN (`n=1..30`) и SR (`n=2..20`).
- **Теория:** `docs/sr_bounds_theory.tex` — таблица режимов, пример `n=14`
  (`sym`=97 против `cons`=91), графики (`\srASym`, `\srFARSym`), листинг,
  замечания переписаны под нормальную аппроксимацию; генератор
  `docs/reports/scripts/gen_coords.py` обновлён.
- **Новый отчёт `docs/reports/sr_verification.tex` (15 стр.)** — аналог SN-отчёта:
  мат.основы (статистика, допущение симметрии / Case K, моменты, ДП-свёртка),
  методы выбора `a`, реализация `SignedRankChart`, реализации на R
  (`npSPC`, `qcr`, базовый R), сопоставление, вычислительный эксперимент
  (перекрёстная проверка, FAR, мощность, анализ расхождений, сводка по
  методам), результаты/заключение/приложения. Макросы графиков —
  `docs/reports/sr_macros.tex` (генерируется `sr_gen_figdata.py`).
- **Новые опыты `docs/reports/experiments/sr/`:** `sr_analysis.py` (ДП-распределение,
  правила PR/`npSPC`, мощность свёрткой и Монте-Карло, время),
  `sr_cross_validation.R` + `sr_cross_check.py` (SR совпал с R: `True`;
  `npSPC` exact `a`=108 против нашего 110), `sr_custom.R`, `sr_qcr_check.R`,
  `sr_modes_experiment.py` + `sr_mode_comparison.R`, `sr_gen_figdata.py`,
  инструкции `01..06`. Ключевые факты: `npSPC` exact берёт **квантиль**, а не
  консервативную границу (его FAR может быть `> FAR₀`); `npSPC`
  (`exact=FALSE`) по эффективной границе совпадает с нашим `symmetric`;
  при малых `n` асимптотическая граница `npSPC` превышает `S`.
- **Ноутбуки** SN/SR: текст о `symmetric` поправлен, оба перезапущены
  (метки и числа обновлены).
- **Сборка:** `docs/Makefile` — цель `srver`, `TARGETS` из трёх PDF, правило
  генерации `sr_macros.tex`. Проверка: `poetry run pytest -q` → 119 passed;
  `make` → три PDF без ошибок, без `Overfull` и без `undefined`.

### 2026-10-18 — Переименование режимов: `conservative`→`exact`, `symmetric`→`normal`

- **ADR-013.** Имена режимов приведены к реальному методу: `conservative` →
  `exact` (точное распределение, критерий `FAR₀/2`), `symmetric` → `normal`
  (нормальная аппроксимация); `nearest` без изменений. Приватные методы
  `_calc_a_exact` / `_calc_a_normal`. Подписи — «Точный (консервативный, FAR₀)»
  и «Нормальная аппроксимация». `ApproachType = Literal['exact','nearest','normal']`,
  значение по умолчанию `approach='exact'`.
- **Обратная совместимость:** `APPROACH_ALIASES` и `normalize_approach`
  (`conservative→exact`, `symmetric→normal`) с `DeprecationWarning` в
  `__init__` и `calculate_limits` обеих карт.
- **Обновлено:** код обеих карт, `tests/test_control_constant_selection.py`
  (имена тестов и вызовы), скрипты `docs/reports/experiments/{sn,sr}/*` и
  `docs/reports/scripts/gen_coords.py`, отчёты `docs/{sn_verification,sr_verification,
  sr_bounds_theory}.tex` (идентификаторы, подписи, легенды, листинги,
  исправлен абзац про обратную совместимость), ноутбуки SN/SR (перезапуск).
- **Проверка:** `poetry run pytest -q` → 119 passed; `make` — три PDF чисто;
  ноутбуки перезапущены без ошибок.
- **Дополнение (§2.6 SN):** в `docs/reports/sn_verification.tex`, подраздел «Фазы I и II
  и вычислительная сложность», добавлено описание режима `normal` (граница —
  замкнутая нормальная аппроксимация `O(1)` + одна проверка хвоста `O(n)`,
  суммарно `O(n)` против `O(n²)` у `exact`/`nearest`) и строка замера в
  `tab:time` (`n=2..100`, режим `normal` ≈ 0.03 с; `exact` 0.24, `nearest` 0.74).
  Ручные правки пользователя (вставка «…или «хвост»» в §1.3) сохранены.
- **Правка §5.2 SN (мощность при сдвиге):** убрана наукообразная и размытая
  формулировка «точный расчёт / точный ответ / проверка формулы методом
  Монте-Карло». Введены «аналитический расчёт» (замкнутая биномиальная формула
  `T_i ~ Bin(n,p)`, `p=Φ(δ)`, пороги `u=⌈(n+a)/2⌉`, `l=⌊(n−a)/2⌋`) и «Проверка
  методом Монте-Карло» (независимая имитация). Подпись `tab:montecarlo` →
  «Проверка аналитической вероятности сигнала методом Монте-Карло (n=16,
  N=5·10⁵)»; столбцы `FAR, …` → `P, Монте-Карло` / `P, аналитически` (строки со
  сдвигом — это вероятность обнаружения, а не FAR). Сборка чисто, `Overfull` 0.
- **Правка §5.3 SN (анализ расхождений):** убран размытый вход «Расхождение
  обусловлено интерпретацией `far`». Введена рамка «две независимые причины»
  и заголовки `\paragraph`: «Трактовка параметра `far`» (npSPC задаёт `far` как
  вероятность одного хвоста; правило `eq:rule` нормирует двустороннюю FAR,
  поэтому значению пакета `far` отвечает наша `FAR₀=2·far`; при `far=0.00135`
  границы совпадают для `n=1..20`) и «Дискретность точной границы» (нормальная
  аппроксимация `⌈z√n⌉`, `z=z_{1−FAR₀/2}`, не учитывает чётность/достижимость).
  Таблица `tab:limits` переделана: явные заголовки `a_exact` / `FAR_exact` /
  `a_npSPC` / `FAR_npSPC` / `a_near` / `FAR_near`, добавлены столбцы
  `FAR_exact` и `FAR_near`, подпись
  исправлена (было «`n=1..20`», а строки выборочные). Сборка чисто, `Overfull` 0.

### 2026-10-19 — Установка пяти внешних навыков агента (skills.sh)

- **Что сделано:** установлены сторонние навыки через CLI экосистемы skills.sh
  (`npx skills add`, проектный уровень, `-a opencode`):
  - `obra/superpowers` — все 15 навыков методологии (brainstorming,
    writing-plans, test-driven-development, systematic-debugging и т. д.);
  - `OthmanAdi/planning-with-files` — 6 навыков (базовый + языковые варианты
    `-ar/-de/-es/-zh/-zht`);
  - `blader/humanizer` — удаление признаков ИИ-текста;
  - `Egonex-AI/Understand-Anything` — 9 навыков `understand-*` (граф знаний по
    коду);
  - `poteto/noodle` (`-s adversarial-review`) — адверсариальное кросс-модельное
    ревью. Источник `pedronauck/skills` из каталога skills.sh оказался устаревшим
    (навык из репозитория удалён), поэтому взят первоисточник.
  Итог: `.agents/skills/` (32 навыка) + корневой `skills-lock.json`.
  См. ADR-015.
- **Затронуто:** `.agents/skills/**`, `skills-lock.json`,
  `.opencode/memory/tasks-completed.md`, `.opencode/memory/architecture-decisions.md`.
- **Проверка:** `npx skills ls`; OpenCode зарегистрировал все навыки
  (появились в списке доступных), кастомные `.opencode/skills/` (book-lookup,
  notebook-build, style-check) не тронуты.

### 2026-10-19 — Реорганизация `docs/`: `ref/` (источники) и `reports/` (отчёты)

- **Что сделано:** каталог `docs/` разделён на две части:
  - `docs/ref/` — источники: `chakraborti_*.pdf`, `Klyachkin_*.pdf`,
    `1-s2.0-*.pdf` (статья);
  - `docs/reports/` — отчёты и всё для сборки: `sn_verification.tex/.pdf`,
    `sr_verification.tex/.pdf`, `sr_macros.tex`, `Makefile`, `build/`,
    `scripts/`, `experiments/sn|sr/`.
  Пути внутри отчётов/опытов приведены к виду «от корня репозитория»
  (`docs/reports/experiments/...`); из `Makefile` убран мёртвый таргет
  `sr_bounds_theory.pdf` (файл удалён), `cd ..` → `cd ../..`.
  См. ADR-016.
- **Затронуто:** `docs/**` (перенос), `AGENTS.md`, `.opencode/rules/reference.md`,
  `.opencode/rules/sources.md`, `.opencode/skills/book-lookup/SKILL.md`,
  `.opencode/memory/book-map.md`, `.gitignore`, `.tex`-отчёты, скрипты опытов.
- **Проверка:** `cd docs/reports && make` — оба PDF собраны без ошибок;
  греп по старым путям (`docs/experiments|scripts|sn_verification|…`) пуст.

### 2026-10-19 — Проект стал устанавливаемым пакетом (pip + poetry)

- **Что сделано:** по требованию пользователя `nonparametric-charts` теперь
  ставится и через `poetry`, и через `pip`:
  - код переведён в стандартную **src-layout**: `src/base|charts|utils` →
    `src/nonparametric_charts/{base,charts,utils}` (через `git mv`, история
    сохранена);
  - добавлены `__init__.py`: пакетный (публичный API `SignChart`,
    `SignedRankChart`, `BaseControlChart`, `__version__`) и в `base`/`charts`;
  - `pyproject.toml`: вместо `package-mode = false` —
    `[tool.poetry] packages = [{ include = "nonparametric_charts", from = "src" }]`;
    сборка — `poetry-core` (PEP 517), читается и `pip`.
  См. ADR-017 (заменяет ADR-002).
- **Импорты:** `from src.*` → `from nonparametric_charts.*` в `src/`, `tests/`,
  скриптах `docs/reports/experiments/*` и `docs/reports/scripts/*`; ноутбуки
  добавляют `../src` в `sys.path`, тесты — `src` (в `conftest.py`), чтобы
  работать и без установки.
- **Документация:** обновлены `AGENTS.md` (жёсткое правило №6, дерево, env),
  `.opencode/rules/reference.md` (дерево, env, pip), `plot-style.md`,
  `notebook-style.md`, навыки `notebook-build`/`style-check`/`book-lookup`,
  шаблоны, агенты, отчёт `sr_verification.tex` (пути модулей; экранированы
  подчёркивания в `\texttt`).
- **Проверка:** `poetry run pytest -q` → 119 passed; `poetry build` и
  `poetry run pip wheel --no-deps .` — wheel со всем пакетом и
  `coefficients.json`; импорт пакета проверен из корня и из `notebooks/`;
  `cd docs/reports && make` собирает оба PDF; ноутбуки — валидный JSON.

---

### 2026-10-19 — Разделение: `tests/` — код, `examples/` — примеры, `experiments/` — опыты

- **Что сделано:** проверка примеров книги вынесена из `tests/` в новый корневой
  `examples/` (5 скриптов печатают консольный отчёт, сверяют значения с книгой
  и сохраняют графики в `results/examples/`); `tests/` очищен до тестов кода —
  переписан `conftest.py`, добавлен `tests/test_charts.py`; опыты перенесены из
  `docs/reports/experiments/` в корневой `experiments/` (пути внутри обновлены до
  корня репозитория). См. ADR-018.
- **Затронуто:** `examples/**` (новый), `tests/` (удалены `sign/`, `signed_rank/`),
  `experiments/**` (перенос), `docs/reports/Makefile`, `docs/reports/*.tex`,
  `.gitignore`, `AGENTS.md`, `.opencode/rules/reference.md`.
- **Алиасы запуска:** entry point `npc` (`[project.scripts]`,
  `src/nonparametric_charts/cli.py`) — `npc test`, `npc examples`,
  `npc experiment {sn|sr|all}`; работают и через pip, и через poetry.
- **Проверка:** `poetry run pytest -q` → 111 passed;
  `poetry run python examples/run_all.py` → все 5 примеров совпали с книгой;
  `npc test`, `npc examples`, `npc experiment --list`/`sn` проверены.
- **Примечание:** ноутбуки не трогались (по просьбе), в шапках `notebooks/*.ipynb`
  остались ссылки на старые `tests/sign|signed_rank/` — обновить при следующей
  правке ноутбуков.

---

### 2026-10-19 — Единый строгий стиль вывода экспериментов

- **Что сделано:** консольный вывод и инструкции `experiments/**` приведены к
  строгому единому виду по требованию пользователя:
  - аббревиатуры только английские: `FAR`, `ARL`, `MRL`, `FA(IC)`, `delay`;
  - убраны «наш расчёт», «наше правило», «Pсигн», «ложн.трен.», «ЧЛТ», «СДС»;
  - методы называются нейтрально: `exact`, `normal`, `nearest(α=…)`,
    `normal(approx)`, `npSPC(far=…)`, `npSPC-exact/asym`;
  - условия задаются явно: `IC`, `δ = 1σ` (сдвиг медианы в σ);
  - заголовки секций конкретизируют, что именно проверяется
    (`FAR: теория vs Монте-Карло`), вместо «проверка точных значений»;
  - «книжное правило» в комментариях R → `exact`.
  Затронуты `sn_analysis.py`, `sr_analysis.py`, `cross_check.py`,
  `sr_cross_check.py`, `modes_experiment.py`, `sr_modes_experiment.py`,
  `custom_sign_chart.R`, `sr_custom.R` и инструкции `01/02/03/05_*.txt`.
- **Проверка:** запущены `sn_analysis.py`, `sr_analysis.py`, обе кросс-проверки —
  вывод читается, значения прежние (совпадение SN/SR Python↔R: True).
  Скрипты с R (`03_custom_*`, `05_modes_*`) не запускались: R в окружении нет;
  правки там только в заголовках/формате вывода.
- **Примечание:** прозу отчётов `docs/reports/{sn,sr}_verification.tex`
  («наша реализация», «нормальная аппроксимация», строки таблиц «наша: exact»)
  не трогали — по решению пользователя отчёты оставлены как есть.

### 2026-10-19 — Процедура построения новой карты + старт CUSUM (§4.2.2)

- **Что сделано:** оформлен межсессионный порядок постройки новых карт и заведён
  рабочий документ под CUSUM (см. ADR-019).
  - команда `.opencode/commands/new-chart.md` — этапы 0–12 с микро-этапами, шлюзами
    (`book-checker`, `style-check`, `adversarial-review`, `humanizer`) и сессионным
    протоколом;
  - шаблон `.opencode/templates/chart-plan.md` — рабочий документ карты
    (шапка, Definition of Done, досье, архитектура, план, журнал, риски);
  - починен `.opencode/templates/new-chart.md`: чек-лист `tests/<name>/` → `examples/`
    (+ `README`/`run_all`), добавлены ссылки на `/new-chart` и рабочий документ;
  - `AGENTS.md`: строки навигации на команду и рабочие документы карт.
- **CUSUM (§4.2.2):** создан `docs/reports/cusum_plan.md` с досье §4.2.2 (стр. 202–208)
  и рабочими примерами §4.3.2 (стр. 229–243): формулы ур. 4.7–4.12, дизайн `(h,k)`,
  Марков/симуляция, таблица примеров 4.6–4.10. Найдена **опечатка книги** в ур. 4.11
  (нижняя CUSUM-SR напечатана с `− k`; пример 4.9, стр. 237, использует `+ k`).
- **Затронуто:** `.opencode/commands/new-chart.md` (новый),
  `.opencode/templates/{chart-plan,new-chart}.md`, `AGENTS.md`,
  `docs/reports/cusum_plan.md` (новый), `.opencode/memory/*`.
- **Проверка:** текст книги выписан через `book-lookup` (печ. 202–208, 229–243);
  ур. 4.11 сверено с примером 4.9. Код/тесты не трогались.
- **Далее:** этап 0 — согласовать объём (CUSUM-SN и/или CUSUM-SR), проверить внешние
  реализации R для будущей кросс-валидации.

### 2026-10-19 — CUSUM-SN: ядро (фаза 3a)

- **Что сделано:** реализована CUSUM-карта по знакам (см. ADR-020).
  - `src/nonparametric_charts/utils/statistics.py` (`sign_counts`, `sign_statistic`) —
    общая знаковая статистика; `SignChart` делегирует ей расчёт знаков.
  - `src/nonparametric_charts/charts/cusum_sign_chart.py::CusumSignChart`:
    рекурсии `SN_t⁺ = max(0, SN_{t−1}⁺ + SN_t − k)` и
    `SN_t⁻ = min(0, SN_{t−1}⁻ + SN_t + k)` (ур. 4.7–4.8), счётчики `N⁺`/`N⁻`,
    правило первого сигнала (`≥ h` / `≤ −h`), `plot`, `get_summary`.
    `control_limits = {CL: 0, UCL: +h, LCL: −h, k, h, ...}`.
  - экспорты: `charts/__init__.py`, `utils/__init__.py`, `src/nonparametric_charts/__init__.py`.
  - тесты `tests/test_cusum_sign_chart.py` (9 тестов) по примерам 4.6 и 4.7.
- **Расширение:** объём первой итерации — только `CUSUM-SN` (решение пользователя);
  `CUSUM-SR` — следом на той же архитектуре.
- **Проверка:** `poetry run pytest -q` → **120 passed** (было 111; +9).
  Шлюз `book-checker`: расхождений нет; пример 4.6 воспроизводится точно
  (`t = 28`, `N⁺ = 6`), пример 4.7 — без сигнала.
- **Далее:** фаза 3b — распределение длины серии (Марков, пример 4.8) и подбор `h`
  под `ARL_IC` (сверка с рис. 4.5: `n=10, k=6, h=4 → ARL_IC≈500`).

### 2026-10-19 — CUSUM-SN: примеры книги (этап 4)

- **Что сделано:** добавлены скрипты проверки примеров книги:
  - `examples/example_4_6_cusum_sn_individual.py` — данные табл. 4.5, `k=0.5`, `h=3`;
    сверка `SN_t`, `SN_t⁺`, `N⁺` и сигнала (`t = 28`, `SN_t⁺ = 3`, `N⁺ = 6`,
    оценка сдвига `28 − 6 = 22`).
  - `examples/example_4_7_cusum_sn_subgrouped.py` — данные табл. 4.6, `n=10`,
    `k=2`, `h=8`; сверка обеих ветвей и счётчиков; сигнала нет.
  - `examples/README.md` — добавлены строки примеров 4.6 и 4.7.
- **Проверка:** `poetry run python examples/run_all.py` и `npc examples` —
  все **7** примеров совпали с книгой (было 5).
- **Далее:** фаза 3b (RL/подбор `h`) или этап 5 (ноутбук).

### 2026-10-19 — Единый академический стиль всех графиков

- **Что сделано:**
  - `utils/plot_style.py` переписан как единственный источник **семантических
    ролей** цвета: `INK`, `ACCENT`, `ALERT`, `CENTER`, `LIMIT`, `WARNING`,
    `ZONE_LINE`, `ZONE_FILL`, `GRID`, `PALETTE`; добавлены `ROLE_STYLES` и
    помощник `hline(ax, y, role, ...)`. Шрифт/размеры/рамки — в rcParams.
  - `base/base_chart.py` и `utils/plotting.py`: контрольные линии, зоны и
    подписи значений переведены на роли (CL — серый, границы — тёмно-серые,
    зоны — тонкие серые, нарушения — единый `ALERT`).
  - `charts/{sign,signed_rank,cusum_sign}_chart.py`: убраны `crimson`/`red`/
    `green`/`gold`/`darkorange`/`steelblue`/`forestgreen`, хардкод
    `fontsize`/`fontweight`; общий акцент `ACCENT` для всех карт; нижняя ветвь
    CUSUM — из `PALETTE`; `plot_comparison` — из `PALETTE`.
  - Примеры 4.3/4.5: UWL/LWL через `hline(..., "warning")`.
  - Ноутбук `signed_rank_chart_analysis.ipynb`: гистограмма/линии — роли.
  - TeX-отчёты: `\definecolor` приведены к палитре Python.
  - Правило `.opencode/rules/plot-style.md` дополнено таблицей ролей и запретом
    «сырых» цветов.
  - По запросу: границы получили сдержанный кирпичный `LIMIT`; легенда — в
    рамке, компактная (2 колонки, `loc='best'`), блок данных — «как есть» в
    правом верхнем углу (прозрачный патч не даёт легенде его перекрыть);
    включён `usetex=True` с `T2A`/`babel russian`, все подписи,
    включая кириллицу, набираются LaTeX-ом через `math_text()`.
  - CUSUM-SN и CUSUM-SR: подписи значений на **обеих** ветвях
    (положительные — сверху, отрицательные — снизу, нулевые — тоже,
    совпадающие нули одной подписью); добавлен запас сверху,
    чтобы блок данных не закрывал точки и подписи.
- **Проверка:** `poetry run pytest -q` → **120 passed**;
  `poetry run python examples/run_all.py` → все **7** примеров совпали.
- **См.:** ADR-021.

### 2026-10-19 — CUSUM-SR: ядро (этап 3) и пример книги 4.9 (этап 4)

- **Что сделано:** реализована CUSUM-карта по знаковым рангам (см. ADR-022).
  - `utils/statistics.py` — `signed_rank_details` / `signed_rank_statistic`
    (общая знаково-ранговая статистика); `SignedRankChart._calculate_sr_for_row`
    делегирует утилите (как `SignChart` делегирует знаковую).
  - `charts/cusum_signed_rank_chart.py::CusumSignedRankChart` — рекурсии
    `SR_t⁺ = max(0, SR_{t−1}⁺ + SR_t − k)` и
    `SR_t⁻ = min(0, SR_{t−1}⁻ + SR_t + k)` (ур. 4.10–4.11), счётчики `N⁺`/`N⁻`,
    правило первого сигнала, `plot`, `get_summary`; `control_limits` =
    `{CL: 0, UCL: +h, LCL: −h, k, h}`. По умолчанию `k = 3`, `h = 8` (пример 4.9).
    Опечатка книги (ур. 4.11: печатное `− k`) учтена — используем `+ k` по
    примеру 4.9 (стр. 237) и параллели с ур. 4.8.
  - экспорты: `charts/__init__.py`, `utils/__init__.py`,
    `src/nonparametric_charts/__init__.py`.
  - тесты `tests/test_cusum_signed_rank_chart.py` (11 тестов по примеру 4.9);
    пример `examples/example_4_9_cusum_sr.py` + строка в `examples/README.md`.
- **Проверка:** `poetry run pytest -q` → **131 passed** (было 120; +11);
  `poetry run npc examples` → все **8** примеров `OK`; график сверен с рис. 4.16.
- **Далее:** фаза 3b — RL (Марков, примеры 4.8/4.10) и подбор `h` под `ARL_IC`.


### 2026-10-19 — Имена примеров 4.1–4.5: добавлен тип карты

- **Что сделано:** скрипты примеров 4.1–4.5 назывались без типа карты
  (`example_4_1_individual.py`, `example_4_2_subgrouped.py`,
  `example_4_3_runs_2of2.py`, `example_4_4_signed_rank.py`,
  `example_4_5_runs_2of2.py`) — по имени нельзя было понять, какая карта.
  Переименованы по единому шаблону `example_<номер>_<тип>_<вариант>.py`,
  совпадающему с именем сохраняемого PNG:
  - `example_4_1_shewhart_sn_individual.py` — Shewhart-SN, n = 1;
  - `example_4_2_shewhart_sn_subgrouped.py` — Shewhart-SN, n = 10;
  - `example_4_3_shewhart_sn_runs_2of2.py` — Shewhart-SN + «2 из 2»;
  - `example_4_4_shewhart_sr_signed_rank.py` — Shewhart-SR, n = 4;
  - `example_4_5_shewhart_sr_runs_2of2.py` — Shewhart-SR + «2 из 2».
  Обновлены `examples/README.md` (таблица и пример запуска) и докстринг
  `examples/_common.py`. Исторические записи (`tasks-completed.md`,
  ADR-018, `docs/reports/cusum_plan.md`) не переписывались.
- **Проверка:** `poetry run python examples/run_all.py` → все **8** примеров `OK`
  (glob `example_*.py` в `run_all.py` и алиас `npc examples` подхватывают новые
  имена автоматически).

### 2026-10-19 — Карты Шухарта приведены к стилю CUSUM

- **Что сделано:** `SignChart.plot` и `SignedRankChart.plot` по оформлению
  выровнены под `CusumSignChart.plot` / `CusumSignedRankChart.plot`:
  - данные рисуются линией с маркерами `'-o'` (было: точки `scatter` + бледная
    соединительная ломаная); нарушения/сигналы — крупные точки
    `scatter(s=70, color=ALERT)`;
  - подписи значений — над точкой при `y ≥ 0` и под ней иначе, формат `.1f`
    (было: только сверху, целые);
  - запас по `y`: `y_low − 0.05·span` … `y_high + 0.25·span` (было симметрично) —
    блок данных больше не наползает на верхнюю границу;
  - правый отступ `+0.5` вместо `+3.2` (последний остаётся только при
    `show_zones=True`);
  - `show_zones` по умолчанию `False` (зоны A/B/C — опция), как в CUSUM;
    `value_offset` у знако-ранговой карты `(0, 0.6)` → `(0, 0.35)`.
  - Правило `.opencode/rules/plot-style.md` дополнено разделом «Единство карт
    Шухарта и CUSUM».
- **Проверка:** `poetry run pytest -q` → **131 passed**;
  `poetry run python examples/run_all.py` → все **8** примеров `OK`; графики
  `example_4_2_shewhart_sn_subgrouped.png`, `example_4_4_shewhart_sr_signed_rank.png`
  визуально сверены с `example_4_6_cusum_sn_individual.png` / `example_4_9_cusum_sr.png`.
- **Примечание:** ноутбуки `notebooks/*_chart_analysis.ipynb` вызывают `plot()`
  без аргументов — они автоматически получают новый стиль; не перезапускались.

### 2026-10-19 — Подписи данных и размер маркера сигнала

- **Что сделано:** по замечаниям к графикам:
  - `value_offset` во всех четырёх `plot()` переведён из **единиц данных** в
    **типографские пункты** (`textcoords='offset points'`, по умолчанию `(0, 4.0)`).
    Причина: на карте с малым размахом (пример 4.1, `SN = ±1`) смещение `0.35`
    в единицах данных давало огромный зазор, подписи уходили за края осей;
    на 4.4/4.5 (`±10`) тот же `0.35` был незаметен. Теперь зазор одинаков
    независимо от масштаба.
  - размер маркера сигнала/нарушения вынесен в `plot_style`:
    `DATA_MARKER_SIZE = 4.0` (диаметр, pt) и
    `SIGNAL_MARKER_SIZE = 2 * DATA_MARKER_SIZE**2 = 32` (площадь, pt²) —
    вдвое больше базового маркера по площади (было `s = 70`, т. е. в 4.4 раза
    больше по площади). Применено в `SignChart`, `SignedRankChart`,
    `CusumSignChart`, `CusumSignedRankChart`.
- **Проверка:** `poetry run pytest -q` → **131 passed**;
  `poetry run python examples/run_all.py` → все **8** примеров `OK`; визуально
  сверены 4.1 (подписи вплотную к точкам) и 4.4 (красный маркер умеренно крупнее).
- **См.:** `.opencode/rules/plot-style.md` (маркеры, `value_offset` в пунктах).

### 2026-10-19 — Правило веток и раскладка накопленного WIP по 7 веткам

- **Что сделано:**
  - добавлено жёсткое правило №8 «Ветки для крупных изменений» (`AGENTS.md`,
    `.opencode/rules/profile.md`) и журнал `.opencode/memory/branches.md`;
  - накопленный незакоммиченный WIP разложен на 7 тематических веток
    (`chore/external-skills`, `chore/docs-reorg`, `chore/package-src-layout`,
    `chore/repo-split`, `feat/cusum-charts`, `chore/plot-style`,
    `chore/experiments-style`), каждая слита в `master` через `merge --no-ff`
    и удалена;
  - мета-коммит `d673a98` (правила, ADR, журнал задач) — прямо в `master`.
- **Механика:** раскладка **по путям** (без `git add -p`); файлы, несущие
  несколько тем, отнесены к одной ветке (см. примечания в `branches.md`).
- **Проверка:** `poetry run pytest -q` → **135 passed**;
  `poetry run python examples/run_all.py` → все **8** примеров `OK`;
  `git status` пуст. Точка безопасности до раскладки — тег `wip-backup-2026-10-19`.
- **См.:** `.opencode/memory/branches.md`, план `~/.opencode/plan/branch-workflow.md`.

### 2026-10-19 — Общий помощник подписей значений + тесты стиля

- **Что сделано:**
  - `plot_style.annotate_values(ax, x, y, *, mask=None, side='auto',
    offset=(0, 4.0), fmt='{:.1f}', fontsize=9, color=INK)` — единая подпись
    значений у точек: смещение в типографских пунктах, `side` (`'auto'` —
    над/под по знаку, `'above'`/`'below'` — принудительно), `mask` — какие
    точки подписывать.
  - Все четыре `plot()` (`SignChart`, `SignedRankChart`, `CusumSignChart`,
    `CusumSignedRankChart`) переведены на этот помощник вместо локальных
    циклов `ax.annotate` (в CUSUM — `side='above'`/`'below'` + `mask`, чтобы
    совпадающие нули подписывались один раз); из CUSUM-карт убран ставший
    ненужным импорт `INK`.
  - новый `tests/test_plot_style.py` (4 теста): размер маркера сигнала,
    постановка подписей по знаку, **независимость зазора от масштаба оси**
    (регрессия на грабли 4.1), `mask`/`side`.
- **Проверка:** `poetry run pytest -q` → **135 passed** (было 131; +4);
  `poetry run python examples/run_all.py` → все **8** примеров `OK`; графики
  после рефакторинга не изменились.
- **См.:** `.opencode/rules/plot-style.md`.
- **Замечено (не трогал):** `utils/plotting.py` (`add_control_lines`,
  `add_zones`, `add_values_on_points`) нигде не импортируется — мёртвый код;
  в `cusum_sign_chart.py` неиспользуемый импорт `ZONE_LINE` (F401).

### 2026-10-19 — 3b.0–3b.1: марковский расчёт длины серии CUSUM

- Что сделано:
  - зафиксирован чек-лист фазы 3b (3b.0–3b.11) в `docs/reports/cusum_plan.md`;
  - ADR-023: эталон RL — марковская цепь, остальные методы (симуляция,
    интегральное уравнение, приближения) — независимые проверки; дизайн
    `(k, h)` — после движков;
  - новый `src/nonparametric_charts/utils/run_length.py`: общий движок для
    дискретного шага (`upper`/`lower`/`two`), состояния по ур. 4.9/4.12,
    `ARL`/`SDRL`/`MRL`/перцентили/PMF/CDF по ур. 3.22–3.24; распределения
    `SN` (биномиальное, `p` включая OOC) и `SR` (точное нулевое распределение
    Уилкоксона); явная ошибка при бесконечной ARL;
  - `RunLengthResult` с `summary()`; методы `run_length()` у
    `CusumSignChart` и `CusumSignedRankChart`; экспорты в `utils/__init__.py`;
  - `tests/test_run_length.py` (12 тестов).
- Проверка: пример 4.8 — `ARL=16.615`, `SDRL=15.509`, перцентили
  `2/6/12/23/48`; пример 4.10 — `6.809`, `6.106`, `1/2/5/9/19`; рис. 4.5
  (двусторонняя) — `ARL=460.3` (в книге `454.2`); `pytest -q` → **147 passed**;
  `npc examples` → 8/8 `OK`.
- Замечено: рис. 4.6 (`n=10, k=41, h=24`) по формулам книги даёт
  `ARL ≈ 79 500`, а не `500.30`; проверять симуляцией и R (3b.2/3b.10).

### 2026-10-19 — 3b.2: симуляция длины серии CUSUM

- Что сделано: `simulate_cusum_run_length` и обёртки для SN/SR в
  `utils/run_length.py` — Монте-Карло по алгоритму книги, `seed`, `n_rep`,
  `SE(ARL)`, эмпирические `ARL/SDRL/MRL`/перцентили/PMF/CDF; явная ошибка при
  недостижимом сигнале (`max_t`); экспорты; 3 теста в `tests/test_run_length.py`.
- Проверка: пример 4.8 → `ARL=16.69` (точно `16.615`, в пределах 3 SE);
  рис. 4.5 → `461.05` (точно `460.28`); `pytest -q` → **150 passed**.
- Далее: 3b.3 — интегральное уравнение/renewal.

### 2026-10-19 — 3b.3: renewal / интегральный метод для RL

- Что сделано: `renewal_cusum_run_length` — независимое распространение
  распределения по состояниям без обращения `Q`; PMF/CDF, моменты через
  выживание; общий `_prepare_step_distribution`; проверка достижимости
  поглощения; 3 теста.
- Проверка: совпадение с марковским движком на примерах 4.8/4.10 до `1e-10`
  (ARL/SDRL, перцентили идентичны); `pytest -q` → **153 passed**.
- Далее: 3b.4/3b.5.

### 2026-10-19 — примеры 4.8 и 4.10 (марковский RL)

- Что сделано: добавлены `examples/example_4_8_cusum_sn_markov.py` и
  `examples/example_4_10_cusum_sr_markov.py` — пространство состояний, матрица
  `Q`, вероятности сигнала, RL-характеристики, PMF/CDF-график; общий
  `plot_run_length` в `examples/_common.py`; `RunLengthResult.transition_matrix`
  (марковский метод); README обновлён.
- Проверка: 4.8 — `ARL=16.615`, `SDRL=15.509`, перцентили `2/6/12/23/48`;
  4.10 — `6.809`, `6.106`, `1/2/5/9/19`; `Q` совпадает с табл. 4.11/4.14;
  `npc examples` → **10/10 OK**; `pytest -q` → 153 passed.

### 2026-10-19 — 3b.4–3b.6: приближения, OC-кривые, подбор `h`

- Что сделано:
  - `utils/run_length_design.py`: распределения `SN`/`SR` при сдвиге
    (`sign_step_distribution_shift`, `signed_rank_step_distribution_shift`),
    `oc_curve`, приближения `siegmund_arl`/`wald_arl`/`compare_arl_methods`,
    `design_h` + `design_sign_h`/`design_signed_rank_h`, `DesignResult`;
    стандартизованные распределения центрируются по медиане, поэтому IC-ARL
    не зависит от `F`;
  - методы `design_h()` у `CusumSignChart`/`CusumSignedRankChart`; экспорты;
  - `tests/test_run_length_design.py` (26 тестов);
  - `experiments/cusum/01_oc_curves.py` — таблицы и график OC-кривых SN/SR
    по распределениям.
- Решение: для точного решётчатого RL `ARL(h)` ступенчатая, поэтому вместо
  бисекции/Брента — перебор критических `h` с выбором ближайшей ARL.
- Проверка: пример 4.8 → `h=4`, `ARL=16.615`; пример 4.10 → `h=6`,
  `ARL=6.809`; рис. 4.5 → `h=4`, `ARL=460.28`; рис. 4.6 (цель 500) →
  `h=14`, `ARL=480.60` (книжные `h=24`/`500.30` не воспроизводятся);
  `pytest -q` → **179 passed**; `npc examples` → **10/10 OK**.
- Далее: 3b.7 — выбор `k` и совместный дизайн `(k, h)`.
