"""Тесты консольной команды ``npc`` (алиасы запуска)."""

from __future__ import annotations

from pathlib import Path

from nonparametric_charts.cli import (
    build_parser,
    experiment_scripts,
    _repo_root,
    _translate_test_args,
)


def test_experiment_parser_accepts_cusum() -> None:
    """``npc experiment cusum`` разбирается парсером."""
    parser = build_parser()
    args = parser.parse_args(['experiment', 'cusum'])
    assert args.kind == 'cusum'
    assert args.list is False
    assert args.full is False


def test_experiment_parser_accepts_full() -> None:
    """``--full`` включает полный режим экспериментов."""
    parser = build_parser()
    args = parser.parse_args(['experiment', 'cusum', '--full'])
    assert args.kind == 'cusum'
    assert args.full is True


def test_experiment_parser_accepts_all_kinds() -> None:
    parser = build_parser()
    for kind in ('sn', 'sr', 'cusum', 'all'):
        args = parser.parse_args(['experiment', kind])
        assert args.kind == kind


def test_experiment_scripts_sn_sr_are_analysis_files() -> None:
    root = _repo_root()
    assert experiment_scripts(root, 'sn') == [
        root / 'experiments' / 'sn' / 'sn_analysis.py'
    ]
    assert experiment_scripts(root, 'sr') == [
        root / 'experiments' / 'sr' / 'sr_analysis.py'
    ]


def test_experiment_scripts_cusum_are_numbered() -> None:
    """Для CUSUM запускаются все пронумерованные скрипты по порядку."""
    root = _repo_root()
    scripts = experiment_scripts(root, 'cusum')
    assert scripts, 'скрипты experiments/cusum не найдены'
    names = [path.name for path in scripts]
    assert names == sorted(names)
    assert all(name[:2].isdigit() for name in names)
    assert (root / 'experiments' / 'cusum' / '01_oc_curves.py') in scripts
    for name in ('07_grid_resolution.py', '08_search_time.py',
                 '09_parallel.py'):
        assert (root / 'experiments' / 'cusum' / name) in scripts


def test_experiment_scripts_unknown_kind() -> None:
    import pytest

    with pytest.raises(ValueError):
        experiment_scripts(Path('.'), 'unknown')


def test_test_args_pass_through() -> None:
    """Без профильных флагов аргументы передаются pytest как есть."""
    assert _translate_test_args(['-q', 'tests/test_cli.py']) == [
        '-q', 'tests/test_cli.py'
    ]


def test_test_args_fast_excludes_slow() -> None:
    """``npc test --fast`` пропускает маркер ``slow``."""
    assert _translate_test_args(['-q', '--fast']) == ['-q', '-m', 'not slow']


def test_test_args_slow_runs_only_slow() -> None:
    """``npc test --slow`` запускает только помеченные тесты."""
    assert _translate_test_args(['--slow']) == ['-m', 'slow']


def test_test_args_rejects_fast_and_slow_together() -> None:
    import pytest

    with pytest.raises(SystemExit, match='одновременно'):
        _translate_test_args(['--fast', '--slow'])
