"""Консольная команда ``npc`` — алиасы запуска проекта nonparametric-charts.

Устанавливается как entry point (``[project.scripts]`` в ``pyproject.toml``),
поэтому доступна и после ``poetry install``, и после ``pip install .``:

    npc test                 # тесты кода (pytest по tests/)
    npc test -q              # с аргументами pytest (передаются как есть)
    npc test --fast          # только быстрые тесты (без @pytest.mark.slow)
    npc test --slow          # только помеченные @pytest.mark.slow
    npc examples             # проверить все примеры книги (examples/)
    npc examples 4.1 4.4     # только указанные примеры
    npc experiment           # запустить анализы SN, SR и CUSUM (experiments/)
    npc experiment sn        # только SN
    npc experiment cusum     # все пронумерованные скрипты experiments/cusum/
    npc experiment --list    # список скриптов экспериментов

Команда ищет корень репозитория рядом с исходниками (src-layout) или вверх
от текущего каталога, поэтому запускать её можно из любого места внутри
репозитория.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def _repo_root() -> Path:
    """Корень репозитория (там, где лежит ``examples/run_all.py``)."""
    # 1. Рядом с исходниками: <root>/src/nonparametric_charts/cli.py → <root>.
    for parent in Path(__file__).resolve().parents:
        if (parent / "examples" / "run_all.py").is_file():
            return parent

    # 2. Вверх от текущего каталога (если пакет установлен из wheel).
    cwd = Path.cwd().resolve()
    for parent in (cwd, *cwd.parents):
        if (parent / "examples" / "run_all.py").is_file():
            return parent

    raise SystemExit(
        "Не найден корень репозитория nonparametric-charts "
        "(ожидался каталог examples/run_all.py).\n"
        "Запустите команду из корня репозитория."
    )


def _run(cmd: List[str], cwd: Path) -> int:
    """Запустить подпроцесс и вернуть его код возврата."""
    return subprocess.call(cmd, cwd=str(cwd))


def _translate_test_args(pytest_args: List[str]) -> List[str]:
    """Перевести флаги профиля ``--fast``/``--slow`` в аргументы pytest.

    ``--fast`` пропускает тесты с маркером ``slow`` (производительность и
    прочие долгие проверки), ``--slow`` запускает только их. Остальные
    аргументы передаются pytest как есть.
    """
    fast = "--fast" in pytest_args
    slow = "--slow" in pytest_args
    if fast and slow:
        raise SystemExit("Нельзя одновременно --fast и --slow")

    cleaned = [arg for arg in pytest_args if arg not in ("--fast", "--slow")]
    if fast:
        cleaned += ["-m", "not slow"]
    elif slow:
        cleaned += ["-m", "slow"]
    return cleaned


def cmd_test(pytest_args: List[str]) -> int:
    """Запустить pytest, передав ему аргументы как есть."""
    root = _repo_root()
    args = _translate_test_args(pytest_args)
    return _run([sys.executable, "-m", "pytest", *args], root)


def cmd_examples(args: argparse.Namespace) -> int:
    root = _repo_root()
    examples_dir = root / "examples"

    if not args.numbers:
        return _run([sys.executable, str(examples_dir / "run_all.py")], root)

    rc = 0
    for number in args.numbers:
        pattern = f"example_{number.replace('.', '_')}_*.py"
        matches = sorted(examples_dir.glob(pattern))
        if not matches:
            print(f"Пример {number} не найден ({pattern})", file=sys.stderr)
            rc = 1
            continue
        rc |= _run([sys.executable, str(matches[0])], root)
    return rc


_EXPERIMENT_KINDS = ("sn", "sr", "cusum")


def experiment_scripts(root: Path, kind: str) -> List[Path]:
    """Скрипты эксперимента ``kind`` (в порядке запуска).

    Для ``sn``/``sr`` — исторический ``<kind>_analysis.py``. Для ``cusum`` —
    все пронумерованные ``NN_*.py``: каждый такой файл самодостаточен.
    """
    experiments_dir = root / "experiments"
    if kind in {"sn", "sr"}:
        return [experiments_dir / kind / f"{kind}_analysis.py"]
    if kind == "cusum":
        return sorted((experiments_dir / "cusum").glob("[0-9][0-9]_*.py"))
    raise ValueError(f"Неизвестный вид эксперимента: {kind!r}")


def cmd_experiment(args: argparse.Namespace) -> int:
    root = _repo_root()
    experiments_dir = root / "experiments"

    if args.list:
        for path in sorted(experiments_dir.rglob("*.py")):
            print(path.relative_to(root))
        return 0

    kinds = list(_EXPERIMENT_KINDS) if args.kind == "all" else [args.kind]
    rc = 0
    for kind in kinds:
        scripts = experiment_scripts(root, kind)
        if not scripts:
            print(f"Скрипты эксперимента {kind!r} не найдены", file=sys.stderr)
            rc = 1
            continue
        for script in scripts:
            print(f">>> {script.relative_to(root)}", flush=True)
            rc |= _run([sys.executable, str(script)], root)
    return rc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="npc",
        description="Алиасы запуска nonparametric-charts: "
                    "тесты, примеры книги, эксперименты.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_test = sub.add_parser(
        "test",
        help="запустить тесты кода (pytest по tests/); "
             "--fast — без @pytest.mark.slow, --slow — только они",
    )
    p_test.set_defaults(func=lambda args: cmd_test([]))

    p_examples = sub.add_parser(
        "examples", help="проверить примеры книги (examples/)"
    )
    p_examples.add_argument(
        "numbers", nargs="*",
        help="номера примеров, напр. 4.1 4.4 (по умолчанию все)",
    )
    p_examples.set_defaults(func=cmd_examples)

    p_exp = sub.add_parser(
        "experiment", help="запустить эксперименты (experiments/)"
    )
    p_exp.add_argument(
        "kind", nargs="?", default="all",
        choices=["sn", "sr", "cusum", "all"],
        help="какой анализ запустить (по умолчанию all)",
    )
    p_exp.add_argument(
        "--list", action="store_true",
        help="показать доступные скрипты экспериментов",
    )
    p_exp.set_defaults(func=cmd_experiment)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # `npc test …` — всё после «test» передаётся pytest как есть
    # (в т.ч. -q и др.), поэтому эту команду разбираем вручную,
    # минуя argparse.
    if argv and argv[0] == "test":
        return cmd_test(argv[1:])

    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
