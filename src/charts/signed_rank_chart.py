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
    Не имеет замкнутой формы; получается точным перебором
    всех 2^n знаковых комбинаций рангов 1..n.

Контрольные границы:
    LCL = −a,  CL = 0,  UCL = +a,  0 < a ≤ n(n+1)/2

Правило сигнала:
    процесс OOC, если |SR_i| ≥ a

Длина серии в Case K:
    N ~ GEO(FAR),  ARL = 1/FAR,
    MRL = ⌈ln(0.5) / ln(1−FAR)⌉

Три подхода к расчёту константы a:
----------------------------------
1. **Консервативный** (по книге, стр. 198):
       a = наименьшее целое с P(SR ≥ a) ≤ FAR₀/2
2. **«Ближайший»** (обучение / сравнение):
       a = argmin_a |P(|SR| ≥ a) − α|
3. **Симметричный квантильный**:
       a — наименьшее целое, сохраняющее симметрию контрольных границ;
       для нечётного числа возможных значений SR — нечётное a.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from typing import Dict, Optional, Tuple, List, Literal
from scipy import stats

try:
    from src.base.base_chart import BaseControlChart
except ImportError:
    class BaseControlChart:
        def __init__(self, data, sample_size, coefficients_file=None):
            self.data = data
            self.sample_size = sample_size
            self.coefficients_file = coefficients_file


