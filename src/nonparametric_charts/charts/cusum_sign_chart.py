"""
CUSUM-карта по знакам (CUSUM Sign Chart, CUSUM-SN).

Непараметрическая контрольная карта с памятью для контроля медианы (или любого
параметра положения) процесса. В отличие от карты Шухарта, накапливает знаковую
статистику во времени, поэтому эффективнее для обнаружения малых устойчивых
сдвигов.

Теория (Chakraborti & Graham, 2019, § 4.2.2.1, стр. 202–203):
----------------------------------------------------------------------
Знаковая статистика подгруппы:

    SN_t = 2 T_t − n,   T_t = n_t⁺ ~ BIN(n, 0.5) в IC

Верхняя односторонняя кумулятивная сумма (ур. 4.7):

    SN_t⁺ = max(0, SN_{t−1}⁺ + SN_t − k),   SN_0⁺ = 0,
    сигнал при первом t, где SN_t⁺ ≥ h.

Нижняя односторонняя кумулятивная сумма (ур. 4.8):

    SN_t⁻ = min(0, SN_{t−1}⁻ + SN_t + k),   SN_0⁻ = 0,
    сигнал при первом t, где SN_t⁻ ≤ −h.

Двусторонняя карта сигнализирует при срабатывании любой из сторон.
Здесь ``k > 0`` — референсное значение, ``h > 0`` — интервал решения
(дизайн-параметры; выбор ``(h, k)`` — § 3.2.2, стр. 67, и
Amin, Reynolds & Bakir (1995), табл. 5).

Счётчики ``N⁺``/``N⁻`` — число последовательных периодов с ненулевой
статистикой; оценка точки сдвига — ``t − N`` (стр. 231).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

try:
    from nonparametric_charts.base.base_chart import BaseControlChart
except ImportError:
    # Fallback: минимальный базовый класс, если пакет недоступен
    class BaseControlChart:
        def __init__(self, data, sample_size):
            self.data = data
            self.sample_size = sample_size

try:
    from nonparametric_charts.utils.statistics import sign_counts, sign_statistic
except ImportError:  # fallback: локальная реализация
    def sign_counts(values, target_value):
        arr = np.asarray(values, dtype=float).ravel()
        arr = arr[~np.isnan(arr)]
        positive = int(np.sum(arr > target_value))
        negative = int(np.sum(arr < target_value))
        zero = int(arr.size - positive - negative)
        return positive, negative, zero

    def sign_statistic(values, target_value):
        positive, negative, _ = sign_counts(values, target_value)
        return positive - negative

from nonparametric_charts.utils.run_length import cusum_sign_run_length
from nonparametric_charts.utils.run_length_design import design_sign_h
from nonparametric_charts.utils.run_length_design import design_sign_kh

from nonparametric_charts.utils.plot_style import (
    ACCENT,
    ALERT,
    DATA_MARKER_SIZE,
    PALETTE,
    SIGNAL_MARKER_SIZE,
    ZONE_LINE,
    annotate_values,
    data_legend,
    hline,
    math_text,
)


class CusumSignChart(BaseControlChart):
    """
    CUSUM-карта по знакам (CUSUM-SN).

    Непараметрическая карта с памятью для контроля центра процесса
    (медианы или любого параметра положения).

    Parameters
    ----------
    data : pd.DataFrame
        Данные (m подгрупп × n наблюдений); строка — подгруппа.
    sample_size : int
        Размер подгруппы n.
    target_value : float, optional
        Целевое значение μ₀. Если None — медиана всех данных.
    k : float, default=0.5
        Референсное значение (> 0). Значение по умолчанию — как в примере 4.6
        (стр. 229); корректный выбор см. § 3.2.2.
    h : float, default=3.0
        Интервал решения (> 0). Значение по умолчанию — как в примере 4.6
        (стр. 229); подбор под номинальный ARL_IC — отдельная задача.

    Attributes
    ----------
    subgroups : pd.DataFrame
        Статистики по подгруппам: ``sn``, ``sn_plus``, ``sn_minus``,
        ``nplus``, ``nminus``.
    control_limits : dict
        ``CL = 0``, ``UCL = +h``, ``LCL = −h``, плюс ``k``, ``h``.
    violations : list of dict
        Первые сигналы (по одному на сторону).
    """

    def __init__(
        self,
        data: pd.DataFrame,
        sample_size: int,
        target_value: Optional[float] = None,
        k: float = 0.5,
        h: float = 3.0,
    ):
        super().__init__(data, sample_size)
        self.chart_type = "CUSUM-SN"
        self.color = ACCENT

        if k <= 0:
            raise ValueError(f"Референсное значение k должно быть > 0, получено {k}")
        if h <= 0:
            raise ValueError(f"Интервал решения h должен быть > 0, получено {h}")
        self.k = float(k)
        self.h = float(h)

        if target_value is None:
            self.target_value = self._calculate_median()
        else:
            self.target_value = float(target_value)

        self.subgroups: Optional[pd.DataFrame] = None
        self.control_limits: Optional[Dict] = None
        self.violations: List[Dict] = []

    # ------------------------------------------------------------------ #
    #  Вспомогательные расчёты
    # ------------------------------------------------------------------ #

    def _calculate_median(self) -> float:
        """Медиана всех наблюдений как целевое значение."""
        all_values = self.data.iloc[:, :self.sample_size].values.flatten()
        all_values = all_values[~np.isnan(all_values)]
        return float(np.median(all_values)) if len(all_values) > 0 else 0.0

    # ------------------------------------------------------------------ #
    #  Основной расчёт
    # ------------------------------------------------------------------ #

    def calculate_limits(
        self,
        k: Optional[float] = None,
        h: Optional[float] = None,
    ) -> Dict:
        """
        Расчёт кумулятивных сумм по подгруппам и параметров карты.

        Parameters
        ----------
        k : float, optional
            Переопределить референсное значение.
        h : float, optional
            Переопределить интервал решения.

        Returns
        -------
        dict
            ``CL``, ``UCL``, ``LCL``, ``k``, ``h``, ``target_value``, ``n``.
        """
        if k is not None:
            if k <= 0:
                raise ValueError(f"Референсное значение k должно быть > 0, получено {k}")
            self.k = float(k)
        if h is not None:
            if h <= 0:
                raise ValueError(f"Интервал решения h должно быть > 0, получено {h}")
            self.h = float(h)

        subgroup_data = self.data.iloc[:, :self.sample_size]
        results: List[Dict] = []

        sn_plus = 0.0
        sn_minus = 0.0
        nplus = 0
        nminus = 0

        for idx in range(len(subgroup_data)):
            row = subgroup_data.iloc[idx]
            values = row.dropna().values
            if len(values) == 0:
                positive = negative = zero = sn = 0
            else:
                positive, negative, zero = sign_counts(values, self.target_value)
                sn = sign_statistic(values, self.target_value)

            # Верхняя ветвь (ур. 4.7)
            sn_plus = max(0.0, sn_plus + sn - self.k)
            nplus = nplus + 1 if sn_plus > 0 else 0

            # Нижняя ветвь (ур. 4.8)
            sn_minus = min(0.0, sn_minus + sn + self.k)
            nminus = nminus + 1 if sn_minus < 0 else 0

            results.append({
                'subgroup': idx + 1,
                'positive': positive,
                'negative': negative,
                'zero': zero,
                'sn': sn,
                'sn_plus': sn_plus,
                'sn_minus': sn_minus,
                'nplus': nplus,
                'nminus': nminus,
            })

        self.subgroups = pd.DataFrame(results)

        self.control_limits = {
            'CL': 0.0,
            'UCL': self.h,
            'LCL': -self.h,
            'k': self.k,
            'h': self.h,
            'target_value': self.target_value,
            'n': self.sample_size,
        }

        self._find_violations()
        return self.control_limits

    def _find_violations(self):
        """
        Поиск первого сигнала на каждой стороне.

        Верх: ``SN_t⁺ ≥ h``; низ: ``SN_t⁻ ≤ −h``
        (Chakraborti & Graham, 2019, § 4.2.2.1, ур. 4.7–4.8, стр. 202–203).
        Книга сообщает именно первое срабатывание (стр. 231).
        """
        self.violations = []
        if self.subgroups is None or self.control_limits is None:
            return

        h = self.control_limits['h']

        upper = self.subgroups[self.subgroups['sn_plus'] >= h]
        if len(upper) > 0:
            row = upper.iloc[0]
            self.violations.append({
                'subgroup': int(row['subgroup']),
                'side': 'upper',
                'value': float(row['sn_plus']),
                'counter': int(row['nplus']),
                'rule': f'SN⁺ ≥ h = {h}',
            })

        lower = self.subgroups[self.subgroups['sn_minus'] <= -h]
        if len(lower) > 0:
            row = lower.iloc[0]
            self.violations.append({
                'subgroup': int(row['subgroup']),
                'side': 'lower',
                'value': float(row['sn_minus']),
                'counter': int(row['nminus']),
                'rule': f'SN⁻ ≤ −h = −{h}',
            })

        self.violations.sort(key=lambda v: v['subgroup'])

    # ------------------------------------------------------------------ #
    #  Визуализация
    # ------------------------------------------------------------------ #

    def plot(
        self,
        figsize: Tuple[int, int] = (13, 7),
        save_path: Optional[str] = None,
        title: Optional[str] = None,
        show_values: bool = True,
        value_offset: Tuple[float, float] = (0, 4.0),
    ) -> Tuple[plt.Figure, plt.Axes]:
        """
        Построение CUSUM-SN-карты.

        Рисуются обе односторонние ветви (``SN_t⁺`` и ``SN_t⁻``) и границы
        ``±h``. Сигналы выделяются красным.
        """
        if self.control_limits is None:
            self.calculate_limits()

        fig, ax = plt.subplots(figsize=figsize)

        x = self.subgroups['subgroup'].values
        yp = self.subgroups['sn_plus'].values
        ym = self.subgroups['sn_minus'].values
        h = self.control_limits['h']

        lower_color = PALETTE[5]
        ax.plot(x, yp, '-o', color=self.color, linewidth=1.2,
                markersize=DATA_MARKER_SIZE, label='$SN_t^{+}$', zorder=3)
        ax.plot(x, ym, '-o', color=lower_color, linewidth=1.2,
                markersize=DATA_MARKER_SIZE, label='$SN_t^{-}$', zorder=3)

        # Сигналы
        sig_upper = [(v['subgroup'], v['value']) for v in self.violations
                     if v['side'] == 'upper']
        sig_lower = [(v['subgroup'], v['value']) for v in self.violations
                     if v['side'] == 'lower']
        if sig_upper:
            sx, sy = zip(*sig_upper)
            ax.scatter(sx, sy, s=SIGNAL_MARKER_SIZE, color=ALERT, zorder=4,
                       label=f'{math_text("Сигнал")} ({len(self.violations)})')
        if sig_lower:
            sx, sy = zip(*sig_lower)
            ax.scatter(sx, sy, s=SIGNAL_MARKER_SIZE, color=ALERT, zorder=4)

        # Границы
        hline(ax, 0, "center", label=r'$\mathrm{CL} = 0$')
        hline(ax, h, "limit", label=rf'$h = {h:g}$')
        hline(ax, -h, "limit", label=rf'$-h = -{h:g}$')

        if show_values:
            eps = 1e-9
            # Подписываем обе ветви, включая нулевые значения. Если обе ветви
            # нулевые, нуль показываем один раз (точки совпадают) — нижнюю
            # ветвь подписываем только когда верхняя не ноль.
            annotate_values(ax, x, yp, side="above", offset=value_offset,
                            fmt="{:.1f}")
            annotate_values(ax, x, ym, side="below", offset=value_offset,
                            fmt="{:.1f}",
                            mask=[yl < -eps or (yl <= eps and yu > eps)
                                  for yu, yl in zip(yp, ym)])

        ax.set_xlabel(r'$t$ (' + math_text('номер подгруппы') + ')')
        ax.set_ylabel(r'$SN_t^{\pm}$')
        ax.set_xticks(x)
        ax.set_xlim(x.min() - 0.5, x.max() + 0.5)

        # Запас сверху, чтобы блок данных в правом верхнем углу не закрывал
        # подписи значений и точки.
        y_low = min(float(ym.min()), -h)
        y_high = max(float(yp.max()), h)
        span = max(y_high - y_low, 1.0)
        ax.set_ylim(y_low - 0.05 * span, y_high + 0.25 * span)

        if title is None:
            title = (math_text('CUSUM-карта по знакам') + ' — '
                     rf'$n={self.sample_size}$, $k={self.k:g}$, $h={self.h:g}$')
        ax.set_title(title)

        # --- Информационный блок (в стиле легенды, правый верхний угол) ---
        info_lines = [
            rf"$\mu_0 = {self.target_value:.4f}$    "
            rf"$n = {self.sample_size}$, $m = {len(self.subgroups)}$",
            rf"$k = {self.k:g}$   $h = {self.h:g}$",
            math_text('сигналов:') + f' ${len(self.violations)}$',
        ]
        data_legend(ax, info_lines)

        ax.legend(loc='best', fontsize=8, ncol=2, labelspacing=0.25,
                  handlelength=1.4, handletextpad=0.4,
                  borderpad=0.3, borderaxespad=0.4, columnspacing=1.0)
        ax.grid(alpha=0.25, linestyle=':')

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f'График сохранён: {save_path}')
        return fig, ax

    # ------------------------------------------------------------------ #
    #  Сводка
    # ------------------------------------------------------------------ #

    def get_summary(self) -> Dict:
        """Сводная информация о карте."""
        if self.control_limits is None:
            self.calculate_limits()

        first = self.violations[0] if self.violations else None

        return {
            'chart_type': 'CUSUM-SN',
            'target_value': self.target_value,
            'n': self.sample_size,
            'k': self.control_limits['k'],
            'h': self.control_limits['h'],
            'UCL': self.control_limits['UCL'],
            'LCL': self.control_limits['LCL'],
            'CL': self.control_limits['CL'],
            'total_subgroups': len(self.subgroups),
            'total_violations': len(self.violations),
            'first_signal': first,
            'violations': self.violations,
        }

    # ------------------------------------------------------------------ #
    #  Длина серии (RL)
    # ------------------------------------------------------------------ #

    def run_length(
        self,
        sided: str = 'two',
        *,
        p: float = 0.5,
        max_quantile: float = 0.9999,
    ):
        """
        Распределение длины серии CUSUM-SN (марковский метод).

        Parameters
        ----------
        sided : {'upper', 'lower', 'two'}, default='two'
            Тип карты.
        p : float, default=0.5
            ``P(X ≥ μ₀)``; в IC ``p = 0.5``.
        max_quantile : float, default=0.9999
            Уровень усечения хвоста PMF.

        Returns
        -------
        RunLengthResult
            ``ARL``, ``SDRL``, ``MRL``, перцентили, PMF/CDF.

        Notes
        -----
        Ур. 4.9 (стр. 203), ур. 3.22–3.24 (стр. 112). Используются
        текущие ``k`` и ``h`` карты (после ``calculate_limits`` — их
        актуальные значения).
        """
        return cusum_sign_run_length(
            self.sample_size, self.k, self.h,
            sided=sided, p=p, max_quantile=max_quantile,
        )

    def design_h(
        self,
        target_arl: float,
        sided: str = 'two',
        *,
        p: float = 0.5,
        max_candidates: int = 5_000,
    ):
        """
        Подобрать ``h`` под номинальную ``ARL`` в IC.

        Parameters
        ----------
        target_arl : float
            Номинальная ``ARL_IC`` (например, 370 или 500).
        sided : {'upper', 'lower', 'two'}, default='two'
            Тип карты.
        p : float, default=0.5
            ``P(X ≥ μ₀)`` в IC.
        max_candidates : int, default=5000
            Предохранитель перебора вариантов ``h``.

        Returns
        -------
        DesignResult
            Найденный ``h``, достигнутая ``ARL`` и отклонение от номинала.

        Notes
        -----
        ``ARL(h)`` — ступенчатая функция, поэтому номинал может быть
        недостижим точно; возвращается ближайший вариант. Выбор ``(k, h)``:
        § 3.2.2, стр. 67; § 4.2.2, стр. 202–203.
        """
        return design_sign_h(
            self.sample_size, target_arl, self.k,
            sided=sided, p=p, max_candidates=max_candidates,
        )

    def design_kh(
        self,
        target_arl: float,
        delta,
        sided: str = 'two',
        *,
        distribution: str = 'normal',
        **kwargs,
    ):
        """
        Совместный дизайн ``(k, h)`` под целевой сдвиг и номинальный ``ARL``.

        Parameters
        ----------
        target_arl : float
            Номинальная ``ARL_IC`` (например, 370 или 500).
        delta : float or sequence of float
            Целевой сдвиг (сдвиги) медианы в единицах σ; ``δ ≠ 0``.
        sided : {'upper', 'lower', 'two'}, default='two'
            Тип карты.
        distribution : str, default='normal'
            Распределение процесса при сдвиге.
        **kwargs
            Дополнительные параметры ``design_kh`` (``k_values``,
            ``k_fractions``, ``tol`` и т. д.).

        Returns
        -------
        DesignKHResult
            Оптимальная пара ``(k, h)`` и полная сетка.

        Notes
        -----
        ``k`` выбирается первым (аналог ``k = δ/2``), ``h`` — под номинал;
        критерий — минимум ``ARL_OOC``. § 3.2.2, стр. 67–72;
        § 4.3.2, стр. 232–233.
        """
        return design_sign_kh(
            self.sample_size, target_arl, delta,
            sided=sided, distribution=distribution, **kwargs,
        )
