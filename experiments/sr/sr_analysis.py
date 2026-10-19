#!/usr/bin/env python3
"""Расчётное сопровождение отчёта о верификации SR-карты (знаково-ранговой).

Считает:
  * точное распределение SR (ДП-свёртка, эквивалент перебора 2^n);
  * границы a по правилам exact, normal, npSPC-exact/asym(far=0.0027);
  * точные FAR/ARL/MRL;
  * вероятность сигнала при сдвиге δ = 0, 0.5, 1, 1.5, 2 σ: свёртка
    ранговых вероятностей знака и Монте-Карло;
  * сверку FAR: теория vs Монте-Карло (IC);
  * время расчёта.

Запуск из корня репозитория:
    poetry run python experiments/sr/sr_analysis.py
"""

from __future__ import annotations

import sys
import time
from math import comb, ceil, floor, log, sqrt

import numpy as np
from scipy.integrate import quad
from scipy.stats import norm

sys.path.insert(0, "src")

from nonparametric_charts.charts.signed_rank_chart import SignedRankChart  # noqa: E402

FAR0 = 0.0027
ALPHA = 0.05
DELTAS = [0.0, 0.5, 1.0, 1.5, 2.0]

# Экземпляр без конструктора — только для доступа к точному распределению SR.
_SR = SignedRankChart.__new__(SignedRankChart)
_SR._sr_dist_cache = {}


# --------------------------------------------------------------------------- #
#  Точное распределение SR через ДП-свёртку (O(n·S), эквивалент 2^n)
# --------------------------------------------------------------------------- #
def sr_dist(n: int) -> dict[int, float]:
    dp: dict[int, int] = {0: 1}
    for j in range(1, n + 1):
        nxt: dict[int, int] = {}
        for v, c in dp.items():
            nxt[v + j] = nxt.get(v + j, 0) + c
            nxt[v - j] = nxt.get(v - j, 0) + c
        dp = nxt
    total = float(1 << n)
    return {v: c / total for v, c in dp.items()}


def p_sr_ge_a(n: int, a: int, dist: dict[int, float] | None = None) -> float:
    d = dist if dist is not None else sr_dist(n)
    return float(sum(p for v, p in d.items() if v >= a))


def far_abs(n: int, a: int, dist: dict[int, float] | None = None) -> float:
    return float(min(2.0 * p_sr_ge_a(n, a, dist), 1.0))


# --------------------------------------------------------------------------- #
#  Правила границ пакета npSPC (R/shewhart_sr.R)
# --------------------------------------------------------------------------- #
def npspc_exact(n: int, far: float = 0.0027):
    """Exact_distribution(n, far/2): maxim = квантиль уровня 1−far/2, ≤ S."""
    alpha = far / 2.0
    d = sr_dist(n)
    S = n * (n + 1) // 2
    cdf = 0.0
    u = S
    for v in sorted(d):
        cdf += d[v]
        if cdf >= 1.0 - alpha:
            u = int(min(v, S))
            break
    return u, far_abs(n, u, d)


def npspc_asym(n: int, far: float = 0.0027) -> float:
    """Limits_asymptotical(n, far/2): UCL = z_{1−far/2}·SD(SR) (дробное)."""
    alpha = far / 2.0
    sd = sqrt(n * (n + 1) * (2 * n + 1) / 6.0)
    return float(norm.ppf(1.0 - alpha) * sd)


def book_limits(n: int, far0: float = FAR0):
    return SignedRankChart._calc_a_exact(n, far0, _SR._p_sr_ge_a)


# --------------------------------------------------------------------------- #
#  Вероятность сигнала при сдвиге
# --------------------------------------------------------------------------- #
def _rank_sign_probs(n: int, delta: float) -> list[float]:
    """q_j = P(знак j-й по |·| порядковой статистики положителен).

    Для X ~ N(delta, 1): плотность |X| равна f(a) = φ(a−δ)+φ(a+δ),
    функция распределения F(a) = Φ(a−δ)+Φ(a+δ)−1, условная вероятность
    знака «+» при |X| = a есть g(a) = φ(a−δ)/(φ(a−δ)+φ(a+δ)). Тогда
    q_j = ∫_0^∞ g(a) f_(j)(a) da, где f_(j) — плотность j-й порядковой
    статистики модулей.
    """
    def f_a(a: float) -> float:
        return float(norm.pdf(a - delta) + norm.pdf(a + delta))

    def F_a(a: float) -> float:
        return float(norm.cdf(a - delta) + norm.cdf(a + delta) - 1.0)

    def g(a: float) -> float:
        denom = norm.pdf(a - delta) + norm.pdf(a + delta)
        return float(norm.pdf(a - delta) / denom) if denom > 0 else 0.5

    qs = []
    for j in range(1, n + 1):
        coef = n * comb(n - 1, j - 1)

        def integrand(a: float) -> float:
            Fa = F_a(a)
            return (g(a) * coef * (Fa ** (j - 1))
                    * ((1.0 - Fa) ** (n - j)) * f_a(a))

        val, _ = quad(integrand, 0.0, np.inf, limit=200)
        qs.append(float(min(max(val, 0.0), 1.0)))
    return qs


