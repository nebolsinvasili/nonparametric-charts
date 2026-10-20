# Журнал веток

Контроль веток для крупных изменений (правило №8, `rules/profile.md`).

| Ветка | Статус | База | Тема | Открыта | Закрыта | Merge commit |
| --- | --- | --- | --- | --- | --- | --- |
| `chore/external-skills` | closed | `master` | Навыки через `npx skills` (ADR-015) | 2026-10-19 | 2026-10-19 | `90eaf3f` |
| `chore/docs-reorg` | closed | `master` | `docs/` → `ref/` + `reports/` (ADR-016) | 2026-10-19 | 2026-10-19 | `bc09ef3` |
| `chore/package-src-layout` | closed | `master` | Installable package, src-layout (ADR-017) | 2026-10-19 | 2026-10-19 | `becd4d4` |
| `chore/repo-split` | closed | `master` | `tests/` — код, `examples/`, `npc` (ADR-018) | 2026-10-19 | 2026-10-19 | `3ba1bb8` |
| `feat/cusum-charts` | closed | `master` | CUSUM-SN/SR, утилита статистик (ADR-020/022) | 2026-10-19 | 2026-10-19 | `1c192d5` |
| `chore/plot-style` | closed | `master` | Единый стиль графиков (ADR-021) | 2026-10-19 | 2026-10-19 | `ade862b` |
| `chore/experiments-style` | closed | `master` | Строгий вывод экспериментов | 2026-10-19 | 2026-10-19 | `391cb16` |
| `feat/cusum-run-length` | open | `master` | RL CUSUM: марковский движок, дизайн `(k,h)` (ADR-023) | 2026-10-19 | — | — |

Текущее состояние `feat/cusum-run-length`: 3b.0–3b.9 готовы (марковский RL,
симуляция, renewal, приближения, OC-кривые, подбор `h`, совместный дизайн
`(k, h)` с консервативным правилом, API/визуализация RL, тесты/производительность),
плюс процессные улучшения (алиас `npc experiment cusum`, кэш ARL, точная
квадратура SR для `n ≤ 20`); 3b.10 (кросс-валидация Python↔R, `npSPC`) готова,
при ней исправлен баг двусторонней цепи (ADR-025); 3b.11 (документирование,
отчёт `docs/reports/cusum_verification.tex/.pdf`) и ноутбук
`notebooks/cusum_analysis.ipynb` готовы. Все пункты DoD закрыты; ветка
готова к слиянию.

Статусы: `planned` → `open` → `closed`. Ветки после слияния удалены.

## Примечания к раскладке WIP (2026-10-19)

- Раскладка накопленного WIP сделана **по путям/файлам** (без `git add -p`).
- Мета-коммит `d673a98` (правило №7/№8, журнал, ADR/журнал задач) заодно захватил
  уже проиндексированные **чистые переименования** `src/* → src/nonparametric_charts/*`
  и удаление `coefficients.json` — переносы без изменения содержимого (попали в
  индекс до раскладки).
- Файлы, несущие изменения нескольких тем, отнесены к одной ветке:
  - `base_chart.py`, `sign_chart.py`, `signed_rank_chart.py` (layout + стиль +
    делегирование утилите) — в `chore/package-src-layout`;
  - `examples/README.md` (строки примеров 4.6/4.7/4.9) — в `chore/repo-split`;
  - цвета в `docs/reports/*.tex` — в `chore/docs-reorg`.
- Точка безопасности до раскладки: тег `wip-backup-2026-10-19`
  (можно удалить: `git tag -d wip-backup-2026-10-19`).
