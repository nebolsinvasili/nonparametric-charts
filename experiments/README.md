# Опыты и воспроизведение

Каталог `experiments/` содержит вычислительные проверки, которые **не входят**
в обычный `pytest`: сверка с книгой, Монте-Карло, кросс-валидация с R,
подбор параметров, производительность, генерация данных для отчётов.

Тесты API и инвариантов лежат в `tests/`; примеры книги — в `examples/`.
Здесь — исследовательские запуски и их ожидаемые результаты.

## Быстрый старт

```bash
cd <корень репозитория>

# Python-окружение
poetry install --with dev

# все опыты CUSUM (нужен R для 05; см. ниже)
poetry run npc experiment cusum

# только Python-опыты CUSUM
poetry run python experiments/cusum/01_oc_curves.py
poetry run python experiments/cusum/02_sr_exact_vs_mc.py
poetry run python experiments/cusum/03_kh_design.py
poetry run python experiments/cusum/04_performance.py
poetry run python experiments/cusum/06_gen_figdata.py > /tmp/cusum_macros.tex
```

Скрипты сами добавляют `src/` в `sys.path`, поэтому установка пакета для
запуска не обязательна, но Poetry-окружение должно содержать зависимости.

## Структура

```text
experiments/
  00_ENVIRONMENT.txt      общее окружение Python/R, установка npSPC
  sn/                     исторические опыты знаковой карты
  sr/                     исторические опыты знаково-ранговой карты
  cusum/                  CUSUM-SN/SR: OC, RL, подбор, R-сверка
```

### `experiments/sn/` и `experiments/sr/`

Это расчётное сопровождение отчётов `docs/reports/sn_verification.tex` и
`sr_verification.tex`. Файлы `01_*.txt` … `06_*.txt` — **runbook'и**: что
запускать, какие пакеты нужны, что должно получиться. Это не логи запусков.

| Шаг | SN | SR | Требуется |
| --- | --- | --- | --- |
| 01 | `sn_analysis.py` | `sr_analysis.py` | Python |
| 02 | `cross_check.py` + `cross_validation.R` | `sr_cross_check.py` + `sr_cross_validation.R` | Python, R + npSPC |
| 03 | `custom_sign_chart.R` | `sr_custom.R` | R |
| 04 | `qcr_check.R` | `sr_qcr_check.R` | R + qcr |
| 05 | `modes_experiment.py` + `mode_comparison.R` | `sr_modes_experiment.py` + `sr_mode_comparison.R` | Python, R + npSPC |
| 06 | `gen_figdata.py` | `sr_gen_figdata.py` | Python |

Команды и ожидаемые числа — в одноимённых `NN_*.txt`. Промежуточные CSV
(`data_*.csv`, `*_out.csv`, `modes_*.csv`) пересоздаются и в git не входят.

### `experiments/cusum/`

Подробное описание алгоритмов, каждого скрипта и ожидаемых результатов —
в `experiments/cusum/README.md`. Кратко:

| Скрипт | Назначение | Выход |
| --- | --- | --- |
| `01_oc_curves.py` | `ARL(δ)` для SN/SR и распределений | `results/experiments/cusum_oc_curves.png` |
| `02_sr_exact_vs_mc.py` | точное распределение SR против Монте-Карло | `cusum_sr_exact_vs_mc.png` |
| `03_kh_design.py` | подбор `(k, h)` для `n = 5…20` | `cusum_kh_design.png`, `.txt` |
| `04_performance.py` | фазы RL, рост по `n`, время подбора | `cusum_performance.png`, `.txt` |
| `05_cross_validation.py` | Python против npSPC (R) | `cusum_cross_validation.txt` |
| `06_gen_figdata.py` | макросы графиков для отчёта | stdout → `docs/reports/cusum_macros.tex` |

## Окружение R

Нужно только для сверок с `npSPC` и `qcr`. Готовый идемпотентный скрипт:

```bash
bash experiments/cusum/setup_renv.sh
```

По умолчанию окружение создаётся в `/tmp/opencode/renv`, micromamba — в
`/tmp/opencode/mm`. Пути переопределяются переменными `RENV` и `MAMBA_DIR`.

Проверка:

```bash
R_LIBS=$RENV/lib/R/library $RENV/bin/Rscript -e 'library(npSPC)'
```

Ручная установка и список пакетов — в `experiments/00_ENVIRONMENT.txt`.

## Порядок воспроизведения с нуля

1. `poetry install --with dev`.
2. `poetry run npc test --fast` — быстрая проверка кода.
3. `poetry run npc examples` — примеры книги.
4. `poetry run python experiments/cusum/01_oc_curves.py`.
5. `poetry run python experiments/cusum/02_sr_exact_vs_mc.py`.
6. `poetry run python experiments/cusum/03_kh_design.py`.
7. `poetry run python experiments/cusum/04_performance.py`.
8. При необходимости R: `bash experiments/cusum/setup_renv.sh`, затем
   `05_cross_validation.py`.
9. `make -C docs/reports cusum` — отчёт.
10. `cd notebooks && jupyter lab` — ноутбуки.

## Выходы и артефакты

- `results/examples/` — графики примеров книги.
- `results/experiments/` — таблицы и графики опытов.
- `experiments/cusum/xval/` — CSV кросс-валидации (создаются R-стороной).
- `docs/reports/build/` — вспомогательные файлы LaTeX.

Каталог `results/` и промежуточные CSV в git не коммитятся: их всегда можно
пересоздать командами выше.

## Частые проблемы

**`ModuleNotFoundError: nonparametric_charts`** — запускайте из корня
репозитория или установите пакет (`poetry install` / `pip install .`).

**`npc: command not found`** — entry point не установлен; используйте
`poetry run python ...` или `python -m nonparametric_charts.cli`.

**`05_cross_validation.py` падает без R** — это ожидаемо. Либо установите
R-окружение, либо запускайте с `--no-r` при наличии
`experiments/cusum/xval/`.

**Долгий `03_kh_design.py`** — это нормально для SR при больших `n`. Для
быстрой проверки запускайте отдельный пример из
`experiments/cusum/README.md`.

**Другие числа, чем в README** — проверьте `n`, `δ`, `sided`, `ic_rule`,
версию Python и параметры `tol`; время выполнения от машины зависит, а
`k`, `h` и `ARL` при тех же входах — нет.

## Правило сопровождения

Каждый новый опыт должен иметь:

- README или раздел в существующем README;
- описание алгоритма и ссылку на формулу/раздел книги;
- точную команду запуска;
- входы, выходы и ожидаемый результат;
- сведения о внешних зависимостях (R, пакеты, данные).
