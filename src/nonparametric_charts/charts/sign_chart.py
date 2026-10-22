"""
Карта знаковых сумм Шухарта (Shewhart Sign Chart)

Непараметрическая контрольная карта, основанная на знаковом тесте.
Использует знаки отклонений наблюдений от целевого значения μ₀.

Теория (Chakraborti & Graham, 2019, Section 4.2.1.1.1, стр. 189–196):
----------------------------------------------------------------------
Для каждой подгруппы размера n вычисляется знаковая статистика:

    SN_i = n_i⁺ − n_i⁻ = Σ_{j=1}^{n} φ(X_ij − μ₀) = 2T_i − n

где:
    n_i⁺  — число наблюдений > μ₀
    n_i⁻  — число наблюдений < μ₀
    T_i = n_i⁺  — классическая знаковая статистика, T_i ~ BIN(n, 0.5) в IC

Контрольные границы:
    LCL = −a,  CL = 0,  UCL = +a

Правило сигнала:
    процесс OOC, если |SN_i| ≥ a

Длина серии в Case K:
    N ~ GEO(FAR),  ARL = 1/FAR,  MRL = ⌈ln(0.5) / ln(1−FAR)⌉

Три подхода к расчёту константы a:
----------------------------------
1. **Точный (консервативный)** (по книге, стр. 191), id `exact`:
       a = наименьшее достижимое (той же чётности, что и n)
       с P(SN ≥ a) ≤ FAR₀/2; гарантирует FAR ≤ FAR₀.
       Если вероятность недостижима (малое n) — a = n.

2. **Нормальная аппроксимация** (id `normal`):
       a = наименьшее достижимое значение (той же чётности, что и n),
       не меньше z_{1−FAR₀/2} · SD(SN), где SD(SN) = sqrt(n);
       асимптотическая граница (ср. npSPC::Limits_asymptotical).

3. **«Ближайший»** (id `nearest`, обучение / сравнение):
       a = argmin_a |P(|SN| ≥ a) − α|
       Достигнутый FAR может превышать α.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from typing import Dict, Optional, Tuple, List, Literal
from scipy import stats
from scipy.stats import binom
from scipy.special import comb

try:
    from nonparametric_charts.base.base_chart import BaseControlChart
except ImportError:
    # Fallback: минимальный базовый класс, если пакет недоступен
    class BaseControlChart:
        def __init__(self, data, sample_size):
            self.data = data
            self.sample_size = sample_size

try:
    from nonparametric_charts.utils.statistics import sign_counts
except ImportError:  # fallback: локальная реализация
    def sign_counts(values, target_value):
        arr = np.asarray(values, dtype=float).ravel()
        arr = arr[~np.isnan(arr)]
        positive = int(np.sum(arr > target_value))
        negative = int(np.sum(arr < target_value))
        zero = int(arr.size - positive - negative)
        return positive, negative, zero

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


class SignChart(BaseControlChart):
    """
    Карта знаковых сумм (Shewhart Sign Chart).

    Непараметрическая карта для контроля центра процесса.

    Parameters
    ----------
    data : pd.DataFrame
        Данные (m подгрупп × n наблюдений).
    sample_size : int
        Размер подгруппы n.
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
        self.chart_type = "Sign"
        self.color = ACCENT
        self.approach = normalize_approach(approach)
        self.far0 = far0
        self.alpha = alpha
        self.significance_level = alpha
        self.a_value = a_value

        if target_value is None:
            self.target_value = self._calculate_median()
        else:
            self.target_value = float(target_value)
        
        # Результаты расчёта (заполняются в calculate_limits)
        self.subgroups: Optional[pd.DataFrame] = None
        self.control_limits: Optional[Dict] = None
        self.violations: List[Dict] = []
        self.comparison_table: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------ #
    #  Вспомогательные расчёты
    # ------------------------------------------------------------------ #

    def _calculate_median(self) -> float:
        """Медиана всех наблюдений как целевое значение."""
        all_values = self.data.iloc[:, :self.sample_size].values.flatten()
        all_values = all_values[~np.isnan(all_values)]
        return float(np.median(all_values)) if len(all_values) > 0 else 0.0

    def _calculate_signs_for_row(self, row: pd.Series) -> Dict:
        """Расчёт статистик знаков для одной подгруппы."""
        values = row.dropna().values
        if len(values) == 0:
            return {'positive': 0, 'negative': 0, 'zero': 0, 'sn': 0}

        positive, negative, zero = sign_counts(values, self.target_value)

        return {
            'positive': positive,
            'negative': negative,
            'zero': zero,
            'sn': positive - negative,
        }

    # ------------------------------------------------------------------ #
    #  Расчёт вероятностей и константы a
    # ------------------------------------------------------------------ #

    @staticmethod
    def _p_sn_ge_a(n: int, a: int) -> float:
        """
        P(SN ≥ a) в IC-состоянии.

        SN = 2T − n, T ~ BIN(n, 0.5).
        SN ≥ a  ⇔  T ≥ ceil((n + a)/2).
        """
        if a > n:
            return 0.0
        if a <= -n:
            return 1.0
        t_threshold = int(np.ceil((n + a) / 2))
        if t_threshold > n:
            return 0.0
        if t_threshold < 0:
            return 1.0
        return float(np.sum([comb(n, m) * (0.5 ** n) for m in range(t_threshold, n + 1)]))

    @classmethod
    def _p_abs_sn_ge_a(cls, n: int, a: int) -> float:
        """P(|SN| ≥ a) в IC-состоянии. По симметрии: 2·P(SN ≥ a)."""
        if a <= 0:
            return 1.0
        return min(2.0 * cls._p_sn_ge_a(n, a), 1.0)

    @classmethod
    def _calc_a_exact(cls, n: int, far0: float) -> Tuple[int, float]:
        """
        Подход 1: точный (консервативный; книга, стр. 191–192).

        a — наименьшее *достижимое* значение SN (той же чётности, что и n),
        для которого P(SN ≥ a) ≤ FAR₀/2; это гарантирует FAR ≤ FAR₀.

        Если целевая вероятность недостижима (малое n, книга стр. 190),
        берётся максимально возможное a = n — самые широкие границы и
        наименьший достижимый FAR (как для n = 1, где a = 1, FAR = 1).
        """
        target = far0 / 2
        start = 1 if n % 2 == 1 else 2
        for a in range(start, n + 1, 2):
            if cls._p_sn_ge_a(n, a) <= target:
                return a, 2.0 * cls._p_sn_ge_a(n, a)
        return n, 2.0 * cls._p_sn_ge_a(n, n)

    @classmethod
    def _calc_a_nearest(cls, n: int, alpha: float) -> Tuple[int, float]:
        """
        Подход 3: ближайший к α.
        a = argmin_a |P(|SN| ≥ a) − α|.
        """
        best_a, best_p, best_diff = 1, 1.0, float('inf')
        for a in range(1, n + 1):
            p = cls._p_abs_sn_ge_a(n, a)
            diff = abs(p - alpha)
            if diff < best_diff:
                best_diff, best_a, best_p = diff, a, p
        return best_a, best_p

    @classmethod
    def _calc_a_normal(cls, n: int, far0: float) -> Tuple[int, float]:
        """
        Подход 2: нормальная аппроксимация (симметричная граница ±a).

        Граница берётся по нормальному приближению распределения SN в IC:
        a — наименьшее достижимое значение (той же чётности, что и n),
        не меньше z_{1−FAR₀/2} · SD(SN), где SD(SN) = sqrt(n). Риск делится
        симметрично: по z_{1−FAR₀/2}·SD на каждый хвост, суммарно номинальный
        двусторонний FAR₀. Это асимптотический по природе метод (ср.
        npSPC::Limits_asymptotical); достигнутый FAR не обязан быть ≤ FAR₀.
        """
        z = stats.norm.ppf(1.0 - far0 / 2.0)
        a0 = int(np.ceil(z * np.sqrt(n)))
        a = a0 if a0 % 2 == n % 2 else a0 + 1
        a = min(max(a, 1), n)
        return a, 2.0 * cls._p_sn_ge_a(n, a)

    def _calculate_a_value(self) -> int:
        """Расчёт a согласно выбранному подходу."""
        n = self.sample_size
        if self.approach == 'exact':
            a, _ = self._calc_a_exact(n, self.far0)
        elif self.approach == 'nearest':
            a, _ = self._calc_a_nearest(n, self.alpha)
        elif self.approach == 'normal':
            a, _ = self._calc_a_normal(n, self.far0)
        else:
            raise ValueError(f"Неизвестный подход: {self.approach}")
        return max(a, 1)

    def compare_approaches(self) -> pd.DataFrame:
        """
        Сравнение трёх подходов для текущего n.

        Returns
        -------
        pd.DataFrame с колонками:
            approach, a, FAR, ARL_IC, MRL_IC, description
        """
        n = self.sample_size
        rows = []

        for approach, label in self.APPROACH_LABELS.items():
            if approach == 'exact':
                a, far = self._calc_a_exact(n, self.far0)
                desc = f'P(SN ≥ a) ≤ FAR₀/2, FAR₀ = {self.far0}'
            elif approach == 'normal':
                a, far = self._calc_a_normal(n, self.far0)
                desc = f'нормальная аппроксимация z·√n, FAR₀ = {self.far0}'
            elif approach == 'nearest':
                a, far = self._calc_a_nearest(n, self.alpha)
                desc = f'|P(|SN| ≥ a) − α| → min, α = {self.alpha}'
            else:
                continue

            arl = 1.0 / far if far > 0 else np.inf
            mrl = int(np.ceil(np.log(0.5) / np.log(1 - far))) if 0 < far < 1 else np.nan

            rows.append({
                'approach': approach,
                'label': label,
                'a': a,
                'FAR': far,
                'ARL_IC': arl,
                'MRL_IC': mrl,
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
        """
        Расчёт контрольных границ и статистик по подгруппам.

        Parameters
        ----------
        a_value : int, optional
            Явно заданное a. Если указано — подход игнорируется.
        approach : str, optional
            Переопределить подход к расчёту a.

        Returns
        -------
        Dict с полями CL, UCL, LCL, a_value, target_value, FAR, ARL_IC, MRL_IC.
        """
        if approach is not None:
            self.approach = normalize_approach(approach)

        # Расчёт SN по каждой подгруппе
        subgroup_data = self.data.iloc[:, :self.sample_size]
        results = []
        for idx in range(len(subgroup_data)):
            row = subgroup_data.iloc[idx]
            result = self._calculate_signs_for_row(row)
            result['subgroup'] = idx + 1
            results.append(result)
        self.subgroups = pd.DataFrame(results)

        n = self.sample_size

        # Определение c
        if a_value is not None:
            self.a_value = int(a_value)
        elif self.a_value is None:
            self.a_value = self._calculate_a_value()
        # иначе используем установленное ранее self.a_value

        a = self.a_value
        cl, ucl, lcl = 0, a, -a

        # Вероятности и характеристики длины серии
        far = self._p_abs_sn_ge_a(n, a)
        arl = 1.0 / far if far > 0 else np.inf
        mrl = int(np.ceil(np.log(0.5) / np.log(1 - far))) if 0 < far < 1 else np.nan

        self.control_limits = {
            'CL': cl,
            'UCL': ucl,
            'LCL': lcl,
            'a_value': a,
            'target_value': self.target_value,
            'n': n,
            'approach': self.approach,
            'far0': self.far0,
            'alpha': self.alpha,
            'FAR': far,
            'ARL_IC': arl,
            'MRL_IC': mrl,
        }

        # Таблица сравнения подходов
        self.comparison_table = self.compare_approaches()

        self._find_violations()
        return self.control_limits

    def _find_violations(self):
        """
        Поиск нарушений по правилу сигнала: |SN| ≥ a.

        Chakraborti & Graham (2019), § 4.2.1.1, ур. 4.3, стр. 190.
        """
        self.violations = []
        if self.subgroups is None or self.control_limits is None:
            return

        a = self.control_limits['a_value']
        for _, row in self.subgroups.iterrows():
            if row['sn'] >= a or row['sn'] <= -a:
                self.violations.append({
                    'subgroup': int(row['subgroup']),
                    'value': int(row['sn']),
                    'rule': f'|SN| ≥ {a}',
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
        """
        Построение знаковой карты Шухарта.

        Оформление едино с CUSUM-картами (``CusumSignChart.plot``): линия с
        маркерами, тот же запас по осям и постановка подписей значений.

        Параметры
        ---------
        show_zones : bool, default=False
            Рисовать границы зон Вестерн-Электрик (±a/3 и ±2a/3) и подписи
            A/B/C справа. По умолчанию выключено — как в CUSUM-картах.
        fill_zones : bool, default=False
            Если True — заливать зоны полупрозрачным цветом.
        value_offset : (float, float), default=(0, 4.0)
            Смещение подписи значения от точки **в типографских пунктах**
            (не в единицах данных), поэтому зазор не зависит от масштаба оси.

        Цвета зон (σ = a/3 — контрольная граница a соответствует 3σ)
        ---------
        Зона A (внешняя, 2σ…3σ)   — красный
        Зона B (средняя, 1σ…2σ)   — жёлтый
        Зона C (внутренняя, 0…1σ) — зелёный
        """
        if self.control_limits is None:
            self.calculate_limits()

        fig, ax = plt.subplots(figsize=figsize)

        x = self.subgroups['subgroup'].values
        y = self.subgroups['sn'].values
        a = self.control_limits['a_value']

        # --- Зоны (сдержанные: серые линии и опциональная серая заливка) ---
        zone_alpha = 0.5 if fill_zones else 0.0

        if show_zones and a >= 3:
            z1, z2 = a / 3, 2 * a / 3

            if fill_zones:
                for lo, hi in ((z2, a), (-a, -z2), (z1, z2),
                               (-z2, -z1), (-z1, z1)):
                    ax.axhspan(lo, hi, color=ZONE_FILL, alpha=zone_alpha,
                               zorder=0)

            # Горизонтальные линии границ зон
            for level in (z1, z2, -z1, -z2):
                ax.axhline(y=level, color=ZONE_LINE, linestyle=':',
                           linewidth=1.0, zorder=1)

            # Подписи зон справа
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

        # --- Точки: линия с маркерами, нарушения — крупные акцентные точки ---
        is_violation = (y >= a) | (y <= -a)

        ax.plot(x, y, '-o', color=self.color, linewidth=1.2,
                markersize=DATA_MARKER_SIZE, zorder=3, label='$SN_i$')
        if is_violation.any():
            ax.scatter(
                x[is_violation], y[is_violation],
                s=SIGNAL_MARKER_SIZE, color=ALERT, zorder=4,
                label=f'{math_text("Нарушения")} ({is_violation.sum()})',
            )

        # --- Контрольные линии ---
        hline(ax, 0, "center", label=r'$\mathrm{CL} = 0$')
        hline(ax, a, "limit", label=rf'$\mathrm{{UCL}} = +{a}$')
        hline(ax, -a, "limit", label=rf'$\mathrm{{LCL}} = -{a}$')

        # --- Подписи значений (над точкой при y ≥ 0, под ней иначе) ---
        if show_values:
            annotate_values(ax, x, y, offset=value_offset, fmt="{:.1f}")

        # --- Оформление ---
        ax.set_xlabel(r'$t$ (' + math_text('номер подгруппы') + ')')
        ax.set_ylabel(r'$SN_t = n^{+} - n^{-}$')
        ax.set_xticks(x)

        # Правый отступ — под подписи зон, только когда они показаны.
        right_pad = 3.2 if (show_zones and a >= 3) else 0.5
        ax.set_xlim(x.min() - 0.5, x.max() + right_pad)

        # Запас сверху, чтобы блок данных в правом верхнем углу не закрывал
        # подписи значений и точки (как в CUSUM-картах).
        y_low = min(float(y.min()), -a)
        y_high = max(float(y.max()), a)
        span = max(y_high - y_low, 1.0)
        ax.set_ylim(y_low - 0.05 * span, y_high + 0.25 * span)

        approach_label = self.APPROACH_PLOT_LABELS.get(
            self.approach, self.approach)
        if title is None:
            title = (math_text('Знаковая карта Шухарта') + ' — '
                     rf'$n={self.sample_size}$, $a={a}$, '
                     + math_text('подход:') + ' ' + math_text(approach_label))
        ax.set_title(title)

        # --- Информационный блок (в стиле легенды, правый верхний угол) ---
        info_lines = [
            rf"$\mu_0 = {self.target_value:.4f}$    "
            rf"$n = {self.sample_size}$, $m = {len(self.subgroups)}$",
            rf"$a = {a}$   ($\sigma = a/3$)",
            rf"$\mathrm{{FAR}} = {self.control_limits['FAR']:.4f}$   "
            rf"$\mathrm{{ARL}} = {self.control_limits['ARL_IC']:.1f}$   "
            rf"$\mathrm{{MRL}} = {self.control_limits['MRL_IC']}$",
        ]
        data_legend(ax, info_lines)

        # Легенда с ручками для границ зон (если показываются)
        handles, labels = ax.get_legend_handles_labels()
        if show_zones and a >= 3:
            zone_handles = [
                Line2D([0], [0], color=ZONE_LINE, linestyle=':',
                       linewidth=1.5,
                       label=math_text('Границы зон') + r' $\mathrm{A/B}$'),
            ]
            handles = handles + zone_handles
            labels = labels + [h.get_label() for h in zone_handles]

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
        """
        Сравнение трёх подходов к расчёту a на диапазоне n.

        Parameters
        ----------
        n_range : array-like, optional
            Диапазон значений n. По умолчанию 2..30.
        """
        if n_range is None:
            n_range = np.arange(2, 31)
        n_range = np.asarray(n_range)

        cons_a, cons_far = [], []
        near_a, near_far = [], []
        sym_a, sym_far = [], []

        for n in n_range:
            a_c, f_c = self._calc_a_exact(n, self.far0)
            a_n, f_n = self._calc_a_nearest(n, self.alpha)
            a_s, f_s = self._calc_a_normal(n, self.far0)
            cons_a.append(a_c); cons_far.append(f_c)
            near_a.append(a_n); near_far.append(f_n)
            sym_a.append(a_s);   sym_far.append(f_s)

        fig, axes = plt.subplots(1, 2, figsize=figsize)

        colors = (PALETTE[0], PALETTE[3], PALETTE[2])

        # --- Левый график: значения a ---
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

        # --- Правый график: достигнутый FAR ---
        axes[1].plot(n_range, cons_far, 'o-', color=colors[0],
                     label='Точный')
        axes[1].plot(n_range, near_far, 's--', color=colors[1],
                     label='Ближайший')
        axes[1].plot(n_range, sym_far, '^:', color=colors[2],
                     label='Нормальная аппроксимация')
        axes[1].axhline(self.far0, color=colors[0], linestyle=':', alpha=0.6,
                        label=rf'$FAR_0 = {self.far0}$')
        axes[1].axhline(self.alpha, color=colors[1], linestyle=':', alpha=0.6,
                        label=rf'$\alpha = {self.alpha}$')
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

    def calculate_sign_test(self) -> Dict:
        """Знаковый тест для проверки гипотезы о медиане."""
        if self.subgroups is None:
            self.calculate_limits()

        total_positive = int(self.subgroups['positive'].sum())
        total_negative = int(self.subgroups['negative'].sum())
        total = total_positive + total_negative

        if total > 0:
            k = min(total_positive, total_negative)
            p_value = 2 * stats.binom.cdf(k, total, 0.5)
            z_stat = (total_positive - total_negative) / np.sqrt(total)
        else:
            p_value = 1.0
            z_stat = 0.0

        return {
            'total_positive': total_positive,
            'total_negative': total_negative,
            'total': total,
            'p_value': float(min(p_value, 1.0)),
            'z_statistic': float(z_stat),
            'target_value': self.target_value,
            'significant': p_value < self.significance_level,
        }

    def get_sn_table(self) -> pd.DataFrame:
        """Таблица со значениями SN по подгруппам."""
        if self.subgroups is None:
            self.calculate_limits()
        return self.subgroups.copy()

    def get_sign_matrix(self) -> pd.DataFrame:
        """Матрица знаков (1, −1, 0)."""
        if self.subgroups is None:
            self.calculate_limits()
        sign_matrix = []
        for idx in range(len(self.data)):
            row = self.data.iloc[idx, :self.sample_size].dropna()
            signs = np.where(row.values > self.target_value, 1,
                             np.where(row.values < self.target_value, -1, 0))
            sign_matrix.append(signs)
        columns = [f'x{i+1}' for i in range(self.sample_size)]
        df_signs = pd.DataFrame(sign_matrix, columns=columns)
        df_signs.insert(0, 'subgroup', range(1, len(df_signs) + 1))
        return df_signs

    def get_summary(self) -> Dict:
        """Сводная информация о карте."""
        if self.control_limits is None:
            self.calculate_limits()

        return {
            'chart_type': 'Sign',
            'approach': self.approach,
            'target_value': self.target_value,
            'n': self.sample_size,
            'a': self.control_limits['a_value'],
            'UCL': self.control_limits['UCL'],
            'LCL': self.control_limits['LCL'],
            'CL': self.control_limits['CL'],
            'FAR': self.control_limits['FAR'],
            'ARL_IC': self.control_limits['ARL_IC'],
            'MRL_IC': self.control_limits['MRL_IC'],
            'total_subgroups': len(self.subgroups),
            'total_violations': len(self.violations),
            'mean_sn': float(self.subgroups['sn'].mean()),
            'violations': self.violations,
        }
