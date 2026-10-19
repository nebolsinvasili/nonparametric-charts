#!/usr/bin/env python3
"""Генератор координат графиков и строк таблиц для отчётов по границам.

Печатает LaTeX-макросы (\\def...), которые вставляются в отчёты
`docs/reports/*.tex`. Данные считаются
точно (бином / перебор всех 2^n знаковых наборов), без внешних файлов.

Запуск из корня репозитория:

    poetry run python docs/reports/scripts/gen_coords.py > /tmp/coords.tex

Первоисточник правил: Chakraborti & Graham (2019), § 4.2.1.1 (SN) и
§ 4.2.1.2 (SR).
"""

from __future__ import annotations

import sys
from math import comb
from pathlib import Path
from itertools import product
from collections import Counter

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from nonparametric_charts.charts.sign_chart import SignChart  # noqa: E402
from nonparametric_charts.charts.signed_rank_chart import SignedRankChart  # noqa: E402

FAR0 = 0.0027
ALPHA = 0.05
BS = "\\\\"  # разделитель строк таблицы


def coords(points) -> str:
    return " ".join(f"({x},{y:.7f})" for x, y in points)


def sn_mode(n: int):
    a_c, f_c = SignChart._calc_a_exact(n, FAR0)
    a_n, f_n = SignChart._calc_a_nearest(n, ALPHA)
    a_s, f_s = SignChart._calc_a_normal(n, FAR0)
    return a_c, f_c, a_n, f_n, a_s, f_s


def sr_chart() -> SignedRankChart:
    ch = SignedRankChart.__new__(SignedRankChart)
    ch._sr_dist_cache = {}
    return ch


SR = sr_chart()


def sr_mode(n: int):
    a_c, f_c = SR._calc_a_exact(n, FAR0, SR._p_sr_ge_a)
    a_n, f_n = SR._calc_a_nearest(n, ALPHA, SR._p_abs_sr_ge_a)
    a_s, f_s = SR._calc_a_normal(n, FAR0, SR._p_sr_ge_a)
    return a_c, f_c, a_n, f_n, a_s, f_s


def main() -> None:
    n_sn = list(range(1, 21))
    n_sr = list(range(2, 21))

    print("% ==== SN: таблица сравнения режимов, n = 1..20 ====")
    rows = []
    for n in n_sn:
        a_c, f_c, a_n, f_n, a_s, _ = sn_mode(n)
        par = "да" if (a_n % 2) == (n % 2) else "нет"
        rows.append(f"{n} & {a_c} & {f_c:.6f} & {a_n} & {f_n:.6f} & {a_s} & {par}")
    print("\\def\\snModeTable{%\n" + (BS + "\n").join(rows) + BS + "\n}")

    print("% ==== SN: a(n) по режимам, n = 1..20 ====")
    print("\\def\\snACons{" + coords([(n, sn_mode(n)[0]) for n in n_sn]) + "}")
    print("\\def\\snANear{" + coords([(n, sn_mode(n)[2]) for n in n_sn]) + "}")

    print("% ==== SN: хвост при n = 14 (достижимые a) ====")
    pts = [(a, SignChart._p_sn_ge_a(14, a)) for a in range(14, 0, -2)]
    print("\\def\\snTailFourteen{" + coords(pts) + "}")

    print("% ==== SN: критерий nearest при n = 14, |P(|SN|>=a) - 0.05| ====")
    pts = [(a, abs(SignChart._p_abs_sn_ge_a(14, a) - ALPHA)) for a in range(1, 15)]
    print("\\def\\snNearDiff{" + coords(pts) + "}")
    print("\\def\\snNearMin{(7,0.0073730) (8,0.0073730)}")
    print("% ==== SN: двусторонний хвост P(|SN|>=a) при n = 14 (a = 1..14) ====")
    pts = [(a, SignChart._p_abs_sn_ge_a(14, a)) for a in range(1, 15)]
    print("\\def\\snAbs14{" + coords(pts) + "}")

    print("% ==== SR: таблица сравнения режимов, n = 2..20 ====")
    rows = []
    for n in n_sr:
        S = n * (n + 1) // 2
        a_c, f_c, a_n, f_n, a_s, f_s = sr_mode(n)
        par = "да" if (a_n % 2) == (S % 2) else "нет"
        rows.append(f"{n} & {S} & {a_c} & {f_c:.6f} & {a_s} & {f_s:.6f} & "
                    f"{a_n} & {f_n:.6f} & {par}")
    print("\\def\\srModeTable{%\n" + (BS + "\n").join(rows) + BS + "\n}")

    print("% ==== SR: a(n) по режимам, n = 2..20 ====")
    print("\\def\\srACons{" + coords([(n, sr_mode(n)[0]) for n in n_sr]) + "}")
    print("\\def\\srASym{" + coords([(n, sr_mode(n)[4]) for n in n_sr]) + "}")
    print("\\def\\srANear{" + coords([(n, sr_mode(n)[2]) for n in n_sr]) + "}")
    print("\\def\\srFARSym{" + coords([(n, sr_mode(n)[5]) for n in n_sr]) + "}")

    print("% ==== SR: критерий nearest при n = 14, |P(|SR|>=a) - 0.05| (a = 40..80) ====")
    pts = [(a, abs(SR._p_abs_sr_ge_a(14, a) - ALPHA)) for a in range(40, 81)]
    print("\\def\\srNearDiff{" + coords(pts) + "}")
    print("\\def\\srNearMin{(62,0.0005620) (63,0.0005620)}")
    print("% ==== SR: двусторонний хвост P(|SR|>=a) при n = 14 (a = 40..80) ====")
    pts = [(a, SR._p_abs_sr_ge_a(14, a)) for a in range(40, 81)]
    print("\\def\\srAbs14{" + coords(pts) + "}")


if __name__ == "__main__":
    main()
