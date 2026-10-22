"""
Карта знако-ранговых сумм Шухарта (Shewhart Signed-Rank Chart)

Непараметрическая контрольная карта для медианы симметричного
непрерывного распределения. Основана на статистике знаковых рангов
Уилкоксона (Wilcoxon signed-rank).

Теория (Chakraborti & Graham, 2019, Section 4.2.1.2, стр. 196–202):
----------------------------------------------------------------------
Для каждой подгруппы размера n > 1 вычисляются:
    1. Абсолютные отклонения |X_ij − μ₀|, j = 1..n
    2. Ранги R_ij этих отклонений внутри подгруппы (1..n)
    3. Знаковая статистика:
         SR_i = Σ_{j=1}^{n} φ(X_ij − μ₀) · R_ij
       где φ(t) = +1 при t > 0, −1 при t < 0, 0 при t = 0.

    Связь с классической статистикой Уилкоксона T_n⁺:
         SR_i = 2·T_n⁺ − n(n+1)/2

Распределение SR_i в IC:
    Не имеет замкнутой формы; строится динамическим программированием
    (свёрткой) по 2^n знаковым комбинациям рангов 1..n за O(n·S),
    S = n(n+1)/2.

Контрольные границы:
    LCL = −a,  CL = 0,  UCL = +a,  0 < a ≤ n(n+1)/2

Правило сигнала:
    процесс OOC, если |SR_i| ≥ a

Длина серии в Case K:
    N ~ GEO(FAR),  ARL = 1/FAR,
    MRL = ⌈ln(0.5) / ln(1−FAR)⌉

Три подхода к расчёту константы a:
----------------------------------
1. **Точный (консервативный)** (по книге, стр. 198), id `exact`:
       a — наименьшее достижимое (той же чётности, что и S)
       с P(SR ≥ a) ≤ FAR₀/2; при недостижимости a = S.
2. **Нормальная аппроксимация** (id `normal`):
       a = наименьшее достижимое значение (той же чётности, что и S),
       не меньше z_{1−FAR₀/2} · SD(SR), где
       SD(SR) = sqrt(n(n+1)(2n+1)/6); ср. npSPC::Limits_asymptotical.
3. **«Ближайший»** (id `nearest`, обучение / сравнение):
       a = argmin_a |P(|SR| ≥ a) − α|
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from typing import Dict, Optional, Tuple, List, Literal
from scipy import stats

try:
    from nonparametric_charts.base.base_chart import BaseControlChart
except ImportError:
    class BaseControlChart:
        def __init__(self, data, sample_size):
            self.data = data
            self.sample_size = sample_size

from nonparametric_charts.utils.statistics import signed_rank_details

from nonparametric_charts.utils.plot_style import (
    ACCENT,
    ALERT,
    DATA_MARKER_SIZE,
    INK,
    PALETTE,
    SIGNAL_MARKER_SIZE,
    ZONE_FILL,
    ZONE_LINE,
    annotate_values,
    data_legend,
    hline,
    math_text,
)


ApproachType = Literal['exact', 'nearest', 'normal']

# Устаревшие идентификаторы подходов (обратная совместимость).
APPROACH_ALIASES = {
    'conservative': 'exact',
    'symmetric': 'normal',
}


def normalize_approach(approach: str) -> str:
    """Приводит устаревший идентификатор подхода к актуальному."""
    new = APPROACH_ALIASES.get(approach)
    if new is not None:
        warnings.warn(
            f"approach={approach!r} устарел, используйте {new!r}",
            DeprecationWarning, stacklevel=2,
        )
        return new
    return approach


class SignedRankChart(BaseControlChart):
    """
    Карта знако-ранговых сумм (Shewhart Signed-Rank Chart).

    Непараметрическая карта для контроля медианы симметричного
    непрерывного распределения.

    Parameters
    ----------
    data : pd.DataFrame
        Данные (m подгрупп × n наблюдений).
    sample_size : int
        Размер подгруппы n (> 1).
    target_value : float, optional
        Целевое значение μ₀. Если None — медиана всех данных.
    approach : {'exact', 'nearest', 'normal'}, default='exact'
        Подход к расчёту константы a. Устаревшие синонимы
        {'conservative', 'symmetric'} принимаются с предупреждением.
    far0 : float, default=0.0027
        Номинальный FAR для точного и нормального подходов.
    alpha : float, default=0.05
        Уровень значимости для «ближайшего» подхода.
    a_value : int, optional
        Явно заданное значение a. Если задано — подходы игнорируются.
    """

    APPROACH_LABELS = {
        'exact': 'Точный (консервативный, FAR₀)',
        'normal': 'Нормальная аппроксимация',
        'nearest': 'Ближайший (α)',
    }

    #: Короткие подписи для заголовка (без Unicode-индексов, безопасно для LaTeX).
    APPROACH_PLOT_LABELS = {
        'exact': 'точный (консервативный)',
        'normal': 'нормальная аппроксимация',
        'nearest': 'ближайший',
    }

    def __init__(
        self,
        data: pd.DataFrame,
        sample_size: int,
        target_value: Optional[float] = None,
        approach: ApproachType = 'exact',
        far0: float = 0.0027,
        alpha: float = 0.05,
        a_value: Optional[int] = None,
    ):
        super().__init__(data, sample_size)
        self.chart_type = "SignedRank"
        self.color = ACCENT
        self.approach = normalize_approach(approach)
        self.far0 = far0
        self.alpha = alpha
        self.significance_level = alpha
        self.a_value = a_value

        if sample_size < 2:
            raise ValueError(
                "Знако-ранговая карта требует n ≥ 2 "
                "(ранжирование внутри подгруппы невозможно при n = 1)."
            )

        if target_value is None:
            self.target_value = self._calculate_median()
        else:
            self.target_value = float(target_value)

        # Результаты
        self.subgroups: Optional[pd.DataFrame] = None
        self.control_limits: Optional[Dict] = None
        self.violations: List[Dict] = []
        self.comparison_table: Optional[pd.DataFrame] = None

        # Кэш распределения SR (по n)
        self._sr_dist_cache: Dict[int, Dict[int, float]] = {}

    # ------------------------------------------------------------------ #
    #  Вспомогательные расчёты
    # ------------------------------------------------------------------ #

    def _calculate_median(self) -> float:
        """Медиана всех наблюдений как целевое значение."""
        all_values = self.data.iloc[:, :self.sample_size].values.flatten()
        all_values = all_values[~np.isnan(all_values)]
        return float(np.median(all_values)) if len(all_values) > 0 else 0.0

    def _calculate_sr_for_row(self, row: pd.Series) -> Dict:
        """
        Расчёт знако-ранговой статистики SR_i для одной подгруппы.

        Делегирует общий расчёт в ``utils.statistics.signed_rank_details``
        (см. там шаги и ссылку на книгу), чтобы не дублировать логику между
        ``SignedRankChart`` и ``CusumSignedRankChart``.
        """
        return signed_rank_details(row.dropna().values, self.target_value)

    # ------------------------------------------------------------------ #
    #  Распределение SR (ДП-свёртка)
    # ------------------------------------------------------------------ #

    def _sr_distribution(self, n: int) -> Dict[int, float]:
        """
        Точное распределение SR в IC для подгруппы размера n.

        SR = Σ_{j=1}^{n} s_j · j,  где s_j ∈ {−1, +1} равновероятно.
        Распределение строится динамическим программированием (свёрткой):
        на каждом ранге j текущее распределение сумм сдвигается на ±j.
        Сложность O(n·S), S = n(n+1)/2, — это эквивалент перебора всех
        2^n знаковых наборов, но без явного перечисления (перебор при
        n ≳ 20 практически неосуществим).

        Возвращает словарь {значение_SR: вероятность}.
        """
        if n in self._sr_dist_cache:
            return self._sr_dist_cache[n]

        # dp[v] = число знаковых наборов с суммой v (свёртка ±j)
        dp: Dict[int, int] = {0: 1}
        for j in range(1, n + 1):
            nxt: Dict[int, int] = {}
            for v, c in dp.items():
                nxt[v + j] = nxt.get(v + j, 0) + c
                nxt[v - j] = nxt.get(v - j, 0) + c
            dp = nxt

        total = float(1 << n)
        dist = {int(v): c / total for v, c in dp.items() if c > 0}
        self._sr_dist_cache[n] = dist
        return dist

    def _p_sr_ge_a(self, n: int, a: int) -> float:
        """P(SR ≥ a) в IC."""
        dist = self._sr_distribution(n)
        return float(sum(p for v, p in dist.items() if v >= a))

    def _p_sr_le_a(self, n: int, a: int) -> float:
        """P(SR ≤ −a) в IC. По симметрии = P(SR ≥ a)."""
        return self._p_sr_ge_a(n, a)

    def _p_abs_sr_ge_a(self, n: int, a: int) -> float:
        """P(|SR| ≥ a) в IC = 2·P(SR ≥ a) (симметрия распределения)."""
        if a <= 0:
            return 1.0
        return min(2.0 * self._p_sr_ge_a(n, a), 1.0)

    # ------------------------------------------------------------------ #
    #  Расчёт константы a — три подхода
    # ------------------------------------------------------------------ #

    @classmethod
    def _calc_a_exact(cls, n: int, far0: float,
                      dist_func) -> Tuple[int, float]:
        """
        Подход 1: точный (консервативный; книга, стр. 198).

        a — наименьшее *достижимое* значение SR (той же чётности, что и
        S = n(n+1)/2) с P(SR ≥ a) ≤ FAR₀/2. Если вероятность недостижима
        (малое n), берётся максимум a = S — самые широкие границы и
        наименьший достижимый FAR (книга, пример 4.4: n = 4, a = S = 10).
        """
        S = n * (n + 1) // 2
        target = far0 / 2
        start = 1 if S % 2 == 1 else 2
        for a in range(start, S + 1, 2):
            p = dist_func(n, a)
            if p <= target:
                return a, 2.0 * p
        return S, 2.0 * dist_func(n, S)

    @classmethod
    def _calc_a_nearest(cls, n: int, alpha: float,
                        abs_dist_func) -> Tuple[int, float]:
        """Подход 3: ближайший к α."""
        S = n * (n + 1) // 2
        best_a, best_p, best_diff = 1, 1.0, float('inf')
        for a in range(1, S + 1):
            p = abs_dist_func(n, a)
            diff = abs(p - alpha)
            if diff < best_diff:
                best_diff, best_a, best_p = diff, a, p
        return best_a, best_p

    @classmethod
    def _calc_a_normal(cls, n: int, far0: float,
                       dist_func) -> Tuple[int, float]:
        """
        Подход 2: нормальная аппроксимация (симметричная граница ±a).

        S = n(n+1)/2. Граница берётся по нормальному приближению SR в IC:
        a — наименьшее достижимое значение (той же чётности, что и S), не
        меньше z_{1−FAR₀/2} · SD(SR), где SD(SR) = sqrt(n(n+1)(2n+1)/6).
        Риск делится симметрично: по z_{1−FAR₀/2}·SD на каждый хвост, суммарно
        номинальный двусторонний FAR₀. Асимптотический метод (ср.
        npSPC::Limits_asymptotical); достигнутый FAR не обязан быть ≤ FAR₀.
        """
        S = n * (n + 1) // 2
        z = stats.norm.ppf(1.0 - far0 / 2.0)
        sd = np.sqrt(n * (n + 1) * (2 * n + 1) / 6.0)
        a0 = int(np.ceil(z * sd))
        a = a0 if a0 % 2 == S % 2 else a0 + 1
        a = min(max(a, 1), S)
        return a, 2.0 * dist_func(n, a)

    def _calculate_a_value(self) -> int:
        """Расчёт a согласно выбранному подходу."""
        n = self.sample_size
        if self.approach == 'exact':
            a, _ = self._calc_a_exact(n, self.far0, self._p_sr_ge_a)
        elif self.approach == 'nearest':
            a, _ = self._calc_a_nearest(n, self.alpha, self._p_abs_sr_ge_a)
        elif self.approach == 'normal':
            a, _ = self._calc_a_normal(n, self.far0, self._p_sr_ge_a)
        else:
            raise ValueError(f"Неизвестный подход: {self.approach}")
        return max(int(a), 1)

    def compare_approaches(self) -> pd.DataFrame:
        """Сравнение трёх подходов для текущего n."""
        n = self.sample_size
        S = n * (n + 1) // 2
        rows = []

        for approach, label in self.APPROACH_LABELS.items():
            if approach == 'exact':
                a, far = self._calc_a_exact(n, self.far0, self._p_sr_ge_a)
                desc = f'P(SR ≥ a) ≤ FAR₀/2, FAR₀ = {self.far0}'
            elif approach == 'normal':
                a, far = self._calc_a_normal(n, self.far0, self._p_sr_ge_a)
                desc = f'нормальная аппроксимация z·SD(SR), FAR₀ = {self.far0}'
            elif approach == 'nearest':
                a, far = self._calc_a_nearest(n, self.alpha, self._p_abs_sr_ge_a)
                desc = f'|P(|SR| ≥ a) − α| → min, α = {self.alpha}'
            else:
                continue

            arl = 1.0 / far if far > 0 else np.inf
            mrl = int(np.ceil(np.log(0.5) / np.log(1 - far))) \
                if 0 < far < 1 else np.nan

            rows.append({
                'approach': approach,
                'label': label,
                'a': int(a),
                'FAR': far,
                'ARL_IC': arl,
                'MRL_IC': mrl,
                'SR_max': S,
                'description': desc,
            })

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------ #
    #  Основной расчёт
    # ------------------------------------------------------------------ #

    def calculate_limits(
        self,
        a_value: Optional[int] = None,
        approach: Optional[ApproachType] = None,
    ) -> Dict:
        """Расчёт контрольных границ и статистик по подгруппам."""
        if approach is not None:
            self.approach = normalize_approach(approach)

        subgroup_data = self.data.iloc[:, :self.sample_size]
        results = []
        for idx in range(len(subgroup_data)):
            row = subgroup_data.iloc[idx]
            result = self._calculate_sr_for_row(row)
            result['subgroup'] = idx + 1
            results.append(result)
        self.subgroups = pd.DataFrame(results)

        n = self.sample_size
        S = n * (n + 1) // 2

        if a_value is not None:
            self.a_value = int(a_value)
        elif self.a_value is None:
            self.a_value = self._calculate_a_value()

        a = self.a_value
        cl, ucl, lcl = 0, a, -a

        far = self._p_abs_sr_ge_a(n, a)
        arl = 1.0 / far if far > 0 else np.inf
        mrl = int(np.ceil(np.log(0.5) / np.log(1 - far))) \
            if 0 < far < 1 else np.nan

        self.control_limits = {
            'CL': cl, 'UCL': ucl, 'LCL': lcl,
            'a_value': a,
            'target_value': self.target_value,
            'n': n, 'SR_max': S,
            'approach': self.approach,
            'far0': self.far0, 'alpha': self.alpha,
            'FAR': far, 'ARL_IC': arl, 'MRL_IC': mrl,
        }

        self.comparison_table = self.compare_approaches()
        self._find_violations()
        return self.control_limits

    def _find_violations(self):
        """
        Правило сигнала: |SR_i| ≥ a.

        Chakraborti & Graham (2019), § 4.2.1.2.1, ур. 4.6, стр. 198.
        """
        self.violations = []
        if self.subgroups is None or self.control_limits is None:
            return
        a = self.control_limits['a_value']
        for _, row in self.subgroups.iterrows():
            if row['sr'] >= a or row['sr'] <= -a:
                self.violations.append({
                    'subgroup': int(row['subgroup']),
                    'value': float(row['sr']),
                    'rule': f'|SR| ≥ {a}',
                })

    # ------------------------------------------------------------------ #
    #  Визуализация
    # ------------------------------------------------------------------ #

    def plot(
        self,
        figsize: Tuple[int, int] = (13, 7),
        save_path: Optional[str] = None,
        title: Optional[str] = None,
        show_values: bool = True,
        show_zones: bool = False,
        fill_zones: bool = False,
        value_offset: Tuple[float, float] = (0, 4.0),
    ) -> Tuple[plt.Figure, plt.Axes]:
        """Построение знако-ранговой карты Шухарта.

        Оформление едино с CUSUM-картами (``CusumSignedRankChart.plot``):
        линия с маркерами, тот же запас по осям и постановка подписей.
        ``show_zones`` по умолчанию выключено (как в CUSUM-картах); при
        включении σ = a/3 — контрольная граница a соответствует 3σ,
        зоны A (2σ…3σ), B (1σ…2σ), C (0…1σ).

        ``value_offset`` задаёт смещение подписи значения от точки **в
        типографских пунктах** (не в единицах данных).
        """
        if self.control_limits is None:
            self.calculate_limits()

        fig, ax = plt.subplots(figsize=figsize)

        x = self.subgroups['subgroup'].values
        y = self.subgroups['sr'].values
        a = self.control_limits['a_value']
        S = self.control_limits['SR_max']

        zone_alpha = 0.5 if fill_zones else 0.0

        if show_zones and a >= 3:
            z1, z2 = a / 3, 2 * a / 3
            if fill_zones:
                for lo, hi in ((z2, a), (-a, -z2), (z1, z2),
                               (-z2, -z1), (-z1, z1)):
                    ax.axhspan(lo, hi, color=ZONE_FILL, alpha=zone_alpha,
                               zorder=0)
            for level in (z1, z2, -z1, -z2):
                ax.axhline(y=level, color=ZONE_LINE, linestyle=':',
                           linewidth=1.0, zorder=1)
            x_right = x.max() + 0.4
            for level, label in (
                ((z2 + a) / 2, math_text('Зона A') + r' ($2\sigma\ldots3\sigma$)'),
                ((z1 + z2) / 2, math_text('Зона B') + r' ($1\sigma\ldots2\sigma$)'),
                (0.5 * z1, math_text('Зона C') + r' ($0\ldots1\sigma$)'),
                (-(z1 + z2) / 2, math_text('Зона B') + r' ($1\sigma\ldots2\sigma$)'),
                (-(z2 + a) / 2, math_text('Зона A') + r' ($2\sigma\ldots3\sigma$)'),
            ):
                ax.text(x_right, level, label, color=INK, fontsize=9,
                        va='center', ha='left')

        is_violation = (y >= a) | (y <= -a)

        ax.plot(x, y, '-o', color=self.color, linewidth=1.2,
                markersize=DATA_MARKER_SIZE, zorder=3, label='$SR_i$')
        if is_violation.any():
            ax.scatter(x[is_violation], y[is_violation],
                       s=SIGNAL_MARKER_SIZE, color=ALERT, zorder=4,
                       label=f'{math_text("Нарушения")} ({is_violation.sum()})')

        hline(ax, 0, "center", label=r'$\mathrm{CL} = 0$')
        hline(ax, a, "limit", label=rf'$\mathrm{{UCL}} = +{a}$')
        hline(ax, -a, "limit", label=rf'$\mathrm{{LCL}} = -{a}$')

        # Подписи значений: над точкой при y ≥ 0, под ней иначе (как в CUSUM).
        if show_values:
            annotate_values(ax, x, y, offset=value_offset, fmt="{:.1f}")

        ax.set_xlabel(r'$t$ (' + math_text('номер подгруппы') + ')')
        ax.set_ylabel(
            r'$SR_t = \sum_j \mathrm{sign}(X_{tj}-\mu_0)\,R_{tj}$'
        )
        ax.set_xticks(x)

        # Правый отступ — под подписи зон, только когда они показаны.
        right_pad = 3.2 if (show_zones and a >= 3) else 0.5
        ax.set_xlim(x.min() - 0.5, x.max() + right_pad)

        # Запас сверху, как в CUSUM-картах (блок данных не закрывает точки).
        y_low = min(float(y.min()), -a)
        y_high = max(float(y.max()), a)
        span = max(y_high - y_low, 1.0)
        ax.set_ylim(y_low - 0.05 * span, y_high + 0.25 * span)

        approach_label = self.APPROACH_PLOT_LABELS.get(
            self.approach, self.approach)
        if title is None:
            title = (math_text('Знако-ранговая карта Шухарта') + ' — '
                     rf'$n={self.sample_size}$, $a={a}$, '
                     + math_text('подход:') + ' ' + math_text(approach_label))
        ax.set_title(title)

        # --- Информационный блок (в стиле легенды, правый верхний угол) ---
        info_lines = [
            rf"$\mu_0 = {self.target_value:.4f}$    "
            rf"$n = {self.sample_size}$, $m = {len(self.subgroups)}$",
            rf"$a = {a}$   ($\sigma = a/3$, $\max|SR| = {S}$)",
            rf"$\mathrm{{FAR}} = {self.control_limits['FAR']:.4f}$   "
            rf"$\mathrm{{ARL}} = {self.control_limits['ARL_IC']:.1f}$   "
            rf"$\mathrm{{MRL}} = {self.control_limits['MRL_IC']}$",
        ]
        data_legend(ax, info_lines)

        handles, labels = ax.get_legend_handles_labels()
        if show_zones and a >= 3:
            zone_handles = [
                Line2D([0], [0], color=ZONE_LINE, linestyle=':',
                       linewidth=1.5,
                       label=math_text('Границы зон') + r' $\mathrm{A/B}$'),
            ]
            handles += zone_handles
            labels += [h.get_label() for h in zone_handles]

        ax.legend(handles, labels, loc='best',
                  fontsize=8, ncol=2, labelspacing=0.25,
                  handlelength=1.4, handletextpad=0.4,
                  borderpad=0.3, borderaxespad=0.4, columnspacing=1.0)
        ax.grid(alpha=0.25, linestyle=':')

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f'График сохранён: {save_path}')
        return fig, ax

    def plot_comparison(self, n_range=None, figsize=(14, 9)):
        """Сравнение трёх подходов к расчёту a на диапазоне n."""
        if n_range is None:
            n_range = np.arange(2, 21)
        n_range = np.asarray(n_range)

        cons_a, cons_far = [], []
        near_a, near_far = [], []
        sym_a, sym_far = [], []

        for n in n_range:
            a_c, f_c = self._calc_a_exact(n, self.far0, self._p_sr_ge_a)
            a_n, f_n = self._calc_a_nearest(n, self.alpha, self._p_abs_sr_ge_a)
            a_s, f_s = self._calc_a_normal(n, self.far0, self._p_sr_ge_a)
            cons_a.append(a_c); cons_far.append(f_c)
            near_a.append(a_n); near_far.append(f_n)
            sym_a.append(a_s);   sym_far.append(f_s)

        fig, axes = plt.subplots(1, 2, figsize=figsize)

        colors = (PALETTE[0], PALETTE[3], PALETTE[2])

        axes[0].plot(n_range, cons_a, 'o-', color=colors[0],
                     label=rf'Точный ($FAR_0 = {self.far0}$)')
        axes[0].plot(n_range, near_a, 's--', color=colors[1],
                     label=rf'Ближайший ($\alpha = {self.alpha}$)')
        axes[0].plot(n_range, sym_a, '^:', color=colors[2],
                     label='Нормальная аппроксимация')
        axes[0].set_xlabel('n (размер подгруппы)')
        axes[0].set_ylabel('Константа a')
        axes[0].set_title('Значения a для трёх подходов')
        axes[0].legend()
        axes[0].grid(alpha=0.3)

        axes[1].plot(n_range, cons_far, 'o-', color=colors[0],
                     label='Точный')
        axes[1].plot(n_range, near_far, 's--', color=colors[1],
                     label='Ближайший')
        axes[1].plot(n_range, sym_far, '^:', color=colors[2],
                     label='Нормальная аппроксимация')
        axes[1].axhline(self.far0, color=colors[0], linestyle=':',
                        alpha=0.6, label=rf'$FAR_0 = {self.far0}$')
        axes[1].axhline(self.alpha, color=colors[1], linestyle=':',
                        alpha=0.6, label=rf'$\alpha = {self.alpha}$')
        axes[1].set_xlabel('n (размер подгруппы)')
        axes[1].set_ylabel('Достигнутый FAR')
        axes[1].set_title('Достигнутые FAR')
        axes[1].set_yscale('log')
        axes[1].legend()
        axes[1].grid(alpha=0.3, which='both')

        plt.tight_layout()
        return fig, axes

    # ------------------------------------------------------------------ #
    #  Аналитические результаты
    # ------------------------------------------------------------------ #

    def calculate_signed_rank_test(self) -> Dict:
        """
        Знаково-ранговый тест Уилкоксона для проверки гипотезы
        о медиане μ₀ по всем наблюдениям.
        """
        if self.subgroups is None:
            self.calculate_limits()

        all_values = self.data.iloc[:, :self.sample_size].values.flatten()
        all_values = all_values[~np.isnan(all_values)]
        deviations = all_values - self.target_value
        nonzero = deviations[deviations != 0]

        if len(nonzero) < 2:
            return {
                'n_total': len(nonzero),
                'T_plus': 0.0,
                'SR_total': 0.0,
                'p_value': 1.0,
                'z_statistic': 0.0,
                'target_value': self.target_value,
                'significant': False,
            }

        ranks = stats.rankdata(np.abs(nonzero), method='average')
        signs = np.sign(nonzero)
        T_plus = float(np.sum(ranks[signs > 0]))
        SR_total = float(np.sum(signs * ranks))

        n_tot = len(nonzero)
        mu_T = n_tot * (n_tot + 1) / 4
        sd_T = np.sqrt(n_tot * (n_tot + 1) * (2 * n_tot + 1) / 24)

        if sd_T > 0:
            z_stat = (T_plus - mu_T) / sd_T
            p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
        else:
            z_stat, p_value = 0.0, 1.0

        return {
            'n_total': n_tot,
            'T_plus': T_plus,
            'SR_total': SR_total,
            'p_value': float(min(p_value, 1.0)),
            'z_statistic': float(z_stat),
            'target_value': self.target_value,
            'significant': p_value < self.significance_level,
        }

    def get_sr_table(self) -> pd.DataFrame:
        """Таблица со значениями SR по подгруппам."""
        if self.subgroups is None:
            self.calculate_limits()
        return self.subgroups.copy()

    def get_signed_rank_matrix(self) -> pd.DataFrame:
        """Матрица знаковых рангов (φ(X−μ₀)·rank(|X−μ₀|))."""
        if self.subgroups is None:
            self.calculate_limits()
        rows = []
        for idx in range(len(self.data)):
            row = self.data.iloc[idx, :self.sample_size].dropna().values
            dev = row - self.target_value
            mask = dev != 0
            dev_nz = dev[mask]
            if len(dev_nz) == 0:
                rows.append(np.zeros(self.sample_size, dtype=int))
                continue
            ranks = stats.rankdata(np.abs(dev_nz), method='average')
            signed = np.sign(dev_nz) * ranks
            # Возвращаем выровненный по исходной длине вектор
            out = np.zeros(len(row), dtype=float)
            out[mask] = signed
            # Дополняем нулями, если n_used < sample_size
            if len(out) < self.sample_size:
                out = np.concatenate([out, np.zeros(self.sample_size - len(out))])
            rows.append(out)
        columns = [f'x{i+1}' for i in range(self.sample_size)]
        df = pd.DataFrame(rows, columns=columns)
        df.insert(0, 'subgroup', range(1, len(df) + 1))
        return df

    def get_summary(self) -> Dict:
        """Сводная информация о карте."""
        if self.control_limits is None:
            self.calculate_limits()
        return {
            'chart_type': 'SignedRank',
            'approach': self.approach,
            'target_value': self.target_value,
            'n': self.sample_size,
            'a': self.control_limits['a_value'],
            'UCL': self.control_limits['UCL'],
            'LCL': self.control_limits['LCL'],
            'CL': self.control_limits['CL'],
            'SR_max': self.control_limits['SR_max'],
            'FAR': self.control_limits['FAR'],
            'ARL_IC': self.control_limits['ARL_IC'],
            'MRL_IC': self.control_limits['MRL_IC'],
            'total_subgroups': len(self.subgroups),
            'total_violations': len(self.violations),
            'mean_sr': float(self.subgroups['sr'].mean()),
            'violations': self.violations,
        }