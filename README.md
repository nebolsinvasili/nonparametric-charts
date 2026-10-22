# nonparametric-charts

Python-библиотека непараметрических (distribution-free) контрольных карт
Шухарта и CUSUM для **одномерных** данных процесса. Карты не требуют
нормальности: знаковая контролирует медиану, знаково-ранговая — медиану
симметричного распределения.

Первоисточник методов — Chakraborti & Graham (2019), *Nonparametric
Statistical Process Control* (Wiley). Ссылки на разделы и печатные страницы
даны в докстрингах, отчётах и ноутбуках.

## Что внутри

| Класс | Метод | Раздел книги |
| --- | --- | --- |
| `SignChart` | знаковая карта Шухарта (Shewhart-SN) | § 4.2.1.1 |
| `SignedRankChart` | знаково-ранговая карта Шухарта (Shewhart-SR) | § 4.2.1.2 |
| `CusumSignChart` | CUSUM по знакам (CUSUM-SN) | § 4.2.2.1 |
| `CusumSignedRankChart` | CUSUM по знаковым рангам (CUSUM-SR) | § 4.2.2.4 |

Дополнительно доступны:

- точный марковский расчёт распределения длины серии (`cusum_run_length`);
- симуляция и renewal-проверки;
- OC-кривые `ARL(δ)`;
- подбор `h` и совместный подбор `(k, h)` под номинальный `ARL_IC`;
- единый минималистичный LaTeX-стиль графиков.

## Требования

- Python >= 3.14;
- для установки через Poetry — Poetry 2.x;
- для отчётов — TeX Live с `pgfplots`, `booktabs`, `listings`, `babel-russian`;
- для кросс-валидации с R — отдельное окружение `npSPC` (см.
  `experiments/00_ENVIRONMENT.txt`).

## Установка

Из корня репозитория:

```bash
# вариант 1: Poetry (рекомендуется для разработки)
poetry install --with dev

# вариант 2: pip
python -m pip install .

# проверка импорта
poetry run python -c "import nonparametric_charts; print(nonparametric_charts.__version__)"
```

Пакет использует `src`-layout, поэтому импорт всегда абсолютный:

```python
from nonparametric_charts.charts import CusumSignChart
from nonparametric_charts.utils import cusum_run_length
```

## Формат данных

`pandas.DataFrame`, где:

- **строка** — подгруппа (момент времени);
- **столбец** — наблюдение внутри подгруппы;
- `sample_size` — число столбцов `n`;
- `target_value` — целевое значение `μ₀` (если не задано, берётся медиана
  всех данных).

Пример: 30 подгрупп по 10 наблюдений.

```python
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
data = pd.DataFrame(rng.normal(size=(30, 10)))
```

## Быстрый старт

```python
from nonparametric_charts import CusumSignChart

chart = CusumSignChart(
    data,
    sample_size=10,
    target_value=0.0,
    k=2.0,
    h=8.0,
)
limits = chart.calculate_limits()
print(limits)

fig, ax = chart.plot()          # график CUSUM-SN
summary = chart.get_summary()   # статистики, сигналы, счётчики
```

Подбор параметров под номинальную `ARL_IC`:

```python
# только h при фиксированном k
h_result = chart.design_h(target_arl=370.0, sided='two')
print(h_result.h, h_result.arl, h_result.note)

# совместный подбор (k, h) под целевой сдвиг δ = 1
design = chart.design_kh(target_arl=370.0, delta=1.0, sided='two')
print(design.k, design.h, design.arl_ic, design.arl_ooc)
print(design.table.head())
```

`design_kh` выбирает `k` первым (аналог правила `k = δ/2` для
параметрической карты), затем `h` под номинал. Критерий оптимальности —
минимум `ARL_OOC`; при сетке `δ` используется минимакс. Подробный алгоритм —
в `experiments/cusum/README.md`.

## Команды

Все команды рассчитаны на запуск из корня репозитория.

