"""Пример 4.8 — CUSUM-SN: марковский расчёт длины серии.

Источник
--------
Chakraborti, S. and Graham, M.A. (2019). *Nonparametric Statistical
Process Control*. John Wiley & Sons.
Раздел 4.2.2.3.1, ур. 4.9, стр. 203–204; пример 4.8, стр. 233–236,
таблицы 4.10–4.11, уравнения 3.22–3.24 (стр. 112).

Что показывает пример
---------------------
Верхняя односторонняя CUSUM-SN с ``n = 5``, ``k = 1``, ``h = 4``.
Строится пространство состояний ``Ω⁺ = {0, 2, 4}`` (4 — поглощающее),
матрица переходов ``Q`` и по ней точные характеристики RL:
``ARL_IC = 16.62``, ``SDRL_IC = 15.51``, перцентили ``2, 6, 12, 23, 48``.
"""

from __future__ import annotations

from _common import ROOT, ExampleReport, plot_run_length
from nonparametric_charts.utils.run_length import cusum_sign_run_length

# Пример 4.8: верхняя односторонняя карта.
N = 5
K = 1.0
H = 4.0

# Матрица Q (табл. 4.11 / стр. 235), строки и столбцы — состояния 0 и 2.
Q_BOOK = [
    [26 / 32, 5 / 32],
    [16 / 32, 10 / 32],
]

# Вероятности поглощения (сигнала) из состояний 0 и 2.
ABSORB_BOOK = [1 / 32, 6 / 32]

BOOK_PERCENTILES = [2, 6, 12, 23, 48]


def main() -> int:
    rep = ExampleReport(
        "4.8",
        "CUSUM-SN: марковский расчёт длины серии",
        "Chakraborti & Graham (2019), § 4.2.2.3.1, ур. 4.9, "
        "стр. 203–204; пример 4.8, стр. 233–236, табл. 4.10–4.11",
    )
    rep.start()

    result = cusum_sign_run_length(N, K, H, sided="upper")

    rep.section("Пространство состояний (ур. 4.9, табл. 4.10–4.11)")
    rep.check(
        "непоглощающие состояния",
        [int(state) for state in result.states],
        [0, 2],
    )
    rep.check("h (поглощающее состояние)", result.h, 4.0)
    rep.check("число непоглощающих состояний", result.n_states, 2)

    rep.section("Матрица переходов Q (стр. 235)")
    matrix = result.transition_matrix
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            rep.check(
                f"Q[{i}][{j}]",
                float(matrix[i, j]),
                Q_BOOK[i][j],
                approx=True,
                tol=1e-12,
            )

    absorbing = 1.0 - matrix.sum(axis=1)
    for i, expected in enumerate(ABSORB_BOOK):
        rep.check(
            f"P(сигнал за шаг | состояние {int(result.states[i])})",
            float(absorbing[i]),
            expected,
            approx=True,
            tol=1e-12,
        )

    rep.section("Характеристики RL (стр. 235)")
    rep.check("ARL_IC", result.arl, 16.62, approx=True, tol=0.01)
    rep.check("SDRL_IC", result.sdrl, 15.51, approx=True, tol=0.01)
    rep.check("MRL_IC", result.mrl, 12)
    rep.check(
        "перцентили 5/25/50/75/95",
        [result.percentiles[q] for q in (0.05, 0.25, 0.5, 0.75, 0.95)],
        BOOK_PERCENTILES,
    )
    rep.line(
        "ARL_IC = 1 / P(сигнал) для решётчатой статистики; "
        "точный расчёт подтверждает книжные значения."
    )

    path = rep.results_dir() / "example_4_8_cusum_sn_markov.png"
    rep.section("График распределения RL")
    plot_run_length(
        result,
        path,
        "CUSUM-SN: распределение длины серии "
        rf"($n={N}$, $k={K:g}$, $h={H:g}$)",
    )
    rep.line(f"сохранён: {path.relative_to(ROOT)}")

    return rep.finish()


if __name__ == "__main__":
    raise SystemExit(main())
