"""Пример 4.10 — CUSUM-SR: марковский расчёт длины серии.

Источник
--------
Chakraborti, S. and Graham, M.A. (2019). *Nonparametric Statistical
Process Control*. John Wiley & Sons.
Раздел 4.2.2.4.3, ур. 4.12, стр. 206; пример 4.10, стр. 238–240,
таблицы 4.13–4.14, уравнения 3.22–3.24 (стр. 112).

Что показывает пример
---------------------
Верхняя односторонняя CUSUM-SR с ``n = 4``, ``k = 2``, ``h = 6``.
Пространство состояний ``Ω⁺ = {0, 2, 4, 6}`` (6 — поглощающее),
матрица переходов ``Q`` по распределению статистики Уилкоксона ``T_n⁺``
(табл. 4.3) и точные характеристики RL:
``ARL_IC = 6.81``, ``SDRL_IC = 6.11``, перцентили ``1, 2, 5, 9, 19``.
"""

from __future__ import annotations

from _common import ROOT, ExampleReport, plot_run_length
from nonparametric_charts.utils.run_length import cusum_signed_rank_run_length

# Пример 4.10: верхняя односторонняя карта.
N = 4
K = 2.0
H = 6.0

# Матрица Q (стр. 238–239), строки и столбцы — состояния 0, 2, 4.
Q_BOOK = [
    [11 / 16, 2 / 16, 1 / 16],
    [9 / 16, 2 / 16, 2 / 16],
    [7 / 16, 2 / 16, 2 / 16],
]

# Вероятности поглощения (сигнала) из состояний 0, 2, 4.
ABSORB_BOOK = [2 / 16, 3 / 16, 5 / 16]

BOOK_PERCENTILES = [1, 2, 5, 9, 19]


def main() -> int:
    rep = ExampleReport(
        "4.10",
        "CUSUM-SR: марковский расчёт длины серии",
        "Chakraborti & Graham (2019), § 4.2.2.4.3, ур. 4.12, стр. 206; "
        "пример 4.10, стр. 238–240, табл. 4.13–4.14",
    )
    rep.start()

    result = cusum_signed_rank_run_length(N, K, H, sided="upper")

    rep.section("Пространство состояний (ур. 4.12, табл. 4.13–4.14)")
    rep.check(
        "непоглощающие состояния",
        [int(state) for state in result.states],
        [0, 2, 4],
    )
    rep.check("h (поглощающее состояние)", result.h, 6.0)
    rep.check("число непоглощающих состояний", result.n_states, 3)

    rep.section("Матрица переходов Q (стр. 238–239)")
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

    rep.section("Характеристики RL (стр. 240)")
    rep.check("ARL_IC", result.arl, 6.81, approx=True, tol=0.01)
    rep.check("SDRL_IC", result.sdrl, 6.11, approx=True, tol=0.01)
    rep.check("MRL_IC", result.mrl, 5)
    rep.check(
        "перцентили 5/25/50/75/95",
        [result.percentiles[q] for q in (0.05, 0.25, 0.5, 0.75, 0.95)],
        BOOK_PERCENTILES,
    )
    rep.line(
        "Распределение SR_t берётся из T_n⁺ (табл. 4.3); "
        "точный расчёт подтверждает книжные значения."
    )

    path = rep.results_dir() / "example_4_10_cusum_sr_markov.png"
    rep.section("График распределения RL")
    plot_run_length(
        result,
        path,
        "CUSUM-SR: распределение длины серии "
        rf"($n={N}$, $k={K:g}$, $h={H:g}$)",
    )
    rep.line(f"сохранён: {path.relative_to(ROOT)}")

    return rep.finish()


if __name__ == "__main__":
    raise SystemExit(main())