| Команда | Что делает | Куда пишет результат |
| --- | --- | --- |
| `poetry run npc test` | все тесты `pytest` | stdout |
| `poetry run npc test --fast` | тесты без `@pytest.mark.slow` | stdout |
| `poetry run npc test --slow` | только медленные тесты | stdout |
| `poetry run npc examples` | проверка всех примеров книги | `results/examples/` |
| `poetry run npc examples 4.1 4.4` | только выбранные примеры | `results/examples/` |
| `poetry run npc experiment cusum` | все опыты CUSUM `01…06` | `results/experiments/` |
| `poetry run npc experiment --list` | список скриптов опытов | stdout |
| `make -C docs/reports cusum` | сборка PDF отчёта CUSUM | `docs/reports/*.pdf` |
| `make -C docs/reports check` | проверка логов TeX | stdout |

`npc` — entry point пакета (`pyproject.toml`). В таблице используется
`poetry run npc`; если окружение активировано (`poetry shell` или
`.venv/bin` в `PATH`), можно писать просто `npc ...`. Если entry point
недоступен, те же действия выполняются напрямую:

```bash
poetry run pytest -q
poetry run python examples/run_all.py
poetry run python experiments/cusum/03_kh_design.py
```

### Важно про опыты

- `poetry run npc experiment cusum` запускает и `05_cross_validation.py`, для которого
  нужны R и пакет `npSPC`. Без R запускайте остальные опыты по одному.
- `05_cross_validation.py --no-r` работает только при наличии ранее
  выгруженных CSV в `experiments/cusum/xval/`.
- Результаты опытов (`results/`, `experiments/*/xval/`) не коммитятся:
  они пересоздаются командами.

## Воспроизведение результатов

### 1. Примеры книги

```bash
poetry run npc examples
```

Ожидаемый итог: `Все примеры (10) прошли проверку`. Каждый пример печатает
`OK`/`FAIL` по своим числам и сохраняет график в `results/examples/`.

### 2. OC-кривые CUSUM

```bash
poetry run python experiments/cusum/01_oc_curves.py
```

Создаёт `results/experiments/cusum_oc_curves.png`, печатает таблицы
`ARL(δ)` для normal, `t`, Laplace, logistic, uniform (SN также gamma).

### 3. Подбор `(k, h)` для `n = 14`

Пример воспроизводит результаты, использованные при проверке ускорения:

```bash
poetry run python - <<'PY'
from nonparametric_charts.utils.run_length_design import design_kh

for statistic in ('SN', 'SR'):
    for target in (370.0, 500.0):
        result = design_kh(
            n=14, target_arl=target, delta=1.0,
            statistic=statistic, sided='two',
        )
        print(
            statistic, target,
            'k =', result.k, 'h =', result.h,
            'ARL_IC =', round(result.arl_ic, 4),
            'ARL_OOC =', round(result.arl_ooc, 4),
        )
PY
```

Ожидаемые значения (двусторонняя карта, `δ = 1`, консервативное правило):

| Карта | `ARL_IC` | `k` | `h` | Факт. `ARL_IC` | `ARL_OOC` |
| --- | ---: | ---: | ---: | ---: | ---: |
| SN | 370 | 5 | 7 | 353.3481 | 1.9887 |
| SN | 500 | 10 | 2 | 546.1333 | 3.0850 |
| SR | 370 | 54 | 37 | 355.4879 | 1.6246 |
| SR | 500 | 54 | 39 | 464.9837 | 1.6965 |

Для SN при номинале 500 точное значение на решётке недостижимо: лучшее
`h = 2` даёт `546.13` (отклонение 9.2 %, в пределах допуска 10 %). Это
свойство ступенчатой `ARL(h)`, а не ошибка поиска.

### 4. Производительность

```bash
poetry run python experiments/cusum/04_performance.py
```

Печатает фазы расчёта, рост стоимости по `n`, время `design_kh`; сохраняет
`cusum_performance.png` и `cusum_performance.txt`. Время зависит от машины,
поэтому сравнивайте не абсолютные секунды, а порядок и соотношения.

### 5. Кросс-валидация Python ↔ R

```bash
# один раз: подготовить R + npSPC
bash experiments/cusum/setup_renv.sh

# сверка
R_LIBS=/tmp/opencode/renv/lib/R/library \
RSCRIPT=/tmp/opencode/renv/bin/Rscript \
poetry run python experiments/cusum/05_cross_validation.py
```

Без R (если `experiments/cusum/xval/` уже есть):

```bash
poetry run python experiments/cusum/05_cross_validation.py --no-r
```

Результат: `results/experiments/cusum_cross_validation.txt`.

### 6. Отчёты

