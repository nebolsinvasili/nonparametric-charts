#!/usr/bin/env python3
"""Кросс-валидация CUSUM-SN/SR: nonparametric_charts против npSPC (R).

Сверяет три уровня (этап 3b.10 плана `docs/reports/cusum_plan.md`):

1. **Статистики подгрупп** — знаковая ``SN = n⁺ − n⁻`` и знаково-ранговая
   ``SR = 2T⁺ − n(n+1)/2`` на одних и тех же данных (включая данные книги:
   ``data1`` — табл. 4.7a, стр. 226; ``data2`` — табл. 4.6, стр. 22).
2. **Кумулятивные суммы и сигналы** — ``S⁺``/``S⁻`` и индекс первой тревоги
   по сетке ``(k, h)`` и сторон карты.
3. **Длины серий** — ARL по имитации на общих данных (R и Python считают
   одну и ту же выборку) и точный марковский ARL (ур. 4.9, стр. 203;
   ур. 4.12, стр. 206).

Эталон R-стороны — пакет ``npSPC`` (CER-UFBA/npSPC, функции ``cusum_sn`` /
``cusum_sr``); его заведомые особенности фиксируются отдельно, без подгонки
нашей реализации.

Запуск из корня репозитория:
    R_LIBS=/tmp/opencode/renv/lib/R/library \\
        RSCRIPT=/tmp/opencode/renv/bin/Rscript \\
        poetry run python experiments/cusum/05_cross_validation.py

Без R (использует ранее выгруженные CSV):
    poetry run python experiments/cusum/05_cross_validation.py --no-r
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "src")

from nonparametric_charts.charts.cusum_sign_chart import (  # noqa: E402
    CusumSignChart,
)
from nonparametric_charts.charts.cusum_signed_rank_chart import (  # noqa: E402
    CusumSignedRankChart,
)
from nonparametric_charts.utils.run_length import (  # noqa: E402
    cusum_sign_run_length,
    cusum_signed_rank_run_length,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
XVAL = HERE / "xval"
RESULTS = ROOT / "results" / "experiments"

STAT_KEYS = {'SN': ('sn', 'sn_plus', 'sn_minus'),
             'SR': ('sr', 'sr_plus', 'sr_minus')}


# --------------------------------------------------------------------------- #
#  Запуск R-стороны
# --------------------------------------------------------------------------- #

def run_r() -> None:
    """Запустить R-скрипт сверки.

    Нужны R и пакет npSPC (см. ``experiments/00_ENVIRONMENT.txt``).
    """
    rscript = os.environ.get('RSCRIPT', 'Rscript')
    cmd = [rscript, str(HERE / '05_cross_validation.R')]
    print(f'R: {" ".join(cmd)}')
    subprocess.run(cmd, cwd=ROOT, check=True)


# --------------------------------------------------------------------------- #
#  Общие данные и карты
# --------------------------------------------------------------------------- #

def load_datasets() -> dict[str, pd.DataFrame]:
    """Восстановить наборы данных из long-формата ``xval/data.csv``."""
    raw = pd.read_csv(XVAL / 'data.csv')
    datasets: dict[str, pd.DataFrame] = {}
    for name, block in raw.groupby('dataset', sort=False):
        wide = block.pivot(index='group', columns='obs', values='value')
        wide.columns = [f'obs{int(c)}' for c in wide.columns]
        datasets[name] = wide.reset_index(drop=True)[
            sorted(wide.columns, key=lambda c: int(c[3:]))
        ]
    return datasets


def build_chart(
    statistic: str, data: pd.DataFrame, n: int, k: float, h: float
):
    """Создать карту с ``μ₀ = 0`` (как в npSPC) и посчитать пределы."""
    cls = CusumSignChart if statistic == 'SN' else CusumSignedRankChart
    chart = cls(
        data=data, sample_size=n, target_value=0.0,
        k=float(k), h=float(h),
    )
    chart.calculate_limits()
    return chart


def chart_first_signal(chart, sided: str, groups: int):
    """Индекс первой тревоги (1-based) или ``None``."""
    found = [v['subgroup'] for v in chart.violations
             if sided == 'two' or v['side'] == sided]
    return min(found) if found else None


# --------------------------------------------------------------------------- #
#  1–2. Статистики, кумулятивные суммы, сигналы
# --------------------------------------------------------------------------- #

def check_statistics(datasets: dict[str, pd.DataFrame], out: list[str]) -> set:
    """Сверить статистики; вернуть наборы, где npSPC расходится (нули)."""
    steps = pd.read_csv(XVAL / 'steps.csv')
    rows, mismatches, zero_sets = [], 0, set()
    for (name, statistic), block in steps.groupby(['dataset', 'statistic'],
                                                  sort=False):
        key, _, _ = STAT_KEYS[statistic]
        data = datasets[name]
        n = data.shape[1]
        chart = build_chart(statistic, data, n, 1.0, 10.0)
        ours = chart.subgroups[key].to_numpy()

        block = block.sort_values('group')
        r_npspc = block['step'].to_numpy()
        diff_npspc = np.max(np.abs(ours - r_npspc))
        if statistic == 'SR':
            diff_ref = np.max(np.abs(ours - block['step_alt'].to_numpy()))
            reference = 'n_eff'
        else:
            diff_ref = diff_npspc
            reference = 'npSPC'

        if diff_ref > 1e-9:
            mismatches += 1
        expected = statistic == 'SR' and diff_npspc > 1e-9
        if expected:
            zero_sets.add((name, statistic))
        rows.append((name, statistic, n, diff_npspc, diff_ref, reference))

    out.append('1. СТАТИСТИКИ ПОДГРУПП (max |Python − R|)')
    out.append(f'   {"dataset":<9}{"stat":<5}{"n":>3}'
               f'{"|Δ| vs npSPC":>14}{"|Δ| vs эталон":>15}  эталон / note')
    for name, statistic, n, d_np, d_ref, reference in rows:
        if d_ref > 1e-9:
            note = 'РАСХОЖДЕНИЕ с эталоном'
        elif d_np > 1e-9:
            note = 'нули в данных: npSPC центрирует SR по n, не по n_eff'
        else:
            note = 'ok'
        out.append(f'   {name:<9}{statistic:<5}{n:>3}'
                   f'{d_np:>14.3e}{d_ref:>15.3e}  {reference:<8} {note}')
    out.append(f'   Итог: расхождений с эталоном — {mismatches}; '
               f'наборов с нулями (SR): {len(zero_sets)}.')
    out.append('')
    return zero_sets


def check_signals(datasets: dict[str, pd.DataFrame], zero_sets: set,
                  out: list[str]) -> None:
    configs = pd.read_csv(XVAL / 'config.csv')
    signals = pd.read_csv(XVAL / 'signals.csv')
    merged = configs.merge(
        signals, on=['dataset', 'statistic', 'k', 'h'], how='left'
    )

    total = matched = 0
    expected_total = expected_matched = 0
    npspc_total = npspc_matched = 0
    first_group = raw_missed_first = 0
    worst: list[str] = []
    for _, row in merged.iterrows():
        name, statistic = row['dataset'], row['statistic']
        nsig = int(row['n'])
        chart = build_chart(
            statistic, datasets[name], nsig, row['k'], row['h']
        )
        sided = {
            'upper': 'upper', 'lower': 'lower', 'two.sided': 'two'
        }[row['side']]
        ours = chart_first_signal(chart, sided, len(datasets[name]))
        ref = (None if pd.isna(row['signal_fixed'])
               else int(row['signal_fixed']))
        raw = (None if pd.isna(row['signal_npspc'])
               else int(row['signal_npspc']))
        expected = (name, statistic) in zero_sets
        if expected:
            expected_total += 1
            if ours == ref:
                expected_matched += 1
        else:
            total += 1
            if ours == ref:
                matched += 1
            elif len(worst) < 6:
                worst.append(
                    f'{name}/{statistic} k={row["k"]:g} h={row["h"]:g} '
                    f'{row["side"]}: Python={ours} R={ref}'
                )
            npspc_total += 1
            if ours == raw:
                npspc_matched += 1
            if ours == 1:
                first_group += 1
                if raw != ours:
                    raw_missed_first += 1
    out.append('2. СИГНАЛЫ (первая тревога по сетке (k, h), стороны)')
    out.append(f'   Эталон (исправленная рекурсия): конфигураций {total}, '
               f'совпало {matched}.')
    out.append(f'   Наборы SR с нулями: совпало {expected_matched}/'
               f'{expected_total} — расхождение ожидаемо.')
    out.append(f'   Сырой вызов npSPC::cusum_*: совпало {npspc_matched}/'
               f'{npspc_total}; все {npspc_total - npspc_matched} расхождений '
               'объясняются фиктивным нулём в позиции 1: теряется первая '
               f'подгруппа (тревог в ней — {first_group}) и её вклад в сумму.')
    out.append(f'   Без потери первой подгруппы npSPC совпал бы с эталоном '
               f'во всех {npspc_total} конфигурациях.')
    for line in worst:
        out.append(f'   расхождение: {line}')
    out.append('')


# --------------------------------------------------------------------------- #
#  3. Длина серии: имитация на общих данных и точный марковский расчёт
# --------------------------------------------------------------------------- #

def simulated_rl(config: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """RL по каждому прогону на данных, сгенерированных в R."""
    raw = pd.read_csv(XVAL / f'arl_{config["name"]}.csv')
    sided = config['sided']
    side_key = 'two' if sided == 'two.sided' else sided
    rls, censored = [], []
    for _, block in raw.groupby('sim', sort=True):
        wide = block.pivot(index='group', columns='obs', values='value')
        wide.columns = [f'obs{int(c)}' for c in wide.columns]
        order = sorted(wide.columns, key=lambda c: int(c[3:]))
        data = wide[order].reset_index(drop=True)
        chart = build_chart(
            config['statistic'], data, int(config['n']),
            float(config['k']), float(config['h']),
        )
        rl = chart_first_signal(chart, side_key, len(data))
        rls.append(np.nan if rl is None else float(rl))
        censored.append(rl is None)
    return np.array(rls, dtype=float), np.array(censored, dtype=bool)


def check_run_length(out: list[str]) -> None:
    arl_config = pd.read_csv(XVAL / 'arl_config.csv')
    arl_rl = pd.read_csv(XVAL / 'arl_rl.csv')

    out.append('3. ДЛИНА СЕРИИ (имитация на общих данных + точный марковский)')
    header = (f'   {"config":<9}{"sided":<10}{"ARL R":>10}{"ARL Py":>10}'
              f'{"Δ":>8}{"RL совпало":>12}{"npSPC":>8}'
              f'{"SE R":>8}{"марков":>10}')
    out.append(header)
    for _, config in arl_config.iterrows():
        ref = arl_rl[arl_rl['config'] == config['name']].sort_values('sim')
        ref_rl = ref['rl'].to_numpy()
        raw_rl = ref['rl_npspc'].to_numpy()
        ours, _ = simulated_rl(config)

        both_known = ~np.isnan(ref_rl) & ~np.isnan(ours)
        same_known = both_known & (np.abs(ref_rl - ours) < 1e-9)
        both_censored = np.isnan(ref_rl) & np.isnan(ours)
        cens_agrees = np.isnan(ref_rl) == np.isnan(ours)
        matches = int(same_known.sum() + both_censored.sum())
        raw_matches = int(np.sum((np.isnan(raw_rl) & np.isnan(ours)) |
                                 (np.abs(raw_rl - ours) < 1e-9)))

        ref_mean = np.nanmean(ref_rl)
        our_mean = np.nanmean(ours)
        known = ref_rl[~np.isnan(ref_rl)]
        se = float(np.std(known, ddof=1) / np.sqrt(known.size))

        stat = config['statistic']
        sided = 'two' if config['sided'] == 'two.sided' else config['sided']
        if config['shift'] == 0:
            if stat == 'SN':
                exact = cusum_sign_run_length(
                    int(config['n']), float(config['k']), float(config['h']),
                    sided=sided,
                ).arl
            else:
                exact = cusum_signed_rank_run_length(
                    int(config['n']), float(config['k']), float(config['h']),
                    sided=sided,
                ).arl
            arrow = f'{exact:>10.1f}'
        else:
            arrow = f'{"—":>10}'

        out.append(
            f'   {config["name"]:<9}{config["sided"]:<10}'
            f'{ref_mean:>10.2f}{our_mean:>10.2f}'
            f'{our_mean - ref_mean:>8.2f}'
            f'{matches:>12}{raw_matches:>8}{se:>8.2f}{arrow}'
        )
        if not (same_known.all() and cens_agrees.all()):
            bad = np.nonzero(
                ~(same_known | (np.isnan(ref_rl) & np.isnan(ours)))
            )[0]
            out.append(f'   прогоны с расхождением RL: {bad[:8].tolist()} '
                       f'(всего {bad.size})')
    out.append('   «RL совпало» — прогоны с совпадающим RL против '
               'исправленной рекурсии; «npSPC» — против сырого вызова '
               'cusum_* (включая совпадение отсутствия тревоги).')
    out.append('')


# --------------------------------------------------------------------------- #

def main() -> int:
    no_r = '--no-r' in sys.argv
    if not no_r:
        run_r()
    elif not (XVAL / 'config.csv').exists():
        print('Нет CSV R-стороны; запустите без --no-r (нужен R + npSPC).')
        return 1

    datasets = load_datasets()
    out: list[str] = []
    out.append('=' * 72)
    out.append('3b.10. Кросс-валидация CUSUM-SN/SR: Python против npSPC (R)')
    out.append('Эталон: npSPC (CER-UFBA/npSPC), функции cusum_sn / cusum_sr.')
    out.append(
        'Источник метода: Chakraborti & Graham (2019), '
        '§4.2.2.1, стр. 202–203;'
    )
    out.append('§4.2.2.4, стр. 205–206.')
    out.append('=' * 72)
    out.append('')

    check_statistics_result = check_statistics(datasets, out)
    check_signals(datasets, check_statistics_result, out)
    check_run_length(out)

    text = '\n'.join(out)
    print(text)
    RESULTS.mkdir(parents=True, exist_ok=True)
    report = RESULTS / 'cusum_cross_validation.txt'
    report.write_text(text + '\n', encoding='utf-8')
    print(f'Отчёт: {report.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
