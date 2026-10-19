#!/usr/bin/env python3
"""Координаты графиков для отчёта о верификации SR-карты.

Печатает макросы \\def для вставки в docs/reports/sr_verification.tex.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "src")

from sr_analysis import (  # noqa: E402
    FAR0,
    ALPHA,
    _SR,
    book_limits,
    far_abs,
    npspc_asym,
    npspc_exact,
    p_sr_ge_a,
    p_signal_conv,
    sr_dist,
)

from nonparametric_charts.charts.signed_rank_chart import SignedRankChart  # noqa: E402


def sym_a(n: int) -> int:
    return SignedRankChart._calc_a_normal(n, FAR0, _SR._p_sr_ge_a)[0]


def near_a(n: int) -> int:
    return SignedRankChart._calc_a_nearest(n, ALPHA, _SR._p_abs_sr_ge_a)[0]


def coords(points, fmt: str = "{:.6f}") -> str:
    return " ".join(f"({x},{fmt.format(y)})" for x, y in points)


def main() -> None:
    ns = list(range(2, 21))

    print("% ==== SR: границы a(n) по режимам, n = 2..20 ====")
    print("\\def\\vSRACons{" + coords([(n, book_limits(n)[0]) for n in ns]) + "}")
    print("\\def\\vSRASym{" + coords([(n, sym_a(n)) for n in ns]) + "}")
    print("\\def\\vSRANear{" + coords([(n, near_a(n)) for n in ns]) + "}")
    print("\\def\\vSRANpExact{" + coords([(n, npspc_exact(n, FAR0)[0]) for n in ns]) + "}")
    print("\\def\\vSRANpAsym{" + coords([(n, npspc_asym(n, FAR0)) for n in ns]) + "}")

    print("% ==== SR: достигнутый FAR(n) по режимам, n = 2..20 ====")
    print("\\def\\vSRFARCons{" + coords([(n, book_limits(n)[1]) for n in ns]) + "}")
    print("\\def\\vSRFARSym{" + coords(
        [(n, far_abs(n, sym_a(n))) for n in ns]) + "}")
    print("\\def\\vSRFARNear{" + coords(
        [(n, far_abs(n, near_a(n))) for n in ns]) + "}")

    print("% ==== SR: таблица режимов, n = 2..20 ====")
    rows = []
    for n in ns:
        ac, fc = book_limits(n)
        asy, _ = SignedRankChart._calc_a_normal(n, FAR0, _SR._p_sr_ge_a)
        an, fn = SignedRankChart._calc_a_nearest(n, ALPHA, _SR._p_abs_sr_ge_a)
        rows.append(f"{n} & {ac} & {fc:.6f} & {asy} & {far_abs(n, asy):.6f} "
                    f"& {an} & {fn:.6f}")
    print("\\def\\vSRModeTable{%")
    print(" \\\\\n".join(rows) + " \\\\}")

    print("% ==== SR: пример n = 14 (критерий nearest), a = 40..80 ====")
    print("\\def\\vSRNearAbs14{" + coords(
        [(a, far_abs(14, a)) for a in range(40, 81)]) + "}")
    print("\\def\\vSRNearMin14{" + coords(
        [(a, far_abs(14, a)) for a in (62, 63)]) + "}")

    print("% ==== SR: мощность при сдвиге (n = 16), delta = 0..2 ====")
    deltas = [i / 4 for i in range(0, 9)]
    n = 16
    a_book = book_limits(n)[0]
    a_np = npspc_exact(n, FAR0)[0]
    print(f"% n=16: книга a={a_book}, npSPC exact a={a_np}")
    print("\\def\\vSROCBk{" + coords(
        [(d, p_signal_conv(n, a_book, d)) for d in deltas]) + "}")
    print("\\def\\vSROCNp{" + coords(
        [(d, p_signal_conv(n, a_np, d)) for d in deltas]) + "}")

    print("% ==== SR: распределение SR в IC (n = 5) ====")
    d5 = sr_dist(5)
    pts = sorted((v, p) for v, p in d5.items())
    print("\\def\\vSRpmfFive{" + coords(pts) + "}")

    print("% ==== SR: односторонний хвост P(SR>=a) для n = 5,10,14,20 ====")
    names = {5: "Five", 10: "Ten", 14: "Fourteen", 20: "Twenty"}
    for nn in (5, 10, 14, 20):
        d = sr_dist(nn)
        S = nn * (nn + 1) // 2
        pts = [(a, p_sr_ge_a(nn, a, d)) for a in range(S if S % 2 else S - 1,
                                                      0, -2)]
        print(f"\\def\\vSRTail{names[nn]}{{" + coords(pts) + "}")


if __name__ == "__main__":
    main()
