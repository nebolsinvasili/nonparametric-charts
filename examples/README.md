# Проверка примеров книги

Скрипты в этом каталоге проверяют примеры из книги Chakraborti & Graham (2019),
*Nonparametric Statistical Process Control*. Каждый скрипт:

1. строит карту по данным примера;
2. печатает результаты в консоль (границы, статистики, сигналы);
3. сверяет их с книжными значениями и показывает `OK`/`FAIL`;
4. сохраняет график в `results/examples/`.

Это *отдельная от тестов кода* проверка: сверка с конкретными числами из книги.
Тесты библиотеки (без привязки к примерам) живут в `tests/`.

## Примеры

| Скрипт | Пример | Что проверяется |
| --- | --- | --- |
| `example_4_1_shewhart_sn_individual.py` | 4.1 | знаковая карта (Shewhart-SN) по индивидуальным наблюдениям, n = 1 (стр. 219–221) |
| `example_4_2_shewhart_sn_subgrouped.py` | 4.2 | знаковая карта (Shewhart-SN) по подгруппам, n = 10 (стр. 222–224) |
| `example_4_3_shewhart_sn_runs_2of2.py` | 4.3 | знаковая карта (Shewhart-SN) + правило «2 из 2», UWL/LWL = ±6 (стр. 224–225) |
| `example_4_4_shewhart_sr_signed_rank.py` | 4.4 | знако-ранговая карта (Shewhart-SR), n = 4 (стр. 225–228) |
| `example_4_5_shewhart_sr_runs_2of2.py` | 4.5 | знако-ранговая карта (Shewhart-SR) + правило «2 из 2» (стр. 228–229) |
| `example_4_6_cusum_sn_individual.py` | 4.6 | CUSUM-SN, индивидуальные измерения, k = 0.5, h = 3, сигнал t = 28 (стр. 229–231) |
| `example_4_7_cusum_sn_subgrouped.py` | 4.7 | CUSUM-SN по подгруппам, n = 10, k = 2, h = 8, сигнала нет (стр. 232–233) |
| `example_4_9_cusum_sr.py` | 4.9 | CUSUM-SR по подгруппам, n = 4, k = 3, h = 8, сигналы t = 10 и t = 12 (стр. 236–238) |

## Запуск

Из корня репозитория (пакет должен быть установлен или доступен `src/` —
скрипты добавляют его в `sys.path` сами):

```bash
# алиас (после poetry install / pip install .)
npc examples                 # все примеры

# один пример
poetry run python examples/example_4_2_shewhart_sn_subgrouped.py

# все примеры сразу
poetry run python examples/run_all.py
```

Графики сохраняются в `results/examples/` (каталог игнорируется git).
Ненулевой код возврата означает расхождение с книгой.
