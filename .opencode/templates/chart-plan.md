# Рабочий документ карты: <Название> (`<ChartName>Chart`)

> Постоянный документ по одной карте. НЕ авто-подгружается в контекст; здесь
> подробности, в `memory/tasks-completed.md` — только короткие записи.
> Порядок работы — команда `/new-chart` (`.opencode/commands/new-chart.md`).

## Шапка

- **Карта:** <название> (`<ChartName>Chart`).
- **Раздел книги:** Chakraborti & Graham (2019), § <раздел>, стр. <a>–<b>.
- **Case:** K / U.
- **Статистика:** <SN / SR / ...>.
- **Статус:** этап <N> из 12.
- **Дата начала:** YYYY-MM-DD.

## Definition of Done

- [ ] Код + тесты (`pytest`) зелёные.
- [ ] Примеры книги (`examples/`, `npc examples`) — `OK`.
- [ ] Ноутбук исполняется, `style-check` пройден.
- [ ] Опыты + кросс-валидация (Python↔R) + инструкции воспроизведения.
- [ ] Отчёт `docs/reports/<chart>_verification.tex/.pdf`, `make` чисто.
- [ ] Память обновлена (`tasks-completed`, ADR, `book-map`).

**Не делаем:** <что вне объёма>.

## Досье первоисточника (этап 1)

| Утверждение (статистика / границы / правило / характеристики) | Ссылка (§, печ. стр.) | Примечание / расхождение |
| --- | --- | --- |
|  |  |  |

Открытые вопросы к первоисточнику: <...>

## Архитектура (этап 2)

- **API класса:** `__init__(...)`, методы, ключи `control_limits`.
- **Режимы / параметры метода:** <...>.
- **Общее с `BaseControlChart`:** <...>.
- **Расположение модулей:** `charts/` / `utils/`.
- **ADR:** ADR-NNN <название> (что выбрано / отвергнуто).

## План реализации (чек-лист)

- [ ] `tests/...`
- [ ] `src/nonparametric_charts/charts/<chart>.py`
- [ ] экспорт в `src/nonparametric_charts/__init__.py` (+ `cli`, если нужно)
- [ ] `examples/...`
- [ ] `notebooks/<chart>_analysis.ipynb`
- [ ] `experiments/<chart>/...`
- [ ] `docs/reports/<chart>_verification.tex`

## Журнал прогресса (по этапам)

Запись на каждый микро-этап: дата → этап → сделано → проверка → далее.

### YYYY-MM-DD — этап N
- Сделано: ...
- Проверка: ...
- Далее: ...

## Открытые вопросы и риски

- <...>

## Артефакты (ссылки)

- Код: `src/nonparametric_charts/charts/<chart>.py`
- Тесты: `tests/...`
- Примеры: `examples/...`
- Ноутбук: `notebooks/<chart>_analysis.ipynb`
- Опыты: `experiments/<chart>/...`
- Отчёт: `docs/reports/<chart>_verification.tex/.pdf`
