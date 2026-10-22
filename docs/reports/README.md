# Отчёты: сборка и проверка

Каталог `docs/reports/` содержит TeX-отчёты о верификации карт и рабочие
документы:

| Файл | Содержание |
| --- | --- |
| `sn_verification.tex/.pdf` | знаковая карта Шухарта (SN) |
| `sr_verification.tex/.pdf` | знаково-ранговая карта Шухарта (SR) |
| `cusum_verification.tex/.pdf` | непараметрические CUSUM-SN/SR |
| `sr_macros.tex`, `cusum_macros.tex` | сгенерированные макросы графиков |
| `cusum_plan.md` | рабочий план и журнал CUSUM |

PDF-файлы коммитятся; вспомогательные `.aux/.log/.toc/.out` и `build/` —
нет.

## Требования

- `pdflatex` (TeX Live);
- пакеты `pgfplots`, `booktabs`, `listings`, `babel-russian`, `T2A`,
  `hyperref`, `geometry`, `amsmath`;
- Python-окружение Poetry для генерации макросов.

Проверка:

```bash
pdflatex --version
poetry run python -c "import nonparametric_charts"
```

## Сборка

Из каталога `docs/reports/`:

```bash
make cusum     # только CUSUM
make snver     # только SN
make srver     # только SR
make           # все три отчёта
```

Или из корня репозитория:

```bash
make -C docs/reports cusum
make -C docs/reports
```

Каждый отчёт собирается **двумя проходами** `pdflatex` (оглавление и
перекрёстные ссылки). Готовый PDF копируется из `build/` в
`docs/reports/`.

## Проверка

```bash
make check
```

Печатает для каждого лога:

```text
cusum_verification         overfull=5   underfull=20  errors=0
sn_verification            overfull=0   underfull=14  errors=0
sr_verification            overfull=4   underfull=8   errors=0
```

- `errors` — ошибки LaTeX, undefined references/control sequences; должно
  быть `0`, иначе `make check` возвращает ненулевой код;
- `overfull`/`underfull` — информационные предупреждения. Норма проекта —
  не больше 8 overfull на отчёт; новые overfull лучше править текстом или
  переносами, а не уменьшением шрифта.

Логи лежат в `docs/reports/build/*.log`.

## Макросы графиков

`cusum_macros.tex` и `sr_macros.tex` генерируются скриптами, вручную их не
редактируют:

```bash
# CUSUM
poetry run python experiments/cusum/06_gen_figdata.py \
    > docs/reports/cusum_macros.tex

# SR
poetry run python experiments/sr/sr_gen_figdata.py \
    > docs/reports/sr_macros.tex
```

`make cusum` и `make srver` вызывают эти команды автоматически, если
макросы отсутствуют или устарели. Если изменились данные/параметры
графиков, удалите соответствующий `*_macros.tex` и пересоберите отчёт.

## Ожидаемые результаты

На текущем состоянии проекта:

| Отчёт | Страниц | `make check` |
| --- | ---: | --- |
| `cusum_verification.pdf` | 13 | `overfull=5`, `errors=0` |
| `sn_verification.pdf` | 15 | `overfull=0`, `errors=0` |
| `sr_verification.pdf` | 14 | `overfull=4`, `errors=0` |

Число страниц может измениться после правок текста; важны `errors=0` и
отсутствие новых overfull.

## Быстрая проверка после правок

```bash
cd docs/reports
make cusum
make check
pdfinfo cusum_verification.pdf | grep Pages
```

Если PDF не изменился по смыслу, но пересобрался с другой датой, git может
показать бинарную модификацию. Перед коммитом проверьте, что изменения
действительно нужны; случайные пересборки лучше не коммитить.

## Частые проблемы

**`Undefined control sequence` в caption** — некоторые команды (например,
`\path`) нельзя использовать в moving arguments. Замените на `\texttt{...}`
или вынесите команду из caption.

**`LaTeX Error: File ... not found`** — не хватает TeX-пакета; установите
его через менеджер TeX Live.

**Кириллица не отображается** — проверьте `T2A` и `babel-russian` в
преамбуле; движок должен быть `pdflatex`.

**`make check` падает, хотя PDF собрался** — смотрите `errors` в логах:
undefined references часто лечатся повторным проходом, а реальные ошибки —
только правкой TeX.

**Макросы не обновились** — `make` не всегда видит изменения, если файл уже
существует; удалите `cusum_macros.tex`/`sr_macros.tex` и пересоберите.

## Соглашения

- Формулы и числа сверяются с книгой; в тексте указываются раздел и
  печатная страница.
- Графики — минималистичный LaTeX-стиль, единые цвета и подписи.
- Новые таблицы/рисунки сопровождаются ссылкой `\label` и пояснением, что
  именно проверяется.
- После изменения отчёта обновляйте `docs/reports/*_plan.md` и память
  проекта, если меняются выводы или открытые вопросы.