```bash
cd docs/reports
make cusum        # CUSUM
make              # все три отчёта
make check        # ошибки/overfull/underfull
```

Готовые PDF лежат в `docs/reports/`. Макросы графиков генерируются
автоматически (`06_gen_figdata.py`), вручную их не правят. Подробности —
`docs/reports/README.md`.

### 7. Ноутбуки

```bash
cd notebooks
jupyter lab
```

Ноутбуки рассчитаны на запуск **из каталога `notebooks/`**: они добавляют
`../src` в `sys.path`. Подробности — `notebooks/README.md`.

## Алгоритмы (кратко)

### CUSUM и длина серии

Для статистики подгруппы `Z_t` (SN или SR):

```text
S_t⁺ = max(0, S_{t−1}⁺ + Z_t − k),   S_0⁺ = 0
S_t⁻ = min(0, S_{t−1}⁻ + Z_t + k),   S_0⁻ = 0
```

Сигнал — первое достижение `S_t⁺ ≥ h` или `S_t⁻ ≤ −h`. Длина серии `N` —
номер этого момента. `ARL = E[N]` в IC.

Точный расчёт: марковская цепь по непоглощающим состояниям, матрица `Q`,
`ARL = ξ(I − Q)⁻¹1` (ур. 3.22–3.24, стр. 112; ур. 4.9/4.12, стр. 203–206).
PMF, `SDRL`, `MRL` и перцентили считаются по той же цепи.

### Подбор `(k, h)`

1. `k = frac · E[Z_δ]` — непараметрический аналог `k = δ/2`; кандидаты
   привязываются к решётке статистики.
2. Для каждого `k` подбирается `h`:
   - считается только `ARL`, без PMF (`cached_arl`);
   - граница `h` расширяется экспоненциально до первого `ARL ≥` номинала;
   - затем бисекция по индексам решётки;
   - при нарушении монотонности — линейный скан (fallback);
   - консервативное правило берёт наибольшее `h` с `ARL ≤` номинала;
   - если номинал недостижим, возвращается ближайшее сверху и заполняется
     `note`.
3. Выбирается допустимая пара с минимальным `ARL_OOC` (при сетке `δ` —
   минимакс). Допуск по `ARL_IC` — `tol = 0.10` по умолчанию.

Матрица `Q` строится векторизованно; на сетке с шагом `0.5` состояния не
округляются. Это ускоряет подбор в разы без изменения результатов.

## Структура репозитория

```text
src/nonparametric_charts/
  base/                 BaseControlChart
  charts/               SignChart, SignedRankChart, CusumSignChart, CusumSignedRankChart
  utils/
    run_length.py       точный RL, симуляция, renewal
    run_length_design.py OC-кривые, ARL-приближения, подбор (k, h)
    plot_style.py       единый LaTeX-стиль
    plotting.py         графики PMF/CDF
tests/                  тесты API и инвариантов
examples/               проверка примеров книги (10 примеров)
experiments/            опыты SN, SR, CUSUM + R-сверка
notebooks/              ноутбуки быстрого старта
docs/reports/           TeX/PDF-отчёты и планы
docs/ref/               книги и статьи-первоисточники
results/                результаты запусков (gitignored)
```

## Документация

- `experiments/README.md` — опыты, окружение, порядок запуска.
- `experiments/cusum/README.md` — подробные алгоритмы CUSUM и подбора,
  описание каждого скрипта, ожидаемые результаты.
- `docs/reports/README.md` — сборка и проверка отчётов.
- `notebooks/README.md` — запуск ноутбуков и kernel.
- `docs/reports/cusum_plan.md` — рабочий план и журнал CUSUM.
- `.opencode/memory/architecture-decisions.md` — ADR, включая ADR-026
  (ускорение подбора) и ADR-027 (документация воспроизводимости).
- `AGENTS.md` — правила проекта и навигация.

## Соглашения

- Формулы, константы и правила сигнала сверяются с книгой Chakraborti &
  Graham; в коде указывается раздел и печатная страница.
- Графики оформляются через `apply_minimal_latex_style()`.
- Новые опыты и модули сопровождаются README: назначение, алгоритм,
  команда запуска, входы/выходы, ожидаемый результат.
- Старые версии кода сохраняются в истории git; ветки и артефакты,
  фиксирующие воспроизводимость, не удаляются без явного разрешения.
