#!/usr/bin/env python3
"""Расчётное сопровождение отчёта о верификации SN-карты.

Считает:
  * границы a по правилам exact, nearest, npSPC(far=0.0027/0.00135);
  * точные FAR/ARL/MRL (распределение SN = 2T − n, T ~ Bin(n, 1/2));
  * вероятность сигнала при сдвиге δ = 0, 0.5, 1, 1.5, 2 σ;
  * сверку FAR: теория vs Монте-Карло (IC и δ = 1σ);
  * время расчёта.

Запуск из корня репозитория:
    poetry run python experiments/sn/sn_analysis.py
"""

from __future__ import annotations

import sys
import time
from math import comb, ceil, floor, log

import numpy as np
from scipy.stats import binom, norm

sys.path.insert(0, "src")

from nonparametric_charts.charts.sign_chart import SignChart  # noqa: E402

FAR0 = 0.0027
ALPHA = 0.05
DELTAS = [0.0, 0.5, 1.0, 1.5, 2.0]


# --------------------------------------------------------------------------- #
#  Правило пакета npSPC
# --------------------------------------------------------------------------- #
def npspc_limits(n: int, far: float = 0.0027):
    """Реплика R/shewhart_sn.R: q — наименьшее с P(Bin(n,1/2) >= q) < far."""
    q = 1
    for k in range(1, n + 1):
        if binom.sf(k - 1, n, 0.5) < far:  # sf(k-1) = P(X >= k)
            q = k
            break
    else:
        q = n
    ucl = 2 * q - n
    far_used = 2 * binom.sf(q - 1, n, 0.5)
    return ucl, far_used


def book_limits(n: int, far0: float = FAR0):
    return SignChart._calc_a_exact(n, far0)


# --------------------------------------------------------------------------- #
#  Точная вероятность сигнала при сдвиге
# --------------------------------------------------------------------------- #
def p_signal(n: int, a: int, delta: float) -> float:
    """P(|SN| >= a) при X ~ N(delta, 1), целевое значение 0.

    T = число X > 0 ~ Bin(n, p), p = Phi(delta), SN = 2T - n.
    """
    p = float(norm.cdf(delta))
    k_hi = ceil((n + a) / 2)
    k_lo = floor((n - a) / 2)
    hi = binom.sf(k_hi - 1, n, p)
    lo = binom.cdf(k_lo, n, p)
    return float(min(hi + lo, 1.0))


def arl(far: float) -> float:
    return float("inf") if far <= 0 else 1.0 / far


def mrl(far: float) -> float:
    return float("nan") if not (0 < far < 1) else ceil(log(0.5) / log(1 - far))


# --------------------------------------------------------------------------- #
def main() -> None:
    print("A. Границы a и FAR по правилам, n = 1..20")
    print(f"  {'n':>3} | {'exact':>5} {'FAR':>10} | {'nearest':>7} | "
          f"{'npSPC(.0027)':>12} {'FAR':>10} | {'npSPC(.00135)':>13}")
    rows_a = []
    for n in range(1, 21):
        a_ex, f_ex = book_limits(n)
        a_nr, _ = SignChart._calc_a_nearest(n, ALPHA)
        a_n2, f_n2 = npspc_limits(n, 0.0027)
        a_n1, _ = npspc_limits(n, 0.00135)
        rows_a.append((n, a_ex, a_nr, a_n2, a_n1))
        print(f"  {n:>3} | {a_ex:>5} {f_ex:>10.6f} | {a_nr:>7} | "
              f"{a_n2:>12} {f_n2:>10.6f} | {a_n1:>13}")
    print("  exact != npSPC(.0027) при n =",
          [r[0] for r in rows_a if r[1] != r[3]] or "—")
    print("  exact == npSPC(.00135) при всех n:",
          all(r[1] == r[4] for r in rows_a))

    print()
    print("B. Сигнал и ARL при сдвиге δ, n = 16")
    n = 16
    a_ex, _ = book_limits(n)
    a_np, _ = npspc_limits(n, 0.0027)
    print(f"  a: exact = {a_ex}, npSPC(.0027) = {a_np}")
    print(f"  {'δ(σ)':>5} {'Φ(δ)':>7} | {'exact':>19} | {'npSPC(.0027)':>19}")
    print(f"  {'':>5} {'':>7} | {'P(signal)':>10} {'ARL':>8} | "
          f"{'P(signal)':>10} {'ARL':>8}")
    for d in DELTAS:
        pb = p_signal(n, a_ex, d)
        pn = p_signal(n, a_np, d)
        print(f"  {d:>5.1f} {norm.cdf(d):>7.4f} | {pb:>10.6f} {arl(pb):>8.2f} | "
              f"{pn:>10.6f} {arl(pn):>8.2f}")

    print()
    print("C. FAR: теория vs Монте-Карло, n = 16, m = 500000")
    rng = np.random.default_rng(20261018)
    m = 500_000
    X = rng.standard_normal((m, n))
    print(f"  {'условие':<7} {'правило':<14} {'a':>3} {'FAR_mc':>10} "
          f"{'FAR_theory':>11} {'ARL_mc':>9}")
    for cond, rule, a, d in [("IC", "exact", a_ex, 0.0),
                             ("δ=1σ", "exact", a_ex, 1.0),
                             ("δ=1σ", "npSPC(.0027)", a_np, 1.0)]:
        sn = 2 * ((X + d) > 0).sum(axis=1) - n
        far_mc = float((np.abs(sn) >= a).mean())
        far_th = p_signal(n, a, d)
        print(f"  {cond:<7} {rule:<14} {a:>3} {far_mc:>10.6f} "
              f"{far_th:>11.6f} {arl(far_mc):>9.2f}")

    print()
    print("D. Время, n = 16")
    t0 = time.perf_counter()
    for _ in range(1000):
        book_limits(16)
    t1 = time.perf_counter()
    print(f"  a, exact:        1000 вызовов — {t1 - t0:.4f} с")
    t0 = time.perf_counter()
    for _ in range(1000):
        npspc_limits(16)
    t1 = time.perf_counter()
    print(f"  a, npSPC(.0027): 1000 вызовов — {t1 - t0:.4f} с")

    X2 = rng.standard_normal((1_000_000, 16))
    t0 = time.perf_counter()
    sn2 = 2 * (X2 > 0).sum(axis=1) - 16
    sig2 = np.abs(sn2) >= a_ex
    t1 = time.perf_counter()
    print(f"  SN, 1e6 подгрупп (IC): {t1 - t0:.4f} с, сигналов {int(sig2.sum())}")


if __name__ == "__main__":
    main()
