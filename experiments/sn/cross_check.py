#!/usr/bin/env python3
"""Python-сторона перекрёстной проверки: те же данные, что у npSPC.

Читает experiments/sn/data_cross.csv (n строк — наблюдения, m столбцов —
подгруппы) и experiments/sn/data_cross_out.csv (результат R).
Сверяет знаковую статистику и множества сигналов.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

N = 16
M = 3000
SHIFT_AT = 2001  # 1-based

X = pd.read_csv("experiments/sn/data_cross.csv").values  # (n, m)
assert X.shape == (N, M), X.shape

neg = (X < 0).sum(axis=0)
pos = (X > 0).sum(axis=0)
zero = (X == 0).sum(axis=0)
SN = pos - neg

out = pd.read_csv("experiments/sn/data_cross_out.csv")

print("SN: Python == R:", bool(np.array_equal(SN, out["SN"].values)))
for a, rule in ((12, "npSPC(.0027)"), (14, "exact")):
    sig = np.abs(SN) >= a
    before = int(sig[: SHIFT_AT - 1].sum())
    label = "sig_np" if a == 12 else "sig_bk"
    print(f"{rule:<13} a={a:>3}: сигналов {int(sig.sum())}, IC {before}, "
          f"FAR(IC) {before / (SHIFT_AT - 1):.5f}, "
          f"R[{label}] == Python: {bool(np.array_equal(sig, out[label].values))}")
print("нулевых отклонений:", int(zero.sum()))
print("SN[1:12]:", SN[:12].tolist())