def p_signal_conv(n: int, a: int, delta: float) -> float:
    """Свёртка: SR = Σ s_j·j, s_j = +1 с вероятностью q_j (независимо).

    Это приближение (в действительности знаки разных рангов зависимы через
    общие порядковые статистики), но воспроизводит основной эффект сдвига.
    """
    qs = _rank_sign_probs(n, delta)
    dp: dict[int, float] = {0: 1.0}
    for j, q in zip(range(1, n + 1), qs):
        nxt: dict[int, float] = {}
        for v, p in dp.items():
            nxt[v + j] = nxt.get(v + j, 0.0) + p * q
            nxt[v - j] = nxt.get(v - j, 0.0) + p * (1.0 - q)
        dp = nxt
    return float(min(sum(p for v, p in dp.items() if abs(v) >= a), 1.0))


def p_signal_mc(sample: np.ndarray, a: int) -> float:
    return float(np.mean(np.abs(sample) >= a))


def sr_statistics(X: np.ndarray) -> np.ndarray:
    """SR = Σ sign(X_ij)·rank(|X_ij|) по каждой строке (подгруппе)."""
    ranks = np.argsort(np.argsort(np.abs(X), axis=1), axis=1) + 1
    signs = np.where(X > 0, 1, -1)
    return (signs * ranks).sum(axis=1)


def arl(far: float) -> float:
    return float("inf") if far <= 0 else 1.0 / far


def mrl(far: float) -> float:
    return float("nan") if not (0 < far < 1) else ceil(log(0.5) / log(1 - far))


# --------------------------------------------------------------------------- #
def main() -> None:
    print("A. Границы a и FAR по правилам, n = 2..20")
    print(f"  {'n':>3} {'S':>4} | {'exact':>5} {'FAR':>10} | {'normal':>7} | "
          f"{'npSPC-exact':>12} {'FAR':>10} | {'npSPC-asym':>10}")
    rows = []
    for n in range(2, 21):
        S = n * (n + 1) // 2
        a_ex, f_ex = book_limits(n)
        a_s, _ = SignedRankChart._calc_a_normal(n, FAR0, _SR._p_sr_ge_a)
        a_ne, f_ne = npspc_exact(n, 0.0027)
        u_asym = npspc_asym(n, 0.0027)
        rows.append((n, a_ex, a_s, a_ne))
        print(f"  {n:>3} {S:>4} | {a_ex:>5} {f_ex:>10.6f} | {a_s:>7} | "
              f"{a_ne:>12} {f_ne:>10.6f} | {u_asym:>10.3f}")
    print("  exact != npSPC-exact(.0027) при n =",
          [r[0] for r in rows if r[1] != r[3]] or "—")
    print("  exact == normal при n =",
          [r[0] for r in rows if r[1] == r[2]] or "—")

    print()
    print("B. Сигнал при сдвиге δ, n = 16, m = 500000")
    n = 16
    a_ex, _ = book_limits(n)
    a_ne, _ = npspc_exact(n, 0.0027)
    print(f"  a: exact = {a_ex}, npSPC-exact(.0027) = {a_ne}")
    print(f"  {'δ(σ)':>5} {'Φ(δ)':>7} | {'exact':>19} | "
          f"{'npSPC-exact(.0027)':>19}")
    print(f"  {'':>5} {'':>7} | {'P_conv':>9} {'P_mc':>9} | "
          f"{'P_conv':>9} {'P_mc':>9}")
    rng = np.random.default_rng(20261018)
    m = 500_000
    for d in DELTAS:
        X = rng.standard_normal((m, n)) + d
        sr = sr_statistics(X)
        print(f"  {d:>5.1f} {norm.cdf(d):>7.4f} | "
              f"{p_signal_conv(n, a_ex, d):>9.6f} {p_signal_mc(sr, a_ex):>9.6f} | "
              f"{p_signal_conv(n, a_ne, d):>9.6f} {p_signal_mc(sr, a_ne):>9.6f}")

    print()
    print("C. FAR: теория vs Монте-Карло, n = 16, m = 500000, IC")
    rng = np.random.default_rng(20261018)
    X = rng.standard_normal((m, n))
    sr = sr_statistics(X)
    d16 = sr_dist(n)
    print(f"  {'правило':<20} {'a':>3} {'FAR_mc':>10} {'FAR_theory':>11} "
          f"{'ARL_mc':>9}")
    for rule, a in [("exact", a_ex),
                    ("normal", SignedRankChart._calc_a_normal(
                        n, FAR0, _SR._p_sr_ge_a)[0]),
                    ("npSPC-exact(.0027)", a_ne)]:
        far_mc = p_signal_mc(sr, a)
        far_th = far_abs(n, a, d16)
        print(f"  {rule:<20} {a:>3} {far_mc:>10.6f} {far_th:>11.6f} "
              f"{arl(far_mc):>9.2f}")

    print()
    print("D. Время, n = 16")
    t0 = time.perf_counter()
    for _ in range(1000):
        book_limits(16)
    t1 = time.perf_counter()
    print(f"  a, exact:          1000 вызовов — {t1 - t0:.4f} с")
    t0 = time.perf_counter()
    for _ in range(1000):
        npspc_exact(16)
    t1 = time.perf_counter()
    print(f"  a, npSPC-exact:    1000 вызовов — {t1 - t0:.4f} с")

    t0 = time.perf_counter()
    _ = sr_dist(30)
    t1 = time.perf_counter()
    print(f"  SR-распределение (ДП), n = 30 — {t1 - t0:.4f} с")

    X2 = rng.standard_normal((1_000_000, 16))
    t0 = time.perf_counter()
    sr2 = sr_statistics(X2)
    sig2 = np.abs(sr2) >= a_ex
    t1 = time.perf_counter()
    print(f"  SR, 1e6 подгрупп (IC): {t1 - t0:.4f} с, сигналов {int(sig2.sum())}")


if __name__ == "__main__":
    main()
