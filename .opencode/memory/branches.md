# Журнал веток

Контроль веток для крупных изменений (правило №8, `rules/profile.md`).

| Ветка | Статус | База | Тема | Открыта | Закрыта | Merge commit |
| --- | --- | --- | --- | --- | --- | --- |
| `chore/external-skills` | planned | `master` | Навыки через `npx skills` (ADR-015) | — | — | — |
| `chore/docs-reorg` | planned | `master` | `docs/` → `ref/` + `reports/` (ADR-016) | — | — | — |
| `chore/package-src-layout` | planned | `master` | Installable package, src-layout (ADR-017) | — | — | — |
| `chore/repo-split` | planned | `master` | `tests/` — код, `examples/`, `npc` (ADR-018) | — | — | — |
| `feat/cusum-charts` | planned | `master` | CUSUM-SN/SR, утилита статистик (ADR-020/022) | — | — | — |
| `chore/plot-style` | planned | `master` | Единый стиль графиков (ADR-021) | — | — | — |
| `chore/experiments-style` | planned | `master` | Строгий вывод экспериментов | — | — | — |

Статусы: `planned` → `open` → `closed`.

## Примечания

- Раскладка накопленного WIP сделана **по путям/файлам** (без `git add -p`):
  часть файлов несут изменения нескольких тем, отнесены к одной ветке.
- Точка безопасности до раскладки: тег `wip-backup-2026-10-19`.
