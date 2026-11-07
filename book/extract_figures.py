#!/usr/bin/env python3
"""Автоматическая вырезка рисунков из PDF книги в ``book/images/``.

Фигуры в книге — векторные (растровых вставок нет), поэтому «достать» их
можно только рендером страницы с последующей обрезкой. Скрипт делает это
по подписям:

1. ``pdftotext -bbox-layout`` даёт координаты строк на каждой странице.
2. Находится строка ``FIGURE <глава>.<номер>`` — это нижняя граница рисунка
   (подпись всегда под рисунком).
3. Верхняя граница — конец последней «полноширинной» строки основного текста
   выше подписи; если такой строки нет (рисунок в начале страницы) — верх
   полосы набора.
4. Полоса рендерится ``pdftoppm`` с обрезкой по координатам, затем
   подрезаются белые поля (Pillow) и добавляется небольшой отступ.
5. Если подпись помечена ``(Continued)`` (рисунок на две страницы),
   части склеиваются по вертикали — так собирается, например, рис. 3.19.

Запуск (нужен Pillow — он есть в venv проекта)::

    .venv/bin/python book/extract_figures.py --figures 3.8-3.23
    .venv/bin/python book/extract_figures.py --figures 3.8-3.23 --force
    .venv/bin/python book/extract_figures.py --figures 4.1-4.20 --contact /tmp/fig4.png

Повторный запуск без ``--force`` не перезаписывает уже существующие файлы.
Координаты для ручной правки — ``OVERRIDES`` ниже: ``{номер: (top, bottom)}``
в пунктах PDF; ``None`` означает «вычислить автоматически».
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_PDF = ROOT.parent / 'docs/ref/chakraborti_s_graham_ma_nonparametric_statistical_process_co.pdf'
DEFAULT_OUT = ROOT / 'images'

#: Ручные правки границ (в пунктах PDF, начало координат — левый верх страницы).
#: Пример: {'3.14': (None, 405.0)} — низ взять вручную.
OVERRIDES: dict[str, tuple[float | None, float | None]] = {
    '4.30': (370.0, None),  # тело последней строки табл. 4.24
}

PAGE_RE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', re.S)
LINE_RE = re.compile(
    r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>',
    re.S,
)
CAPTION_RE = re.compile(r'^FIGURE\s+(\d+)\.(\d+)([a-z]?)\b(.*)$', re.S)
CONTINUED_RE = re.compile(r'\(Continued\)', re.I)
TABLE_RE = re.compile(r'^Table\s+(\d+)\.(\d+)\b', re.S)

CONTENT_TOP = 66.0      # ниже колонтитула (он заканчивается около y=58)
MARGIN_X = 40.0         # поля страницы, которые заведомо шире полосы набора
BODY_MIN_WIDTH = 240.0  # «полноширинная» строка основного текста
BODY_MAX_HEIGHT = 12.5
BODY_MAX_X0 = 90.0
TOP_GAP = 8.0           # отступ от последней строки текста до рисунка
CAPTION_GAP = 3.0       # отступ от подписи
PAD_PX = 12             # белое поле вокруг вырезанного рисунка, пиксели
STACK_GAP_PX = 24       # зазор между частями рисунка на двух страницах


@dataclass
class Line:
    y0: float
    y1: float
    x0: float
    x1: float
    text: str

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass
class Page:
    number: int
    width: float
    height: float
    lines: list[Line]


@dataclass
class Caption:
    page: Page
    figure: str
    y0: float
    text: str


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kwargs)


def load_pages(pdf: Path, wanted_pages: set[int] | None = None) -> dict[int, Page]:
    """Разбирает bbox-разметку PDF (одним проходом pdftotext)."""
    with tempfile.NamedTemporaryFile('r', suffix='.html', delete=False, encoding='utf-8') as tmp:
        tmp_path = Path(tmp.name)
    try:
        run(['pdftotext', '-bbox-layout', '-q', str(pdf), str(tmp_path)])
        html = tmp_path.read_text(encoding='utf-8', errors='replace')
    finally:
        tmp_path.unlink(missing_ok=True)

    pages: dict[int, Page] = {}
    for number, (width, height, body) in enumerate(PAGE_RE.findall(html), start=1):
        if wanted_pages is not None and number not in wanted_pages:
            continue
        lines = []
        for x0, y0, x1, y1, raw in LINE_RE.findall(body):
            text = ' '.join(re.sub(r'<[^>]+>', '', raw).split())
            if text:
                lines.append(
                    Line(float(y0), float(y1), float(x0), float(x1), text)
                )
        lines.sort(key=lambda line: (line.y0, line.x0))
        pages[number] = Page(number, float(width), float(height), lines)
    return pages


def parse_figures(spec: str) -> list[str]:
    """``3.8-3.23`` или ``3.8,3.10`` → список номеров."""
    result: list[str] = []
    for chunk in spec.split(','):
        chunk = chunk.strip()
        if not chunk:
            continue
        if '-' in chunk:
            start, end = chunk.split('-', 1)
            ch_s, n_s = start.split('.')
            ch_e, n_e = end.split('.')
            if ch_s != ch_e:
                raise SystemExit(f'диапазон в пределах одной главы: {chunk}')
            for n in range(int(n_s), int(n_e) + 1):
                result.append(f'{ch_s}.{n}')
        else:
            result.append(chunk)
    return result


def figure_parts(figure: str) -> tuple[str, str | None]:
    """``'4.22c'`` → ``('4.22', 'c')``; ``'4.13'`` → ``('4.13', None)``."""
    number, _, letter = figure.partition('|')
    return number, (letter or None)


def display_name(figure: str) -> str:
    """Номер для подписи в LaTeX: ``'4.22|a'`` → ``'4.22a'``."""
    number, letter = figure_parts(figure)
    return number + (letter or '')


def captions_for(pages: dict[int, Page], figure: str) -> list[Caption]:
    number, letter = figure_parts(figure)
    found = []
    for page in pages.values():
        for line in page.lines:
            match = CAPTION_RE.match(line.text)
            if not match:
                continue
            if f'{match.group(1)}.{match.group(2)}' != number:
                continue
            # Панель рисунка (4.22a/b/c) — подпись с той же буквой;
            # рисунок без буквы — только подписи без буквы.
            if (match.group(3) or None) != letter and letter is not None:
                continue
            if letter is None and match.group(3):
                continue
            found.append(Caption(page, figure, line.y0, line.text))
    return found


def caption_block_bottom(caption: Caption) -> float:
    """Низ блока подписи: подпись может занимать две-три строки."""
    lines = caption.page.lines
    index = next(
        (
            i
            for i, line in enumerate(lines)
            if abs(line.y0 - caption.y0) < 0.01
            and CAPTION_RE.match(line.text)
        ),
        None,
    )
    if index is None:
        return caption.y0 + 12.0
    bottom = lines[index].y1
    for following in lines[index + 1:]:
        if following.y0 - bottom <= 5.0 and following.height <= 13.0:
            bottom = max(bottom, following.y1)
        else:
            break
    return bottom


def body_top(caption: Caption) -> float:
    """Низ последней строки основного текста выше подписи (или верх набора)."""
    candidates = [
        line
        for line in caption.page.lines
        if line.y1 < caption.y0 - 4
        and line.width >= BODY_MIN_WIDTH
        and line.height <= BODY_MAX_HEIGHT
        and line.x0 <= BODY_MAX_X0
        and not line.text.startswith('FIGURE')
    ]
    top = CONTENT_TOP
    if candidates:
        top = max(line.y1 for line in candidates) + TOP_GAP

    # На странице может быть несколько рисунков (например, 3.9 и 3.10):
    # рисунок не должен начинаться выше конца предыдущей подписи.
    for line in caption.page.lines:
        if line.y0 >= caption.y0 - 0.5:
            continue
        match = CAPTION_RE.match(line.text)
        if not match:
            # Подпись таблицы тоже ограничивает рисунок снизу (рис. 4.30).
            table = TABLE_RE.match(line.text)
            if not table:
                continue
            previous = Caption(
                caption.page,
                f'{table.group(1)}.{table.group(2)}',
                line.y0,
                line.text,
            )
            top = max(top, caption_block_bottom(previous) + TOP_GAP)
            continue
        previous = Caption(
            caption.page,
            f'{match.group(1)}.{match.group(2)}',
            line.y0,
            line.text,
        )
        top = max(top, caption_block_bottom(previous) + TOP_GAP)

    return min(top, caption.y0 - 20.0)


def render_crop(
    pdf: Path, page: Page, top: float, bottom: float, dpi: int, target: Path
) -> Path:
    """Рендерит полосу страницы; pdftoppm сам добавляет расширение ``.png``."""
    scale = dpi / 72.0
    x = int(max(0.0, MARGIN_X) * scale)
    y = int(max(0.0, top) * scale)
    width = int((page.width - 2 * MARGIN_X) * scale)
    height = int(max(1.0, bottom - top) * scale)
    run(
        [
            'pdftoppm', '-f', str(page.number), '-l', str(page.number),
            '-r', str(dpi), '-x', str(x), '-y', str(y),
            '-W', str(width), '-H', str(height),
            '-png', '-singlefile', str(pdf), str(target),
        ]
    )
    return Path(f'{target}.png')


def trim(path: Path) -> 'Image.Image':  # noqa: F821 - импорт ниже, чтобы дать понятную ошибку
    from PIL import Image

    image = Image.open(path).convert('L')
    # Всё, что светлее 245, считаем фоном; тёмные пиксели — содержимое рисунка.
    mask = image.point(lambda value: 0 if value > 245 else 255)
    box = mask.getbbox()
    image = image.convert('RGB')
    if box is None:
        return image
    padding = PAD_PX
    left = max(0, box[0] - padding)
    upper = max(0, box[1] - padding)
    right = min(image.width, box[2] + padding)
    lower = min(image.height, box[3] + padding)
    return image.crop((left, upper, right, lower))


def stack(parts: list['Image.Image']) -> 'Image.Image':  # noqa: F821
    from PIL import Image

    width = max(part.width for part in parts)
    height = sum(part.height for part in parts) + STACK_GAP_PX * (len(parts) - 1)
    canvas = Image.new('RGB', (width, height), 'white')
    y = 0
    for part in parts:
        canvas.paste(part, ((width - part.width) // 2, y))
        y += part.height + STACK_GAP_PX
    return canvas


def extract(
    pdf: Path, out_dir: Path, figures: list[str], dpi: int, force: bool
) -> dict[str, list[Caption]]:
    pages = load_pages(pdf)
    plan: dict[str, list[Caption]] = {}
    for figure in figures:
        found = captions_for(pages, figure)
        if not found:
            print(f'  {figure}: подпись FIGURE {figure} не найдена — пропуск')
            continue
        plan[figure] = found

    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        for figure, parts in plan.items():
            target = out_dir / f'fig-{display_name(figure).replace("|", "")}.png'
            if target.exists() and not force:
                print(f'  {figure}: {target.name} уже есть (--force для перезаписи)')
                continue

            images = []
            boxes = []
            for index, caption in enumerate(parts):
                top = body_top(caption)
                if figure in OVERRIDES and OVERRIDES[figure][0] is not None:
                    top = OVERRIDES[figure][0]
                bottom = caption.y0 - CAPTION_GAP
                override_top, override_bottom = OVERRIDES.get(figure, (None, None))
                if override_top is not None:
                    top = override_top
                if override_bottom is not None:
                    bottom = override_bottom
                raw = tmp / f'{figure}-{index}'
                rendered = render_crop(pdf, caption.page, top, bottom, dpi, raw)
                images.append(trim(rendered))
                boxes.append(
                    f'стр. {caption.page.number} ({top:.0f}–{bottom:.0f} пт)'
                )

            image = images[0] if len(images) == 1 else stack(images)
            image.save(target)
            note = ' + '.join(boxes)
            print(
                f'  {figure}: {target.name} {image.width}x{image.height}, '
                f'{target.stat().st_size // 1024} КБ — {note}'
            )

    return plan


def contact_sheet(paths: list[Path], output: Path) -> None:
    from PIL import Image, ImageDraw

    if not paths:
        return
    columns = 3
    cell_width, cell_height, label_height = 520, 420, 24
    rows = (len(paths) + columns - 1) // columns
    sheet = Image.new('RGB', (columns * cell_width, rows * cell_height), 'white')
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(paths):
        image = Image.open(path).convert('RGB')
        image.thumbnail((cell_width - 20, cell_height - label_height - 20))
        column, row = index % columns, index // columns
        x = column * cell_width + (cell_width - image.width) // 2
        y = row * cell_height + label_height
        sheet.paste(image, (x, y))
        draw.text(
            (column * cell_width + 10, row * cell_height + 4),
            path.stem,
            fill='black',
        )
    sheet.save(output)
    print(f'контактный лист: {output}')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', type=Path, default=DEFAULT_PDF)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--figures', default='3.8-3.23')
    parser.add_argument('--dpi', type=int, default=200)
    parser.add_argument('--force', action='store_true', help='перезаписать существующие')
    parser.add_argument('--contact', type=Path, help='собрать контактный лист (PNG)')
    args = parser.parse_args()

    try:
        import PIL  # noqa: F401
    except ImportError:
        print('нужен Pillow: .venv/bin/python book/extract_figures.py ...')
        return 1

    if not args.pdf.exists():
        print(f'нет PDF: {args.pdf}')
        return 1

    figures = parse_figures(args.figures)  # панели рисунков — через '|'
    print(f'PDF: {args.pdf.name}; рисунки: {args.figures}; dpi: {args.dpi}')
    plan = extract(args.pdf, args.out, figures, args.dpi, args.force)

    if args.contact:
        paths = [
            args.out / f'fig-{display_name(figure)}.png'
            for figure in plan
        ]
        contact_sheet([p for p in paths if p.exists()], args.contact)

    missing = [figure for figure in figures if figure not in plan]
    if missing:
        print(f'не найдены подписи: {", ".join(missing)}')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
