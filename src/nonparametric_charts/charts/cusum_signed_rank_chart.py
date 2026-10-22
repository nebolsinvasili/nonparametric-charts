"""
CUSUM-карта по знаковым рангам (CUSUM Signed-Rank Chart, CUSUM-SR).

Непараметрическая контрольная карта с памятью для контроля медианы
симметричного непрерывного распределения. В отличие от карты Шухарта,
накапливает знаково-ранговую статистику во времени, поэтому эффективнее
для обнаружения малых устойчивых сдвигов.

Теория (Chakraborti & Graham, 2019, § 4.2.2.4, стр. 205–206):
----------------------------------------------------------------------
Знаково-ранговая статистика подгруппы:

    SR_t = Σ_{j=1}^{n} sign(X_{tj} − μ₀) · R_{tj}
         = 2 T_n⁺ − n(n+1)/2,

где ``R_{tj}`` — ранг ``|X_{tj} − μ₀|`` внутри подгруппы, ``T_n⁺`` —
статистика знаковых рангов Уилкоксона. Требуется **симметрия** распределения
(как и для Шухарт-карты ``SignedRankChart``, § 4.2.1.2).

Верхняя односторонняя кумулятивная сумма (ур. 4.10):

    SR_t⁺ = max(0, SR_{t−1}⁺ + SR_t − k),   SR_0⁺ = 0,
    сигнал при первом t, где SR_t⁺ ≥ h.

Нижняя односторонняя кумулятивная сумма (ур. 4.11):

    SR_t⁻ = min(0, SR_{t−1}⁻ + SR_t + k),   SR_0⁻ = 0,
    сигнал при первом t, где SR_t⁻ ≤ −h.

Двусторонняя карта сигнализирует при срабатывании любой из сторон.
Здесь ``k > 0`` — референсное значение, ``h > 0`` — интервал решения
(параметры карты; выбор ``(h, k)`` — § 3.2.2, стр. 67, и
Bakir & Reynolds (1979)).

.. note::
   Печатная формула ур. 4.11 (стр. 206) содержит ``− k`` в нижней ветви —
   это **опечатка книги**: рабочий пример 4.9 (стр. 237) и параллель с
   ур. 4.8 (CUSUM-SN) требуют ``+ k``. Реализация использует ``+ k``.

Счётчики ``N⁺``/``N⁻`` — число последовательных периодов с ненулевой
статистикой; оценка точки сдвига — ``t − N`` (стр. 237).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from nonparametric_charts.base.base_chart import BaseControlChart
from nonparametric_charts.utils.statistics import signed_rank_details
from nonparametric_charts.utils.run_length import cusum_signed_rank_run_length
from nonparametric_charts.utils.plotting import plot_run_length as _plot_run_length
from nonparametric_charts.utils.run_length_design import design_signed_rank_h
from nonparametric_charts.utils.run_length_design import (
    design_signed_rank_kh,
)
from nonparametric_charts.utils.plot_style import (
    ACCENT,
    ALERT,
    DATA_MARKER_SIZE,
    PALETTE,
    SIGNAL_MARKER_SIZE,
    annotate_values,
    data_legend,
    hline,
    math_text,
)


class CusumSignedRankChart(BaseControlChart):
    """
    CUSUM-карта по знаковым рангам (CUSUM-SR).

    Непараметрическая карта с памятью для контроля центра симметричного
    непрерывного распределения (медианы).

    Parameters
    ----------
    data : pd.DataFrame
        Данные (m подгрупп × n наблюдений); строка — подгруппа.
    sample_size : int
        Размер подгруппы n (≥ 2).
    target_value : float, optional
        Целевое значение μ₀. Если None — медиана всех данных.
    k : float, default=3.0
        Референсное значение (> 0). Значение по умолчанию — как в примере 4.9
        (стр. 236); корректный выбор см. § 3.2.2.
    h : float, default=8.0
        Интервал решения (> 0). Значение по умолчанию — как в примере 4.9
        (стр. 236); подбор под номинальный ARL_IC — отдельная задача.

    Attributes
    ----------
    subgroups : pd.DataFrame
        Статистики по подгруппам: ``sr``, ``sr_plus``, ``sr_minus``,
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
        k: float = 3.0,
        h: float = 8.0,
    ):
        super().__init__(data, sample_size)
        self.chart_type = "CUSUM-SR"
        self.color = ACCENT

        if sample_size < 2:
            raise ValueError(
                "Знако-ранговая карта требует n ≥ 2 "
                "(ранжирование внутри подгруппы невозможно при n = 1)."
            )
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

        sr_plus = 0.0
        sr_minus = 0.0
        nplus = 0
        nminus = 0

        for idx in range(len(subgroup_data)):
            row = subgroup_data.iloc[idx].dropna().values
            details = signed_rank_details(row, self.target_value)
            sr = details['sr']

            # Верхняя ветвь (ур. 4.10)
            sr_plus = max(0.0, sr_plus + sr - self.k)
            nplus = nplus + 1 if sr_plus > 0 else 0

            # Нижняя ветвь (ур. 4.11): книга печатает −k, но пример 4.9
            # (стр. 237) использует +k — следуем примеру.
            sr_minus = min(0.0, sr_minus + sr + self.k)
            nminus = nminus + 1 if sr_minus < 0 else 0

            results.append({
                'subgroup': idx + 1,
                'sr': sr,
                'positive': details['positive'],
                'negative': details['negative'],
                'zero': details['zero'],
                'T_plus': details['T_plus'],
                'sr_plus': sr_plus,
                'sr_minus': sr_minus,
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
            'SR_max': self.sample_size * (self.sample_size + 1) // 2,
        }

        self._find_violations()
        return self.control_limits

    def _find_violations(self):
        """
        Поиск первого сигнала на каждой стороне.

        Верх: ``SR_t⁺ ≥ h``; низ: ``SR_t⁻ ≤ −h``
        (Chakraborti & Graham, 2019, § 4.2.2.4, ур. 4.10–4.11, стр. 205–206).
        Книга сообщает именно первое срабатывание (стр. 237).
        """
        self.violations = []
        if self.subgroups is None or self.control_limits is None:
            return

        h = self.control_limits['h']

        upper = self.subgroups[self.subgroups['sr_plus'] >= h]
        if len(upper) > 0:
            row = upper.iloc[0]
            self.violations.append({
                'subgroup': int(row['subgroup']),
                'side': 'upper',
                'value': float(row['sr_plus']),
                'counter': int(row['nplus']),
                'rule': f'SR⁺ ≥ h = {h}',
            })

        lower = self.subgroups[self.subgroups['sr_minus'] <= -h]
        if len(lower) > 0:
            row = lower.iloc[0]
            self.violations.append({
                'subgroup': int(row['subgroup']),
                'side': 'lower',
                'value': float(row['sr_minus']),
                'counter': int(row['nminus']),
                'rule': f'SR⁻ ≤ −h = −{h}',
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
        Построение CUSUM-SR-карты.

        Рисуются обе односторонние ветви (``SR_t⁺`` и ``SR_t⁻``) и границы
        ``±h``. Сигналы выделяются цветом ``ALERT``.
        """
        if self.control_limits is None:
            self.calculate_limits()

        fig, ax = plt.subplots(figsize=figsize)

        x = self.subgroups['subgroup'].values
        yp = self.subgroups['sr_plus'].values
        ym = self.subgroups['sr_minus'].values
        h = self.control_limits['h']

        lower_color = PALETTE[5]
        ax.plot(x, yp, '-o', color=self.color, linewidth=1.2,
                markersize=DATA_MARKER_SIZE, label='$SR_t^{+}$', zorder=3)
        ax.plot(x, ym, '-o', color=lower_color, linewidth=1.2,
                markersize=DATA_MARKER_SIZE, label='$SR_t^{-}$', zorder=3)

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
                            fmt="{:.0f}")
            annotate_values(ax, x, ym, side="below", offset=value_offset,
                            fmt="{:.0f}",
                            mask=[yl < -eps or (yl <= eps and yu > eps)
                                  for yu, yl in zip(yp, ym)])

        ax.set_xlabel(r'$t$ (' + math_text('номер подгруппы') + ')')
        ax.set_ylabel(r'$SR_t^{\pm}$')
        ax.set_xticks(x)
        ax.set_xlim(x.min() - 0.5, x.max() + 0.5)

        # Запас сверху, чтобы блок данных не закрывал подписи значений.
        y_low = min(float(ym.min()), -h)
        y_high = max(float(yp.max()), h)
        span = max(y_high - y_low, 1.0)
        ax.set_ylim(y_low - 0.05 * span, y_high + 0.25 * span)

        if title is None:
            title = (math_text('CUSUM-карта по знаковым рангам') + ' — '
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
            'chart_type': 'CUSUM-SR',
            'target_value': self.target_value,
            'n': self.sample_size,
            'k': self.control_limits['k'],
            'h': self.control_limits['h'],
            'UCL': self.control_limits['UCL'],
            'LCL': self.control_limits['LCL'],
            'CL': self.control_limits['CL'],
            'SR_max': self.control_limits['SR_max'],
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
        max_quantile: float = 0.9999,
    ):
        """
        Распределение длины серии CUSUM-SR (марковский метод, IC).

        Parameters
        ----------
        sided : {'upper', 'lower', 'two'}, default='two'
            Тип карты.
        max_quantile : float, default=0.9999
            Уровень усечения хвоста PMF.

        Returns
        -------
        RunLengthResult
            ``ARL``, ``SDRL``, ``MRL``, перцентили, PMF/CDF.

        Notes
        -----
        Ур. 4.12 (стр. 206), ур. 3.22–3.24 (стр. 112). Используются
        текущие ``k`` и ``h`` карты (после ``calculate_limits`` — их
        актуальные значения).
        """
        return cusum_signed_rank_run_length(
            self.sample_size, self.k, self.h,
            sided=sided, max_quantile=max_quantile,
        )

    def plot_run_length(
        self,
        sided: str = 'two',
        *,
        max_quantile: float = 0.9999,
        figsize: Tuple[float, float] = (10.0, 5.5),
        title: Optional[str] = None,
        max_t: Optional[int] = None,
        save_path: Optional[str] = None,
    ) -> Tuple[plt.Figure, plt.Axes]:
        """
        График распределения длины серии CUSUM-SR (PMF и CDF, IC).

        Parameters
        ----------
        sided : {'upper', 'lower', 'two'}, default='two'
            Тип карты.
        max_quantile : float, default=0.9999
            Уровень усечения хвоста PMF.
        figsize : (float, float), default=(10, 5.5)
            Размер фигуры.
        title : str, optional
            Заголовок; по умолчанию — характеристики RL.
        max_t : int, optional
            Показать только ``t ≤ max_t``.
        save_path : str, optional
            Путь для сохранения рисунка.

        Returns
        -------
        (matplotlib.figure.Figure, matplotlib.axes.Axes)
            Фигура и ось PMF.

        Notes
        -----
        Ур. 4.12 (стр. 206), ур. 3.22–3.24 (стр. 112). Используются
        текущие ``k`` и ``h`` карты.
        """
        result = self.run_length(sided=sided, max_quantile=max_quantile)
        return _plot_run_length(
            result, figsize=figsize, title=title, max_t=max_t,
            save_path=save_path,
        )

    def design_h(
        self,
        target_arl: float,
        sided: str = 'two',
        *,
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
        return design_signed_rank_h(
            self.sample_size, target_arl, self.k,
            sided=sided, max_candidates=max_candidates,
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
        Совместный подбор ``(k, h)`` под целевой сдвиг и номинальный ``ARL``.

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
        return design_signed_rank_kh(
            self.sample_size, target_arl, delta,
            sided=sided, distribution=distribution, **kwargs,
        )
