#!/usr/bin/env python3
"""Координаты графиков для отчёта о верификации SN-карты.

Печатает макросы \\def для вставки в docs/reports/sn_verification.tex.
"""
from __future__ import annotations

from math import comb, ceil, floor, log

from scipy.stats import binom, norm

FAR0, ALPHA = 0.0027, 0.05


def npspc_a(n: int, far: float = 0.0027) -> int:
    for k in range(1, n + 1):
        if binom.sf(k - 1, n, 0.5) < far:
            return 2 * k - n
    return n


def book_a(n: int, far0: float = FAR0) -> int:
    target = far0 / 2
    for a in range(1 if n % 2 else 2, n + 1, 2):
        if binom.sf(ceil((n + a) / 2) - 1, n, 0.5) <= target:
            return a
    return n


def near_a(n: int, alpha: float = ALPHA) -> int:
    best_a, best_d = 1, float("inf")
    for a in range(1, n + 1):
        d = abs(min(2 * binom.sf(ceil((n + a) / 2) - 1, n, 0.5), 1.0) - alpha)
        if d < best_d:
            best_d, best_a = d, a
    return best_a


def sym_a(n: int, far0: float = FAR0) -> int:
    """Нормальная аппроксимация (режим normal): наименьшее достижимое
    значение (той же чётности, что n) не меньше z_{1−FAR0/2}·sqrt(n)."""
    a0 = ceil(norm.ppf(1 - far0 / 2) * n ** 0.5)
    a = a0 if a0 % 2 == n % 2 else a0 + 1
    return min(max(a, 1), n)


def p_signal(n: int, a: int, delta: float) -> float:
    p = float(norm.cdf(delta))
    return float(min(binom.sf(ceil((n + a) / 2) - 1, n, p)
                     + binom.cdf(floor((n - a) / 2), n, p), 1.0))


def far_abs(n: int, a: int) -> float:
    """Достигнутый двусторонний FAR = P(|SN| >= a) в IC."""
    return float(min(2 * binom.sf(ceil((n + a) / 2) - 1, n, 0.5), 1.0))


def coords(pts) -> str:
    return " ".join(f"({x},{y:.6f})" for x, y in pts)


def main() -> None:
    ns = list(range(1, 21))
    print("\\def\\verACons{" + coords([(n, book_a(n)) for n in ns]) + "}")
    print("\\def\\verANp{" + coords([(n, npspc_a(n, 0.0027)) for n in ns]) + "}")
    print("\\def\\verANear{" + coords([(n, near_a(n)) for n in ns]) + "}")

    deltas = [i / 4 for i in range(0, 9)]
    n = 16
    ab, an = book_a(n), npspc_a(n, 0.0027)
    print(f"% n=16: книга a={ab}, npSPC a={an}")
    print("\\def\\verOCBook{" + coords([(d, p_signal(n, ab, d)) for d in deltas]) + "}")
    print("\\def\\verOCNp{" + coords([(d, p_signal(n, an, d)) for d in deltas]) + "}")

    # нормальное приближение против точного
    print("\\def\\verNormDiff{" + coords(
        [(nn, book_a(nn) - ceil(norm.ppf(1 - FAR0 / 2) * nn ** 0.5))
         for nn in range(10, 61, 2)]) + "}")

    # --- режимы выбора a (раздел «Методы выбора константы a») ---
    ns30 = list(range(1, 31))
    print("\\def\\verModeCons{" + coords([(n, book_a(n)) for n in ns30]) + "}")
    print("\\def\\verModeSym{" + coords([(n, sym_a(n)) for n in ns30]) + "}")
    print("\\def\\verModeNear{" + coords([(n, near_a(n)) for n in ns30]) + "}")
    print("\\def\\verFARCons{" + coords([(n, far_abs(n, book_a(n))) for n in ns30]) + "}")
    print("\\def\\verFARSym{" + coords([(n, far_abs(n, sym_a(n))) for n in ns30]) + "}")
    print("\\def\\verFARNear{" + coords([(n, far_abs(n, near_a(n))) for n in ns30]) + "}")

    rows = []
    for n in range(1, 21):
        ac, asy, an = book_a(n), sym_a(n), near_a(n)
        rows.append(f"{n} & {ac} & {far_abs(n, ac):.6f} & {asy} & "
                    f"{far_abs(n, asy):.6f} & {an} & {far_abs(n, an):.6f}")
    print("\\def\\verModeTable{%")
    print(" \\\\\n".join(rows) + " \\\\}")

    # критерий nearest при n = 14
    print("\\def\\verNearAbs14{" + coords(
        [(a, far_abs(14, a)) for a in range(1, 15)]) + "}")
    print("\\def\\verNearMin14{" + coords(
        [(a, far_abs(14, a)) for a in (7, 8)]) + "}")


if __name__ == "__main__":
    main()
