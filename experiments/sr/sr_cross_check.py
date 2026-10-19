#!/usr/bin/env python3
"""Python-сторона перекрёстной проверки SR: те же данные, что у npSPC.

Читает experiments/sr/data_sr_cross.csv (n строк — наблюдения, m
столбцов — подгруппы) и experiments/sr/data_sr_cross_out.csv
(результат R). Сверяет знаково-ранговую статистику и множества сигналов.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

N = 16
M = 3000
SHIFT_AT = 2001  # 1-based

X = pd.read_csv("experiments/sr/data_sr_cross.csv").values  # (n, m)
assert X.shape == (N, M), X.shape

S = N * (N + 1) // 2
# ранг |X| внутри каждой подгруппы (столбца); np.argsort дважды даёт ранги
ranks = np.argsort(np.argsort(np.abs(X), axis=0), axis=0) + 1
T_plus = np.where(X > 0, ranks, 0).sum(axis=0)
SR = 2 * T_plus - S

out = pd.read_csv("experiments/sr/data_sr_cross_out.csv")

print("SR: Python == R:", bool(np.array_equal(SR, out["SR"].values)))
for a, rule in ((108, "npSPC-exact"), (110, "exact")):
    sig = np.abs(SR) >= a
    before = int(sig[: SHIFT_AT - 1].sum())
    label = "sig_np" if a == 108 else "sig_bk"
    print(f"{rule:<13} a={a:>3}: сигналов {int(sig.sum())}, IC {before}, "
          f"FAR(IC) {before / (SHIFT_AT - 1):.5f}, "
          f"R[{label}] == Python: {bool(np.array_equal(sig, out[label].values))}")
print("нулевых отклонений:", int((X == 0).sum()))
print("SR[1:12]:", SR[:12].tolist())
