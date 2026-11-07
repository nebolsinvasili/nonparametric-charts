#!/usr/bin/env python3
"""Контроль перевода книги: включения, маркеры TODO, рисунки, объём.

Скрипт проверяет механические факты, чтобы таблицы статуса в
``book/README.md`` и ``docs/reports/coverage_plan.md`` не расходились
с исходниками. Запуск:

    make -C book check           # предупреждения, код возврата 0
    make -C book check-strict    # строго: отсутствующие рисунки — ошибка

Логика контроля: пока часть книги не переведена, в ней остаются маркеры
``\\todo{...}``. Их ожидаемое число зафиксировано в ``EXPECTED_TODO``.
Появился лишний TODO — незакрытая заготовка; TODO стало меньше — перевод
продвинулся, но статус в README и реестре не обновлён. И то и другое —
повод обновить ожидания и таблицы.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAIN = ROOT / 'document.tex'

#: Ожидаемое число маркеров ``\todo`` по файлам (непереведённые части).
#: При переводе главы — уменьшить; при добавлении новой заготовки — увеличить.
EXPECTED_TODO = {
    'document.tex': 2,   # приложения A и B
    'chapter-1.tex': 5,  # §1.1–1.5
}

TODO_RE = re.compile(r'\\todo\{')
INCLUDE_RE = re.compile(r'\\include\{([^}]+)\}')
IMAGE_RE = re.compile(r'images/[^"}\s]+')


def read(path: Path) -> str:
    """Читает файл; логи LaTeX могут быть не в UTF-8."""
    return path.read_text(encoding='utf-8', errors='replace')


def counts(text: str) -> dict:
    body = '\n'.join(
        line for line in text.splitlines() if not line.lstrip().startswith('%')
    )
    return {
        'words': len(re.findall(r'\w+', re.sub(r'\\[a-zA-Z]+', ' ', body))),
        'todo': len(TODO_RE.findall(body)),
        'sections': len(re.findall(r'\\section\{', body)),
        'subsections': len(re.findall(r'\\subsection\{', body)),
        'figures': len(re.findall(r'\\begin\{figure\}', body)),
        'tables': len(re.findall(r'\\begin\{table\}', body)),
    }


def main() -> int:
    strict = '--strict' in sys.argv

    problems: list[str] = []
    warnings: list[str] = []

    if not MAIN.exists():
        print(f'ОШИБКА: нет {MAIN}')
        return 1

    main_text = read(MAIN)
    included = INCLUDE_RE.findall(main_text)

    tables = {}
    for name in ['document.tex', *included]:
        path = ROOT / name
        if not path.exists():
            problems.append(f'{name}: файл не найден (проверьте \\include)')
            continue
        text = read(path)
        stat = counts(text)
        tables[name] = stat

        expected = EXPECTED_TODO.get(name, 0)
        if stat['todo'] != expected:
            kind = 'незакрытая заготовка' if stat['todo'] > expected else 'перевод продвинулся'
            problems.append(
                f'{name}: маркеров TODO {stat["todo"]}, ожидалось {expected} '
                f'({kind}) — обновите EXPECTED_TODO, book/README.md и '
                'docs/reports/coverage_plan.md'
            )

    # Рисунки: все упомянутые файлы должны существовать.
    referenced = set()
    for name in tables:
        referenced.update(IMAGE_RE.findall(read(ROOT / name)))
    missing = sorted(ref for ref in referenced if not (ROOT / ref).exists())
    if missing:
        warnings.append(
            f'нет {len(missing)} рисунков: {", ".join(Path(m).name for m in missing)}'
        )

    # Лог сборки (если есть): ошибки поиска файлов и неопределённые ссылки.
    log = ROOT / 'document.log'
    build_errors = 0
    undefined = 0
    latex_errors = 0
    if log.exists():
        log_text = read(log)
        build_errors = log_text.count('not found')
        undefined = log_text.count('undefined')
        latex_errors = len(re.findall(r'^! ', log_text, re.MULTILINE))

    # Свежесть PDF: он должен быть не старше исходников.
    pdf = ROOT / 'document.pdf'
    if not pdf.exists():
        warnings.append('нет document.pdf — выполните make')
    else:
        newest = max((ROOT / name).stat().st_mtime for name in tables)
        if pdf.stat().st_mtime < newest:
            warnings.append('document.pdf старше исходников — пересоберите (make)')

    # Сводка.
    print('=' * 72)
    print('ПЕРЕВОД КНИГИ: Chakraborti & Graham (2019)')
    print('=' * 72)
    header = f'{"файл":<16}{"слов":>8}{"разделов":>10}{"подразд.":>10}{"рис.":>6}{"табл.":>6}{"TODO":>6}'
    print(header)
    print('-' * 72)
    total_words = 0
    for name, stat in tables.items():
        total_words += stat['words']
        print(
            f'{name:<16}{stat["words"]:>8}{stat["sections"]:>10}'
            f'{stat["subsections"]:>10}{stat["figures"]:>6}{stat["tables"]:>6}'
            f'{stat["todo"]:>6}'
        )
    print('-' * 72)
    print(f'{"итого":<16}{total_words:>8}')
    print()

    for text in problems:
        print(f'ОШИБКА: {text}')
    for text in warnings:
        print(f'ПРЕДУПРЕЖДЕНИЕ: {text}')
    if build_errors or undefined:
        print(
            f'ПРЕДУПРЕЖДЕНИЕ: в document.log {build_errors} сообщений «not found», '
            f'{undefined} «undefined» — проверьте рисунки/ссылки'
        )
    if latex_errors:
        print(
            f'ПРЕДУПРЕЖДЕНИЕ: в document.log {latex_errors} ошибок LaTeX '
            '(ожидаемы только из-за отсутствующих рисунков)'
        )

    if not problems and not warnings:
        print('OK: исходники согласованы с заявленным статусом')
    print()

    if problems:
        return 1
    if strict and (missing or build_errors or undefined):
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
