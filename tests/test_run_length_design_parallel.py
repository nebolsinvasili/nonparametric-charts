"""Тесты параллельного подбора ``(k, h)`` (``n_jobs``).

Проверяется, что распараллеливание по независимым кандидатам ``k`` не
меняет результат: совпадают ``k``, ``h``, ``ARL_IC``, ``ARL_OOC`` и порядок
строк таблицы. Числа — из ``tests/test_run_length_design.py``:
``SN n=10, δ=1`` и ``SN n=14, δ=1.5`` (``k=6, h=6, ARL=409``).
"""

from __future__ import annotations

import pytest

from nonparametric_charts.utils.run_length_design import (
    _resolve_n_jobs,
    design_k_from_shift,
    design_kh,
)


def test_n_jobs_validation() -> None:
    """``0`` и значения меньше ``-1`` запрещены."""
    with pytest.raises(ValueError, match='n_jobs'):
        design_kh(10, 500.0, 1.0, n_jobs=0)
    with pytest.raises(ValueError, match='n_jobs'):
        design_kh(10, 500.0, 1.0, n_jobs=-2)


def test_resolve_n_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    """``-1`` превращается в число ядер, остальные значения не меняются."""
    monkeypatch.setattr(
        'nonparametric_charts.utils.run_length_design.os.cpu_count',
        lambda: 3,
    )
    assert _resolve_n_jobs(-1) == 3
    assert _resolve_n_jobs(1) == 1
    assert _resolve_n_jobs(4) == 4


def test_design_kh_parallel_matches_sequential_sn() -> None:
    """``SN n=10``: пул из двух процессов даёт те же числа."""
    sequential = design_kh(
        10, 500.0, 1.0, statistic='SN', k_step=1.0, n_jobs=1
    )
    parallel = design_kh(
        10, 500.0, 1.0, statistic='SN', k_step=1.0, n_jobs=2
    )

    assert (parallel.k, parallel.h) == (sequential.k, sequential.h)
    assert parallel.arl_ic == pytest.approx(sequential.arl_ic)
    assert parallel.arl_ooc == pytest.approx(sequential.arl_ooc)
    assert parallel.table['k'].tolist() == sequential.table['k'].tolist()
    assert (
        parallel.table['arl_ic'].tolist()
        == sequential.table['arl_ic'].tolist()
    )


def test_design_kh_parallel_matches_sequential_sr() -> None:
    """``SR n=4``: распределение считается в каждом процессе независимо."""
    sequential = design_kh(
        4, 500.0, 1.0, statistic='SR', k_step=1.0, n_jobs=1
    )
    parallel = design_kh(
        4, 500.0, 1.0, statistic='SR', k_step=1.0, n_jobs=2
    )

    assert (parallel.k, parallel.h) == (sequential.k, sequential.h)
    assert parallel.arl_ic == pytest.approx(sequential.arl_ic)
    assert parallel.table['h'].tolist() == sequential.table['h'].tolist()


def test_design_k_from_shift_parallel_matches_sequential() -> None:
    """``SN n=14, δ=1.5``: пул не меняет выбранный узел ``k=6, h=6``."""
    sequential = design_k_from_shift(
        14, 500.0, 1.5, statistic='SN', n_jobs=1
    )
    parallel = design_k_from_shift(
        14, 500.0, 1.5, statistic='SN', n_jobs=2
    )

    assert (parallel.k, parallel.h) == (6.0, 6.0)
    assert (parallel.k, parallel.h) == (sequential.k, sequential.h)
    assert parallel.arl == pytest.approx(sequential.arl)
    assert parallel.candidates == sequential.candidates
    assert parallel.k_star == pytest.approx(sequential.k_star)


def test_design_kh_n_jobs_minus_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """``n_jobs=-1`` использует ``os.cpu_count()`` и даёт тот же результат."""
    monkeypatch.setattr(
        'nonparametric_charts.utils.run_length_design.os.cpu_count',
        lambda: 2,
    )
    sequential = design_kh(10, 500.0, 1.0, k_step=1.0, n_jobs=1)
    parallel = design_kh(10, 500.0, 1.0, k_step=1.0, n_jobs=-1)

    assert (parallel.k, parallel.h) == (sequential.k, sequential.h)
    assert parallel.arl_ic == pytest.approx(sequential.arl_ic)
