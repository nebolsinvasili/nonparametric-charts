"""Общие фикстуры и настройка окружения для тестов кода nonparametric-charts.

Проект запускается из корня репозитория (см. AGENTS.md), поэтому:

- каталог ``src`` добавляется в ``sys.path``, чтобы пакет ``nonparametric_charts``
  импортировался и без установки (pip/poetry install делают то же самое);
- matplotlib переключается в безголовый backend (Agg) для тестов графиков.

Здесь только тесты *кода* библиотеки. Проверка примеров из книги (с консольным
выводом и графиками) вынесена в ``examples/``.
"""

import sys
from pathlib import Path

import matplotlib
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

matplotlib.use("Agg")


@pytest.fixture(autouse=True)
def _close_figures():
    """Закрывать все фигуры matplotlib после каждого теста."""
    yield
    import matplotlib.pyplot as plt

    plt.close("all")
