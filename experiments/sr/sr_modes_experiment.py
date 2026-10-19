#!/usr/bin/env python3
"""Сводный эксперимент по режимам выбора константы a (SR-карта).

Для n = 14, 16, 19: m = 3000 подгрупп, первые IC = 2000 — в управляемом
состоянии (IC), с подгруппы 2001 — сдвиг медианы δ = 1σ.

Правила (границы a): exact, normal, nearest(α = 0.05), normal(approx);
пакет npSPC: exact = {TRUE, FALSE} × far = {0.0027, 0.00135}.

Метрики: a, FAR (теория), FA(IC) — ложные тревоги на IC-участке, delay —
задержка обнаружения сдвига.

Данные передаются в R-скрипт sr_mode_comparison.R (пакет npSPC), см.
05_modes_experiment.txt.

Запуск из корня репозитория:

    RSCRIPT=/tmp/opencode/renv/bin/Rscript \
    R_LIBS=/tmp/opencode/renv/lib/R/library \
        poetry run python experiments/sr/sr_modes_experiment.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from math import ceil, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "src")

from nonparametric_charts.charts.signed_rank_chart import SignedRankChart  # noqa: E402

FAR0 = 0.0027
ALPHA = 0.05
NS = [14, 16, 19]
M = 3000
IC = 2000          # число управляемых подгрупп
SHIFT = 1.0        # сдвиг медианы, SD
HERE = Path("experiments/sr")

_SR = SignedRankChart.__new__(SignedRankChart)
_SR._sr_dist_cache = {}


def make_data(n: int) -> np.ndarray:
    rng = np.random.default_rng(20261018 + n)
    X = rng.standard_normal((M, n))
    X[IC:, :] += SHIFT
    return X


def sr_values(X: np.ndarray, target: float = 0.0) -> np.ndarray:
    ranks = np.argsort(np.argsort(np.abs(X - target), axis=1), axis=1) + 1
    signs = np.where(X > target, 1, -1)
    return (signs * ranks).sum(axis=1)


def metrics(sr: np.ndarray, thr: float) -> tuple[int, object, int]:
    """(ложные тревоги на IC, задержка обнаружения, тревог после сдвига)."""
    sig = np.abs(sr) >= thr
    false_alarms = int(sig[:IC].sum())
    post = np.nonzero(sig[IC:])[0]
    delay = int(post[0]) + 1 if post.size else None
    return false_alarms, delay, int(sig[IC:].sum())


def far_theory(n: int, thr: float) -> float:
    return float(SignedRankChart._p_abs_sr_ge_a(_SR, n, ceil(thr)))


def run_r() -> None:
    rscript = os.environ.get("RSCRIPT", "Rscript")
    subprocess.run([rscript, str(HERE / "sr_mode_comparison.R")], check=True)


def main() -> None:
    print(f"Режимы SR: m = {M}, IC = {IC}, δ = {SHIFT:g}σ с подгруппы {IC + 1}")

    for n in NS:
        X = make_data(n)
        pd.DataFrame(X, columns=[f"obs{i + 1}" for i in range(n)]).to_csv(
            HERE / f"data_sr_modes_{n}.csv", index=False)

    run_r()
    npspc = pd.read_csv(HERE / "sr_modes_npspc_limits.csv")

    rows = []
    for n in NS:
        X = make_data(n)
        sr = sr_values(X)
        S = n * (n + 1) // 2
        a_cons, _ = SignedRankChart._calc_a_exact(n, FAR0, _SR._p_sr_ge_a)
        a_sym, _ = SignedRankChart._calc_a_normal(n, FAR0, _SR._p_sr_ge_a)
        a_near, _ = SignedRankChart._calc_a_nearest(n, ALPHA, _SR._p_abs_sr_ge_a)
        sd = sqrt(n * (n + 1) * (2 * n + 1) / 6.0)
        from scipy.stats import norm
        u_asym = float(norm.ppf(1 - FAR0 / 2) * sd)

        modes = [
            ("exact", float(a_cons)),
            ("normal", float(a_sym)),
            (f"nearest(α={ALPHA})", float(a_near)),
            ("normal(approx)", u_asym),
        ]
        for exact in (True, False):
            for far in (0.0027, 0.00135):
                sub = npspc[(npspc["n"] == n) & (npspc["far_arg"] == far)
                            & (npspc["exact"] == exact)]
                modes.append((f"npSPC(exact={exact}, far={far})",
                              float(sub["ucl"].iloc[0])))

        print()
        print(f"n = {n}  (S = {S})")
        print(f"  {'rule':<26}{'a':>10}{'FAR':>12}{'FA(IC)':>9}{'delay':>8}")
        for name, thr in modes:
            far = far_theory(n, thr)
            fa, delay, _ = metrics(sr, thr)
            d = "-" if delay is None else str(delay)
            print(f"  {name:<26}{thr:>10.3f}{far:>12.6f}{fa:>9}{d:>8}")
            rows.append({"n": n, "mode": name, "threshold": thr, "FAR": far,
                         "false_alarms": fa, "delay": delay})

    out = pd.DataFrame(rows)
    out.to_csv(HERE / "sr_modes_summary.csv", index=False)
    print("\nЗаписано: experiments/sr/sr_modes_summary.csv")


if __name__ == "__main__":
    main()
