#!/usr/bin/env python3
"""Проверка таблиц и подписей в LaTeX-исходниках книги.

Ловит ошибки, которые иначе всплывают только в логе pdflatex (и то не как
искомая строка, а как «Extra alignment tab» или «Argument of
\\caption@ydblarg»):

1. **Число колонок.** Для каждого ``tabular`` число колонок в преамбуле
   (``l``/``c``/``r``/``p{...}``, с учётом ``*{n}{spec}`` и ``\\multicolumn``)
   сверяется с числом ячеек в строках ``\\toprule ... \\bottomrule``.
2. **``\\footnote`` в ``\\caption``.** При наличии списка таблиц/рисунков
   падают ``\\caption@ydblarg``; примечание нужно вынести под заголовок.
3. **Ширина по символам.** Преамбула, которая не влезает в ``\\textwidth``
   при 12pt, отмечается как предупреждение: PDF это переживёт, но таблица
   вылезет за поля.

Запуск::

    book/lint_tables.py            # только ошибки, код возврата 1 при находке
    book/lint_tables.py --warn     # плюс предупреждения о ширине
    book/lint_tables.py chapter-4.tex

Подключён к ``make -C book check-strict``.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

#: Приблизительная ширина ``\textwidth`` при 12pt/a4 и полях 2.5 см, pt.
TEXTWIDTH_PT = 455.0
#: Ширина одного «обычного» столбца таблицы (l/c/r) при \small, pt.
COLWIDTH_PT = 34.0
#: Ширина только цифр/знака, pt (r-столбцы у нас числовые).
NARROW_PT = 30.0

BEGIN_RE = re.compile(r'\\begin\{(tabular)\}')
FOOTNOTE_CAPTION_RE = re.compile(
    r'\\caption(?:\[[^\]]*\])?\{(?:[^{}]|\{[^{}]*\})*\\footnote\b'
)
IMAGE_RE = re.compile(r'images/[^"}\s]+')
RULE_RE = re.compile(r'\\(?:top|mid|bottom)rule\b|\\(?:cmid)?rule\b')


def spec_to_columns(spec: str) -> list[str]:
    """Преамбула ``tabular`` → список типов колонок (по одной на колонку)."""
    spec = re.sub(r'@\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', '', spec)
    spec = re.sub(r'[!><]\{[^{}]*\}', '', spec)

    columns: list[str] = []
    i = 0
    while i < len(spec):
        char = spec[i]
        if char in 'lcrX':
            columns.append(char)
            i += 1
        elif char in 'pmb':
            columns.append(char)
            i += 1
            while i < len(spec) and spec[i] != '{':
                i += 1
            depth = 0
            while i < len(spec):
                if spec[i] == '{':
                    depth += 1
                elif spec[i] == '}':
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                i += 1
        elif char == '*':
            match = re.match(r'\*\{(\d+)\}', spec[i:])
            if match:
                count = int(match.group(1))
                i += match.end()
                j = i
                while j < len(spec) and spec[j] != '{':
                    j += 1
                depth = 0
                k = j
                while k < len(spec):
                    if spec[k] == '{':
                        depth += 1
                    elif spec[k] == '}':
                        depth -= 1
                        if depth == 0:
                            break
                    k += 1
                inner = spec_to_columns(spec[j + 1:k])
                columns.extend(inner * count)
                i = k + 1
            else:
                i += 1
        else:
            i += 1
    return columns


def split_braced(text: str, start: int) -> tuple[str, int]:
    """Возвращает содержимое ``{...}``, начинающегося в ``start``, и позицию за ним."""
    depth = 0
    for pos in range(start, len(text)):
        if text[pos] == '{':
            depth += 1
        elif text[pos] == '}':
            depth -= 1
            if depth == 0:
                return text[start + 1:pos], pos + 1
    return text[start + 1:], len(text)


def strip_comments(text: str) -> str:
    """Убирает ``%``-комментарии (кроме ``\\%``), заменяя их пробелом."""
    out: list[str] = []
    i = 0
    while i < len(text):
        char = text[i]
        if char == '%' and (i == 0 or text[i - 1] != '\\'):
            while i < len(text) and text[i] != '\n':
                i += 1
            out.append(' ')
            continue
        out.append(char)
        i += 1
    return ''.join(out)


def row_cells(body: str) -> int:
    """Число ячеек в строке с учётом ``\\multicolumn{n}``."""
    body = body.strip()
    if not body or body.startswith('\\bottomrule'):
        return 0

    cells = 1 + body.count('&')
    for match in re.finditer(r'\\multicolumn\{(\d+)\}', body):
        cells += int(match.group(1)) - 1
    return cells


def check_tabular(text: str, offset_line: int, path: str) -> list[str]:
    problems: list[str] = []
    pos = 0
    while True:
        match = BEGIN_RE.search(text, pos)
        if not match:
            break
        brace = text.find('{', match.start() + len('\\begin{tabular}'))
        if brace < 0:
            break
        spec, after = split_braced(text, brace)
        columns = spec_to_columns(spec)
        line = offset_line + text.count('\n', 0, match.start())

        end = text.find('\\end{tabular}', after)
        if end < 0:
            problems.append(f'{path}:{line}: tabular без \\end{{tabular}}')
            break
        block = strip_comments(text[after:end])

        for raw in re.split(r'(?<!\\)\\\\', block):
            # Отрезаем ``\toprule``/``\midrule``/``\cmidrule{...}``/``\bottomrule``.
            raw = RULE_RE.sub(' ', raw)
            cells = row_cells(raw)
            if cells and cells != len(columns):
                problems.append(
                    f'{path}:{line}: строка с {cells} ячейками при '
                    f'{len(columns)} колонках в преамбуле «{spec.strip()}»'
                )

        width = sum(
            NARROW_PT if col == 'r' else COLWIDTH_PT for col in columns
        )
        if width > TEXTWIDTH_PT:
            problems.append(
                f'{path}:{line}: таблица из {len(columns)} колонок, '
                f'оценка ширины ~{width:.0f} pt > {TEXTWIDTH_PT:.0f} pt — '
                'уменьшите кегль, \\tabcolsep или заголовки столбцов'
            )
        pos = end + len('\\end{tabular}')
    return problems


def check_captions(text: str, path: str, offset_line: int) -> list[str]:
    problems: list[str] = []
    for match in FOOTNOTE_CAPTION_RE.finditer(text):
        line = offset_line + text.count('\n', 0, match.start())
        problems.append(
            f'{path}:{line}: \\footnote внутри \\caption — ломает сборку '
            'при списке таблиц; вынесите примечание строкой под заголовком'
        )
    return problems


def check_images(text: str, path: str, offset_line: int) -> list[str]:
    problems: list[str] = []
    for match in IMAGE_RE.finditer(text):
        ref = match.group(0)
        if ref.endswith(('*', '.png', '.pdf')) and not (ROOT / ref).exists():
            line = offset_line + text.count('\n', 0, match.start())
            problems.append(f'{path}:{line}: нет файла {ref}')
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='*', help='файлы; по умолчанию все *.tex')
    parser.add_argument(
        '--warn', action='store_true',
        help='показать предупреждения о ширине таблиц (по умолчанию только ошибки)',
    )
    args = parser.parse_args(argv)

    files = args.files or sorted(
        str(p.relative_to(ROOT)) for p in ROOT.glob('*.tex')
    )

    errors: list[str] = []
    warnings: list[str] = []
    for name in files:
        path = ROOT / name
        if not path.exists():
            errors.append(f'{name}: файл не найден')
            continue
        text = path.read_text(encoding='utf-8', errors='replace')
        for problem in check_tabular(text, 0, name) + check_captions(text, name, 0):
            if 'оценка ширины' in problem:
                warnings.append(problem)
            else:
                errors.append(problem)
        errors.extend(check_images(text, name, 0))

    for problem in errors:
        print(f'ОШИБКА: {problem}')
    if args.warn:
        for problem in warnings:
            print(f'предупреждение: {problem}')
    elif warnings:
        print(f'(предупреждений о ширине: {len(warnings)}; подробнее — --warn)')

    if errors:
        print(f'\nнайдено ошибок: {len(errors)}')
        return 1
    print(f'таблицы и подписи: OK ({len(files)} файлов)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
