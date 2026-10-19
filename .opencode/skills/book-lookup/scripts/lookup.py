#!/usr/bin/env python3
"""
Поиск по книге Чакраборти (Nonparametric Statistical Process Control, 2019).

Пересчитывает нумерацию страниц: печатная страница = PDF-страница - OFFSET.
В этом скане OFFSET = 22 (проверено: печ. 1 -> PDF 23).

Использование
-------------
    python lookup.py search "Shewhart Sign"          # поиск по regex
    python lookup.py search "signed-rank" --ctx 2
    python lookup.py page 189                        # текст печатной стр. 189
    python lookup.py page 189 --span 3               # 3 страницы от 189
    python lookup.py toc                             # оглавление (PDF 9-20)

Без внешних зависимостей: использует системный pdftotext.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

# Печатная страница = PDF-страница - OFFSET (проверено для этого скана).
OFFSET = 22

ROOT = pathlib.Path(__file__).resolve().parents[4]
DEFAULT_PDF = ROOT / "docs" / "ref" / "chakraborti_s_graham_ma_nonparametric_statistical_process_co.pdf"


def extract_pages(pdf: pathlib.Path):
    """Вернуть список страниц (текст) в порядке PDF. Индекс 0 = PDF стр. 1."""
    try:
        proc = subprocess.run(
            ["pdftotext", "-layout", str(pdf), "-"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        sys.exit("pdftotext не найден. Установите poppler-utils.")
    except subprocess.CalledProcessError as exc:
        sys.exit(f"pdftotext завершился с ошибкой: {exc}")
    return proc.stdout.split("\f")


def cmd_search(pdf, pattern, ctx):
    rx = re.compile(pattern, re.IGNORECASE)
    pages = extract_pages(pdf)
    total = 0
    for pdf_no, page in enumerate(pages, start=1):
        lines = page.splitlines()
        hits = [i for i, line in enumerate(lines) if rx.search(line)]
        if not hits:
            continue
        printed = pdf_no - OFFSET
        print(f"=== PDF p.{pdf_no} | печатная p.{printed} ===")
        shown = set()
        for i in hits:
            lo, hi = max(0, i - ctx), min(len(lines), i + ctx + 1)
            for k in range(lo, hi):
                if k not in shown:
                    print(lines[k].rstrip())
                    shown.add(k)
            print("  ...")
        total += len(hits)
    if total == 0:
        print(f"Совпадений не найдено: {pattern!r}")
    else:
        print(f"\nВсего совпадений: {total}")


def cmd_page(pdf, printed, span):
    pages = extract_pages(pdf)
    for p in range(printed, printed + span):
        pdf_no = p + OFFSET
        if not (1 <= pdf_no <= len(pages)):
            print(f"[печатная p.{p} -> PDF p.{pdf_no} вне диапазона]")
            continue
        print(f"\n========== печатная p.{p} (PDF p.{pdf_no}) ==========\n")
        print(pages[pdf_no - 1].rstrip())


def cmd_toc(pdf):
    pages = extract_pages(pdf)
    for p in range(9, min(21, len(pages) + 1)):
        print(pages[p - 1])


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=pathlib.Path, default=DEFAULT_PDF)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search", help="поиск по regex")
    p_search.add_argument("pattern")
    p_search.add_argument("--ctx", type=int, default=1)

    p_page = sub.add_parser("page", help="текст печатной страницы")
    p_page.add_argument("printed", type=int)
    p_page.add_argument("--span", type=int, default=1)

    sub.add_parser("toc", help="оглавление")

    args = parser.parse_args(argv)
    if not args.pdf.exists():
        sys.exit(f"PDF не найден: {args.pdf}")

    if args.cmd == "search":
        cmd_search(args.pdf, args.pattern, args.ctx)
    elif args.cmd == "page":
        cmd_page(args.pdf, args.printed, args.span)
    elif args.cmd == "toc":
        cmd_toc(args.pdf)


if __name__ == "__main__":
    main(sys.argv[1:])
