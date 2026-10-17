"""
Общие фикстуры и настройка окружения для тестов nonparametric-charts.

Проект запускается из корня репозитория (см. AGENTS.md), поэтому:
- корень репозитория добавляется в sys.path для абсолютных импортов src.*;
- matplotlib переключается в безголовый backend (Agg) для тестов графиков.

Тесты организованы по примерам из книги Чакраборти и Грэма (2019):
один файл — один пример. Построенные карты сохраняются в ``results/tests``
с указанием номера примера в имени файла (см. фикстуру ``results_dir``).
"""

import sys
from pathlib import Path

import matplotlib
import pytest

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

matplotlib.use("Agg")

# Файл коэффициентов Шухарта (репозиторий-относительный путь). Для
# непараметрических карт коэффициенты не используются, но файл является
# частью базовой инфраструктуры nonparametric-charts (BaseControlChart).
COEFFICIENTS_FILE = ROOT / "src" / "utils" / "coefficients.json"

# Каталог для карт, построенных в тестах.
RESULTS_DIR = ROOT / "results" / "tests"


@pytest.fixture(scope="session")
def results_dir() -> Path:
    """Каталог ``results/tests`` для сохранения карт из тестов."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR


@pytest.fixture(autouse=True)
def _close_figures():
    """Закрывать все фигуры matplotlib после каждого теста."""
    yield
    import matplotlib.pyplot as plt

    plt.close("all")
