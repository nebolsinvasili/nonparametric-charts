"""
Общие фикстуры и настройка окружения для тестов ShCC

Проект запускается из корня репозитория (см. AGENTS.md), поэтому:
- корень репозитория добавляется в sys.path для абсолютных импортов src.*
- matplotlib переключается в безголовый backend (Agg) для тестов графиков
"""

import sys
from pathlib import Path

import matplotlib

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

matplotlib.use("Agg")

# Файл коэффициентов Шухарта (репозиторий-относительный путь) —
# BaseControlChart._load_coefficients не ищет файл в src/utils автоматически.
COEFFICIENTS_FILE = ROOT / "src" / "utils" / "coefficients.json"
