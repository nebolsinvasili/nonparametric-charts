# Глоссарий перевода

Единые русские соответствия терминов книги. При первом употреблении в главе
термин даётся по-русски, английский — в скобках. Идентификаторы кода и
обозначения не переводятся.

## Основы SPC

| English | Русский | Примечание / в коде |
| --- | --- | --- |
| statistical process control (SPC) | статистический контроль процессов (SPC) | |
| control chart | контрольная карта | |
| charting statistic | статистика для нанесения на карту | `subgroups[...]` |
| center line (CL) | центральная линия (CL) | `CL` |
| upper/lower control limit (UCL/LCL) | верхняя/нижняя контрольная граница (UCL/LCL) | `UCL`, `LCL` |
| warning limit (UWL/LWL) | предупреждающая граница (UWL/LWL) | `plot_style.WARNING` |
| in-control (IC) / out-of-control (OOC) | в статистически управляемом состоянии (IC) / вышедший из-под контроля (OOC) | |
| common cause | общая (случайная) причина | |
| special (assignable) cause | особая (назначаемая) причина | |
| rational subgrouping | рациональное разделение на подгруппы | |
| subgroup | подгруппа | строка `DataFrame` |
| false alarm | ложная тревога | |
| signal / signaling rule | сигнал / правило сигнала | `_find_violations` |
| sensitivity rules | правила чувствительности | §3.5.1 |
| runs-type signaling rules | правила сигналов на основе серий | §3.5.2, §4.8.1 |
| shift | сдвиг | параметр `δ` |
| process location / scale | положение / масштаб процесса | |
| design of a control chart | проектирование контрольной карты | |
| operating characteristic curve (OC-curve) | кривая операционной характеристики (OC-кривая) | `oc_curve` |

## Случаи и фазы

| English | Русский | Примечание / в коде |
| --- | --- | --- |
| Case K (known parameters) | случай K (параметры известны) | |
| Case U (unknown parameters) | случай U (параметры неизвестны) | |
| Phase I / Phase II | фаза I / фаза II | |
| reference sample | эталонная (референсная) выборка | гл. 4.4, объём `m` |

## Длина серии

| English | Русский | Примечание / в коде |
| --- | --- | --- |
| run length (RL) | длина серии (RL) | `RunLengthResult` |
| average run length (ARL) | средняя длина серии (ARL) | `arl` |
| standard deviation of run length (SDRL) | стандартное отклонение длины серии (SDRL) | `sdrl` |
| median run length (MRL) | медиана длины серии (MRL) | `mrl` |
| false alarm probability (FAP) | вероятность ложной тревоги (FAP) | |
| false alarm rate (FAR) | частота ложных тревог (FAR) | `FAR` |
| average number of samples to signal (ANSS) | среднее число выборок до сигнала (ANSS) | |
| average number of observations to signal (ANOS) | среднее число наблюдений до сигнала (ANOS) | |
| average time to signal (ATS) | среднее время до сигнала (ATS) | |
| steady-state limits | стационарные (асимптотические) границы | EWMA, §4.2.3 |
| decision interval | интервал решения | `h` (CUSUM) |
| reference value | референсное значение | `k` (CUSUM) |

## Карты и статистики

| English | Русский | Примечание / в коде |
| --- | --- | --- |
| Shewhart chart | карта Шухарта | |
| CUSUM chart | карта кумулятивных сумм (CUSUM) | |
| EWMA chart | карта экспоненциально взвешенного скользящего среднего (EWMA) | |
| sign statistic / sign chart | знаковая статистика / знаковая карта | `SN`, `SignChart` |
| signed-rank statistic / chart | знаково-ранговая статистика / карта знаковых рангов | `SR`, `SignedRankChart` |
| Wilcoxon signed-rank statistic | статистика знаковых рангов Уилкоксона | `T_plus` |
| precedence statistic / chart | статистика предшествования (precedence) / карта предшествования | §4.4.1.1 |
| Med chart | карта медианы (Med) | §4.4.1.1.7 |
| Mann–Whitney (MW) statistic | статистика Манна–Уитни (MW) | §4.4.1.2 |
| exceedance statistic | статистика превышений (exceedance) | CUSUM-EX, EWMA-EX |
| Wilcoxon rank-sum statistic | статистика ранговых сумм Уилкоксона | CUSUM-rank, EWMA-rank |
| mean-rank chart | карта средних рангов | §5.2.1.2.1 |
| scale-rank chart | карта рангов масштаба | §5.2.1.2.3 |
| Min chart / CUMIN chart | карта минимума (Min) / карта CUMIN | §5.2.2 |
| bootstrap chart | бутстрэп-карта | §5.2.3 |
| change-point model | модель точки изменения | §5.2.4 |
| variable sample size / interval (VSS/VSI) | переменный объём выборки / переменный интервал (VSS/VSI) | §5.2.5 |
| self-starting chart | самозапускающаяся карта | §4.7 |

## Спорные термины

Фиксируются здесь, чтобы в разных главах не появлялись разные варианты.

| English | Решение | Альтернативы |
| --- | --- | --- |
| charting statistic | «статистика для нанесения на карту» | «картируемая статистика», «статистика карты» |
| precedence test/chart | «предшествование (precedence)» с англ. в скобках | «тест опережения», «критерий первенства» |
| runs-type rules | «правила серий» | «правила серийного типа» |
| in-control | «в статистически управляемом состоянии (IC)» | «управляемое состояние» |
| false alarm rate | «частота ложных тревог» | «доля ложных тревог» |
| steady-state limits | «стационарные (асимптотические) границы» | «установившиеся границы» |
