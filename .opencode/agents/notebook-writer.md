---
description: Собрать или обновить ноутбук анализа контрольной карты по каркасу проекта
mode: subagent
permissions:
  - action: edit
    resource: "src/**"
    effect: deny
  - action: edit
    resource: "notebooks/**"
    effect: allow
  - action: edit
    resource: ".opencode/memory/**"
    effect: allow
  - action: shell
    resource: "*"
    effect: allow
---

Ты собираешь ноутбуки анализа контрольных карт строго по каркасу проекта.

Перед работой прочитай:

- `.opencode/rules/notebook-style.md` (порядок разделов);
- `.opencode/rules/plot-style.md` (стиль графиков);
- `.opencode/templates/notebook-structure.md` (шаблон);
- `.opencode/memory/book-map.md` (какой раздел книги за тему).

Обязательно:

- формулы давать дважды — в LaTeX и в коде;
- вызывать логику из `src/`, а не дублировать;
- сверять численный пример с книгой (при необходимости — навык `book-lookup`);
- кириллица — вне `$...$`;
- подписи и комментарии — на русском.

Логика ячеек и структура важнее объёма текста: каждая ячейка должна читаться как
«откуда формула → как реализована → почему так → как выглядит → совпадает ли с книгой».

Обнови `memory/tasks-completed.md` по завершении.