ApproachType = Literal['conservative', 'nearest', 'symmetric']


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
    approach : {'conservative', 'nearest', 'symmetric'}, default='conservative'
        Подход к расчёту константы a.
    far0 : float, default=0.0027
        Номинальный FAR для консервативного и симметричного подходов.
    alpha : float, default=0.05
        Уровень значимости для «ближайшего» подхода.
    c_value : int, optional
        Явно заданное значение a. Если задано — подходы игнорируются.
    coefficients_file : str, optional
        Путь к файлу с коэффициентами (для совместимости).
    """

    APPROACH_LABELS = {
        'conservative': 'Консервативный (FAR₀)',
        'nearest': 'Ближайший (α)',
        'symmetric': 'Симметричный квантильный',
    }

    def __init__(
        self,
        data: pd.DataFrame,
        sample_size: int,
        target_value: Optional[float] = None,
        approach: ApproachType = 'conservative',
        far0: float = 0.0027,
        alpha: float = 0.05,
        c_value: Optional[int] = None,
        coefficients_file: Optional[str] = None,
    ):
        super().__init__(data, sample_size, coefficients_file)
        self.chart_type = "SignedRank"
        self.color = '#6A4C93'
        self.approach = approach
        self.far0 = far0
        self.alpha = alpha
        self.significance_level = alpha
        self.c_value = c_value

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

        Шаги:
            1. Отбрасываем NaN.
            2. Вычисляем отклонения d_j = x_j − μ₀.
            3. Отбрасываем нули (теоретически их быть не должно).
            4. Ранжируем |d_j| (метод 'average' — ties).
            5. SR = Σ sign(d_j) · rank(|d_j|).
        """
        values = row.dropna().values
        n = len(values)
        if n == 0:
            return {
                'n_used': 0, 'positive': 0, 'negative': 0,
                'zero': 0, 'sr': 0, 'sum_pos_ranks': 0,
                'sum_neg_ranks': 0, 'T_plus': 0,
            }

        deviations = values - self.target_value
        # Теоретически нулей быть не должно (непрерывное распределение);
        # на практике при округлении возможны — исключаем их из ранжирования.
        mask_nonzero = deviations != 0
        deviations_nz = deviations[mask_nonzero]

        n_eff = len(deviations_nz)
        if n_eff == 0:
            return {
                'n_used': 0, 'positive': 0, 'negative': 0,
                'zero': n, 'sr': 0, 'sum_pos_ranks': 0,
                'sum_neg_ranks': 0, 'T_plus': 0,
            }

        abs_dev = np.abs(deviations_nz)
        # Ранги через 'average' — корректно при возможных ties
        ranks = stats.rankdata(abs_dev, method='average')

        signs = np.sign(deviations_nz)
        signed_ranks = signs * ranks

        sr = float(np.sum(signed_ranks))
        sum_pos = float(np.sum(ranks[signs > 0])) if np.any(signs > 0) else 0.0
        sum_neg = float(np.sum(ranks[signs < 0])) if np.any(signs < 0) else 0.0
        T_plus = sum_pos  # классическая статистика Уилкоксона

        return {
            'n_used': n_eff,
            'positive': int(np.sum(signs > 0)),
            'negative': int(np.sum(signs < 0)),
            'zero': int(n - n_eff),
            'sr': sr,
            'sum_pos_ranks': sum_pos,
            'sum_neg_ranks': sum_neg,
            'T_plus': T_plus,
        }

    # ------------------------------------------------------------------ #
    #  Распределение SR (точный перебор)
    # ------------------------------------------------------------------ #

    def _sr_distribution(self, n: int) -> Dict[int, float]:
        """
        Точное распределение SR в IC для подгруппы размера n.

        SR = Σ_{j=1}^{n} s_j · j,  где s_j ∈ {−1, +1} равновероятно.
        Перебираем все 2^n знаковых комбинаций.

        Возвращает словарь {значение_SR: вероятность}.
        """
        if n in self._sr_dist_cache:
            return self._sr_dist_cache[n]

        ranks = np.arange(1, n + 1, dtype=np.int64)
        # Все 2^n векторов знаков
        n_states = 1 << n
        signs = np.empty((n_states, n), dtype=np.int64)
        for k in range(n_states):
            for j in range(n):
                signs[k, j] = 1 if (k >> j) & 1 else -1
        sr_values = signs @ ranks  # shape (2^n,)
        counts = np.bincount((sr_values + ranks.sum()).astype(int),
                             minlength=2 * ranks.sum() + 1)
        probs = counts / counts.sum()
        # Значения SR = −S..+S (S = n(n+1)/2), с шагом 2
        S = int(ranks.sum())
        dist = {int(v): float(probs[v + S])
                for v in range(-S, S + 1, 2) if probs[v + S] > 0}
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
    def _calc_a_conservative(cls, n: int, far0: float,
                             dist_func) -> Tuple[int, float]:
        """
        Подход 1: консервативный (книга, стр. 198).
        a — наименьшее целое с P(SR ≥ a) ≤ FAR₀/2.

        Перебираем a в диапазоне [1, S], где S = n(n+1)/2.
        """
        S = n * (n + 1) // 2
        target = far0 / 2
        # Идём от S вниз, чтобы найти наименьшее a, удовлетворяющее условию
        best_a = 1
        best_p = 1.0
        for a in range(1, S + 1):
            p = dist_func(n, a)
            if p <= target:
                best_a = a
                best_p = 2.0 * p  # двусторонний FAR
                break
        return best_a, best_p

    @classmethod
    def _calc_a_nearest(cls, n: int, alpha: float,
                        abs_dist_func) -> Tuple[int, float]:
        """Подход 2: ближайший к α."""
        S = n * (n + 1) // 2
        best_a, best_p, best_diff = 1, 1.0, float('inf')
        for a in range(1, S + 1):
            p = abs_dist_func(n, a)
            diff = abs(p - alpha)
            if diff < best_diff:
                best_diff, best_a, best_p = diff, a, p
        return best_a, best_p

    @classmethod
    def _calc_a_symmetric(cls, n: int, far0: float,
                          dist_func) -> Tuple[int, float]:
        """
        Подход 3: симметричный квантильный.

        S = n(n+1)/2. Возможные значения SR имеют чётность, равную
        чётности S. Поэтому для сохранения симметрии контрольных
        границ берём a той же чётности, что и S.
        """
        S = n * (n + 1) // 2
        target = far0 / 2
        # Начинаем с S (или S−1, чтобы совпасть по чётности)
        start = S if (S % 2 == 0) else S - 1
        step = 2
        for a in range(start, 0, -step):
            p = dist_func(n, a)
            if p <= target:
                return a, 2.0 * p
        return 1, 2.0 * dist_func(n, 1)

    def _calculate_c_value(self) -> int:
        """Расчёт a согласно выбранному подходу."""
        n = self.sample_size
        if self.approach == 'conservative':
            a, _ = self._calc_a_conservative(n, self.far0, self._p_sr_ge_a)
        elif self.approach == 'nearest':
            a, _ = self._calc_a_nearest(n, self.alpha, self._p_abs_sr_ge_a)
        elif self.approach == 'symmetric':
            a, _ = self._calc_a_symmetric(n, self.far0, self._p_sr_ge_a)
        else:
            raise ValueError(f"Неизвестный подход: {self.approach}")
        return max(int(a), 1)

    def compare_approaches(self) -> pd.DataFrame:
        """Сравнение трёх подходов для текущего n."""
        n = self.sample_size
        S = n * (n + 1) // 2
        rows = []

        for approach, label in self.APPROACH_LABELS.items():
            if approach == 'conservative':
                a, far = self._calc_a_conservative(n, self.far0, self._p_sr_ge_a)
                desc = f'P(SR ≥ a) ≤ FAR₀/2, FAR₀ = {self.far0}'
            elif approach == 'nearest':
                a, far = self._calc_a_nearest(n, self.alpha, self._p_abs_sr_ge_a)
                desc = f'|P(|SR| ≥ a) − α| → min, α = {self.alpha}'
            elif approach == 'symmetric':
                a, far = self._calc_a_symmetric(n, self.far0, self._p_sr_ge_a)
                desc = 'Наименьшее a с сохранением симметрии (чётность S)'
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
        c_value: Optional[int] = None,
        approach: Optional[ApproachType] = None,
    ) -> Dict:
        """Расчёт контрольных границ и статистик по подгруппам."""
        if approach is not None:
            self.approach = approach

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

        if c_value is not None:
            self.c_value = int(c_value)
        elif self.c_value is None:
            self.c_value = self._calculate_c_value()

        a = self.c_value
        cl, ucl, lcl = 0, a, -a

        far = self._p_abs_sr_ge_a(n, a)
        arl = 1.0 / far if far > 0 else np.inf
        mrl = int(np.ceil(np.log(0.5) / np.log(1 - far))) \
            if 0 < far < 1 else np.nan

        self.control_limits = {
            'CL': cl, 'UCL': ucl, 'LCL': lcl,
            'c_value': a,
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
        a = self.control_limits['c_value']
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
        show_zones: bool = True,
        fill_zones: bool = False,
        value_offset: Tuple[float, float] = (0, 0.6),
    ) -> Tuple[plt.Figure, plt.Axes]:
        """Построение знако-ранговой карты Шухарта."""
        if self.control_limits is None:
            self.calculate_limits()

        fig, ax = plt.subplots(figsize=figsize)

        x = self.subgroups['subgroup'].values
        y = self.subgroups['sr'].values
        a = self.control_limits['c_value']
        S = self.control_limits['SR_max']

        zone_colors = {'A': 'red', 'B': 'gold', 'C': 'green'}
        zone_alpha = 0.10 if fill_zones else 0.0

        if show_zones and a >= 3:
            z1, z2 = a / 3, 2 * a / 3
            if fill_zones:
                ax.axhspan(z2, a, color=zone_colors['A'], alpha=zone_alpha, zorder=0)
                ax.axhspan(-a, -z2, color=zone_colors['A'], alpha=zone_alpha, zorder=0)
                ax.axhspan(z1, z2, color=zone_colors['B'], alpha=zone_alpha, zorder=0)
                ax.axhspan(-z2, -z1, color=zone_colors['B'], alpha=zone_alpha, zorder=0)
                ax.axhspan(-z1, z1, color=zone_colors['C'], alpha=zone_alpha, zorder=0)
            for level in (z1, z2, -z1, -z2):
                ax.axhline(
                    y=level,
                    color=zone_colors['B'] if abs(level) == z1 else zone_colors['A'],
                    linestyle=':', linewidth=1.0, alpha=0.8, zorder=1,
                )
            x_right = x.max() + 0.4
            ax.text(x_right, (z2 + a) / 2, 'Zone A', color=zone_colors['A'],
                    fontsize=9, va='center', ha='left', fontweight='bold')
            ax.text(x_right, (z1 + z2) / 2, 'Zone B', color='darkgoldenrod',
                    fontsize=9, va='center', ha='left', fontweight='bold')
            ax.text(x_right, 0, 'Zone C', color=zone_colors['C'],
                    fontsize=9, va='center', ha='left', fontweight='bold')
            ax.text(x_right, -(z1 + z2) / 2, 'Zone B', color='darkgoldenrod',
                    fontsize=9, va='center', ha='left', fontweight='bold')
            ax.text(x_right, -(z2 + a) / 2, 'Zone A', color=zone_colors['A'],
                    fontsize=9, va='center', ha='left', fontweight='bold')

        is_violation = (y >= a) | (y <= -a)

        ax.scatter(x[~is_violation], y[~is_violation],
                   s=60, color=self.color, zorder=3,
                   edgecolors='white', linewidths=1, label='$SR_i$')
        if is_violation.any():
            ax.scatter(x[is_violation], y[is_violation],
                       s=60, color='crimson', zorder=3,
                       edgecolors='white', linewidths=1,
                       label=f'Нарушения ({is_violation.sum()})')

        ax.plot(x, y, '-', color=self.color, linewidth=1.0, alpha=0.5, zorder=2)

        ax.axhline(0, color='green', linestyle='-', linewidth=1.5,
                   label='CL = 0', zorder=1)
        ax.axhline(a, color='red', linestyle='--', linewidth=1.5,
                   label=f'UCL = +{a}', zorder=1)
        ax.axhline(-a, color='red', linestyle='--', linewidth=1.5,
                   label=f'LCL = −{a}', zorder=1)

        if show_values:
            for xi, yi, viol in zip(x, y, is_violation):
                color = 'darkred' if viol else 'black'
                ax.annotate(
                    f'{yi:.0f}',
                    xy=(xi, yi),
                    xytext=(xi + value_offset[0], yi + value_offset[1]),
                    fontsize=9, color=color, ha='center', va='bottom',
                    bbox=dict(boxstyle='round,pad=0.15', fc='white',
                              ec='none', alpha=0.75),
                )

        ax.set_xlabel('Номер подгруппы', fontsize=12)
        ax.set_ylabel('SR = Σ sign(X−μ₀)·rank(|X−μ₀|)', fontsize=12)
        ax.set_xticks(x)
        ax.set_xlim(x.min() - 0.5, x.max() + 1.8)
        y_margin = max(2, a * 0.3)
        ax.set_ylim(-(a + y_margin), a + y_margin)

        approach_label = self.APPROACH_LABELS.get(self.approach, self.approach)
        if title is None:
            title = (f'Знако-ранговая карта Шухарта — n={self.sample_size}, '
                     f'a={a}, подход: {approach_label}')
        ax.set_title(title, fontsize=13, fontweight='bold')

        info = (
            f"μ₀ = {self.target_value:.4f}\n"
            f"n = {self.sample_size},  m = {len(self.subgroups)}\n"
            f"a = {a}  (max |SR| = {S})\n"
            f"FAR = {self.control_limits['FAR']:.4f}\n"
            f"ARL_IC = {self.control_limits['ARL_IC']:.1f}\n"
            f"MRL_IC = {self.control_limits['MRL_IC']}"
        )
        ax.text(0.985, 0.98, info, transform=ax.transAxes,
                fontsize=9, va='top', ha='right',
                bbox=dict(boxstyle='round,pad=0.5', fc='white',
                          ec='gray', alpha=0.9))

        handles, labels = ax.get_legend_handles_labels()
        if show_zones and a >= 3:
            zone_handles = [
                Line2D([0], [0], color=zone_colors['A'], linestyle=':',
                       linewidth=1.5, label='Zone A (границы)'),
                Line2D([0], [0], color='darkgoldenrod', linestyle=':',
                       linewidth=1.5, label='Zone B (границы)'),
            ]
            handles += zone_handles
            labels += [h.get_label() for h in zone_handles]

        ax.legend(handles, labels, loc='upper left', fontsize=9, ncol=2)
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
            a_c, f_c = self._calc_a_conservative(n, self.far0, self._p_sr_ge_a)
            a_n, f_n = self._calc_a_nearest(n, self.alpha, self._p_abs_sr_ge_a)
            a_s, f_s = self._calc_a_symmetric(n, self.far0, self._p_sr_ge_a)
            cons_a.append(a_c); cons_far.append(f_c)
            near_a.append(a_n); near_far.append(f_n)
            sym_a.append(a_s);   sym_far.append(f_s)

        fig, axes = plt.subplots(1, 2, figsize=figsize)

        axes[0].plot(n_range, cons_a, 'o-', color='steelblue',
                     label=f'Консервативный (FAR₀ = {self.far0})')
        axes[0].plot(n_range, near_a, 's--', color='crimson',
                     label=f'Ближайший (α = {self.alpha})')
        axes[0].plot(n_range, sym_a, '^:', color='forestgreen',
                     label='Симметричный квантильный')
        axes[0].set_xlabel('n (размер подгруппы)', fontsize=11)
        axes[0].set_ylabel('Константа a', fontsize=11)
        axes[0].set_title('Значения a для трёх подходов', fontsize=12,
                          fontweight='bold')
        axes[0].legend(fontsize=9)
        axes[0].grid(alpha=0.3)

        axes[1].plot(n_range, cons_far, 'o-', color='steelblue',
                     label='Консервативный')
        axes[1].plot(n_range, near_far, 's--', color='crimson',
                     label='Ближайший')
        axes[1].plot(n_range, sym_far, '^:', color='forestgreen',
                     label='Симметричный')
        axes[1].axhline(self.far0, color='steelblue', linestyle=':',
                        alpha=0.6, label=f'FAR₀ = {self.far0}')
        axes[1].axhline(self.alpha, color='crimson', linestyle=':',
                        alpha=0.6, label=f'α = {self.alpha}')
        axes[1].set_xlabel('n (размер подгруппы)', fontsize=11)
        axes[1].set_ylabel('Достигнутый FAR', fontsize=11)
        axes[1].set_title('Достигнутые FAR', fontsize=12, fontweight='bold')
        axes[1].set_yscale('log')
        axes[1].legend(fontsize=9)
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
            'a': self.control_limits['c_value'],
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