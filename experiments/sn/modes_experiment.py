#!/usr/bin/env python3
"""Сводный эксперимент по режимам выбора константы a (SN-карта).

Для n = 13, 16, 19: m = 3000 подгрупп, первые IC = 2000 — в управляемом
состоянии (IC), с подгруппы 2001 — сдвиг медианы δ = 1σ.

Правила (границы a): exact, normal, nearest(α = 0.05), normal(approx);
пакет npSPC: far = {0.0027, 0.00135}.

Метрики: a, FAR (теория), FA(IC) — ложные тревоги на IC-участке, delay —
задержка обнаружения сдвига.

Данные передаются в R-скрипт mode_comparison.R (пакет npSPC), см.
05_modes_experiment.txt.

Запуск из корня репозитория:

    RSCRIPT=/tmp/opencode/renv/bin/Rscript \
    R_LIBS=/tmp/opencode/renv/lib/R/library \
        poetry run python experiments/sn/modes_experiment.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from math import ceil
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

sys.path.insert(0, "src")

from nonparametric_charts.charts.sign_chart import SignChart  # noqa: E402

FAR0 = 0.0027
ALPHA = 0.05
NS = [13, 16, 19]
M = 3000
IC = 2000          # число управляемых подгрупп
SHIFT = 1.0        # сдвиг медианы, SD
HERE = Path("experiments/sn")


def make_data(n: int) -> np.ndarray:
    rng = np.random.default_rng(20261018 + n)
    X = rng.standard_normal((M, n))
    X[IC:, :] += SHIFT
    return X


def sn_values(X: np.ndarray, target: float = 0.0) -> np.ndarray:
    return (X > target).sum(axis=1) - (X < target).sum(axis=1)


def metrics(sn: np.ndarray, a: int) -> tuple[int, object, int]:
    """(ложные тревоги на IC, задержка обнаружения, тревог после сдвига)."""
    sig = np.abs(sn) >= a
    false_alarms = int(sig[:IC].sum())
    post = np.nonzero(sig[IC:])[0]
    delay = int(post[0]) + 1 if post.size else None
    return false_alarms, delay, int(sig[IC:].sum())


def run_r() -> None:
    rscript = os.environ.get("RSCRIPT", "Rscript")
    subprocess.run([rscript, str(HERE / "mode_comparison.R")], check=True)


def main() -> None:
    print(f"Режимы: m = {M}, IC = {IC}, δ = {SHIFT:g}σ с подгруппы {IC + 1}")

    for n in NS:
        X = make_data(n)
        pd.DataFrame(X, columns=[f"obs{i + 1}" for i in range(n)]).to_csv(
            HERE / f"data_modes_{n}.csv", index=False)

    run_r()
    npspc = pd.read_csv(HERE / "modes_npspc_limits.csv")

    rows = []
    for n in NS:
        X = make_data(n)
        sn = sn_values(X)
        a_cons, _ = SignChart._calc_a_exact(n, FAR0)
        a_sym, _ = SignChart._calc_a_normal(n, FAR0)
        a_near, _ = SignChart._calc_a_nearest(n, ALPHA)
        a_norm = ceil(norm.ppf(1 - FAR0 / 2) * np.sqrt(n))

        modes = [
            ("exact", a_cons),
            ("normal", a_sym),
            (f"nearest(α={ALPHA})", a_near),
            ("normal(approx)", a_norm),
        ]
        for far in (0.0027, 0.00135):
            sub = npspc[(npspc["n"] == n) & (np.isclose(npspc["far_arg"], far))]
            modes.append((f"npSPC(far={far})", int(sub["a"].iloc[0])))

        print()
        print(f"n = {n}")
        print(f"  {'rule':<18}{'a':>4}{'FAR':>12}{'FA(IC)':>9}{'delay':>8}")
        for name, a in modes:
            far = float(SignChart._p_abs_sn_ge_a(n, a))
            fa, delay, _ = metrics(sn, a)
            d = "-" if delay is None else str(delay)
            print(f"  {name:<18}{a:>4}{far:>12.6f}{fa:>9}{d:>8}")
            rows.append({"n": n, "mode": name, "a": a, "FAR": far,
                         "false_alarms": fa, "delay": delay})

    out = pd.DataFrame(rows)
    out.to_csv(HERE / "modes_summary.csv", index=False)
    print("\nЗаписано: experiments/sn/modes_summary.csv")


if __name__ == "__main__":
    main()
