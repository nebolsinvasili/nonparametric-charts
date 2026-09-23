"""
Карта знако-ранговых сумм Шухарта (Wilcoxon Signed-Rank Chart)

Непараметрическая контрольная карта, использующая ранги отклонений
от целевого значения. Основана на критерии Уилкоксона.

Теория:
--------
Для каждой подгруппы вычисляется статистика Уилкоксона:
W = Σ sign(d_ij) · rank(|d_ij|)

где:
- d_ij = x_ij - μ₀ (отклонение от целевого значения)
- sign(d) - знак отклонения (+1 или -1)
- rank(|d|) - ранг абсолютного отклонения

Распределение W:
-----------------
При отсутствии смещения, W имеет симметричное распределение
с центром в 0.

Контрольные границы:
--------------------
CL = 0
UCL = z_{1-α/2} · σ_W (для нормальной аппроксимации)
LCL = -z_{1-α/2} · σ_W

где:
- σ_W = sqrt(n(n+1)(2n+1)/6)
- Или точные границы для малых n

Преимущества:
-------------
- Мощнее знакового теста
- Учитывает величину отклонений
- Непараметрическая - не требует нормальности
- Устойчива к выбросам

Недостатки:
-----------
- Более сложные вычисления
- Требует ранжирования данных
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Optional, Tuple, List
from scipy import stats
from scipy.special import comb
from src.base.base_chart import BaseControlChart


class SignRankChart(BaseControlChart):
    """
    Карта знако-ранговых сумм (Wilcoxon Signed-Rank Chart)
    
    Непараметрическая карта, учитывающая ранги отклонений.
    Основана на критерии Уилкоксона.
    
    Examples:
    ---------
    >>> import pandas as pd
    >>> data = pd.DataFrame(np.random.normal(10, 2, (20, 5)))
    >>> chart = SignedRankChart(data, sample_size=5, target_value=10)
    >>> limits = chart.calculate_limits()
    >>> fig, ax = chart.plot()
    >>> summary = chart.get_summary()
    """
    
    def __init__(self, data: pd.DataFrame, sample_size: int,
                 target_value: Optional[float] = None,
                 coefficients_file: Optional[str] = None,
                 alpha: float = 0.05,
                 use_exact: bool = False):
        """
        Инициализация карты знако-ранговых сумм
        
        Parameters:
        -----------
        data : pd.DataFrame
            Данные для построения карты
        sample_size : int
            Размер подгруппы (n)
        target_value : float, optional
            Целевое значение μ₀
            Если не указано, используется медиана всех данных
        coefficients_file : str, optional
            Путь к файлу с коэффициентами
        alpha : float, default=0.05
            Уровень значимости
        use_exact : bool, default=False
            Использовать точные границы для малых n (n ≤ 20)
        """
        super().__init__(data, sample_size, coefficients_file)
        self.chart_type = "Signed Rank"
        self.color = '#8E44AD'
        self.target_value = target_value
        self.alpha = alpha
        self.use_exact = use_exact
        self.significance_level = alpha
        
        if target_value is None:
            self.target_value = self._calculate_median()
    
    def _calculate_median(self) -> float:
        """Расчет медианы всех данных"""
        all_values = self.data.iloc[:, :self.sample_size].values.flatten()
        all_values = all_values[~np.isnan(all_values)]
        return np.median(all_values) if len(all_values) > 0 else 0.0
    
    def _calculate_wilcoxon_for_row(self, row: pd.Series) -> Dict:
        """
        Расчет статистики Уилкоксона для одной подгруппы
        
        Parameters:
        -----------
        row : pd.Series
            Данные подгруппы
        
        Returns:
        --------
        Dict: Статистики
            - n: количество ненулевых отклонений
            - w: статистика W (сумма знако-рангов)
            - w_plus: сумма положительных рангов
            - w_minus: сумма отрицательных рангов
            - positive: количество положительных отклонений
            - negative: количество отрицательных отклонений
            - zero: количество нулевых отклонений
        """
        values = row.dropna().values
        if len(values) == 0:
            return {'n': 0, 'w': 0, 'w_plus': 0, 'w_minus': 0,
                    'positive': 0, 'negative': 0, 'zero': 0}
        
        deviations = values - self.target_value
        non_zero = deviations[deviations != 0]
        
        if len(non_zero) == 0:
            return {'n': 0, 'w': 0, 'w_plus': 0, 'w_minus': 0,
                    'positive': 0, 'negative': 0, 'zero': len(values)}
        
        # Ранжирование абсолютных отклонений
        abs_dev = np.abs(non_zero)
        ranks = stats.rankdata(abs_dev)
        signs = np.sign(non_zero)
        
        # Вычисление статистик
        w = np.sum(signs * ranks)
        w_plus = np.sum(ranks[signs > 0])
        w_minus = -np.sum(ranks[signs < 0])
        
        return {
            'n': len(non_zero),
            'w': w,
            'w_plus': w_plus,
            'w_minus': w_minus,
            'positive': np.sum(signs > 0),
            'negative': np.sum(signs < 0),
            'zero': len(values) - len(non_zero)
        }
    
    def calculate_limits(self, alpha: Optional[float] = None) -> Dict:
        """
        Расчет контрольных границ
        
        Parameters:
        -----------
        alpha : float, optional
            Уровень значимости
        
        Returns:
        --------
        Dict: Контрольные границы и параметры
            - CL: 0
            - UCL: Верхняя граница
            - LCL: Нижняя граница
            - target_value: Целевое значение
            - alpha: Уровень значимости
            - std_w: Стандартное отклонение W
            - n_eff: Эффективный размер подгруппы
            - limit_type: Тип границ ('exact' или 'normal_approximation')
        """
        if alpha is not None:
            self.alpha = alpha
        
        subgroup_data = self.data.iloc[:, :self.sample_size]
        
        # Расчет статистик для каждой подгруппы
        results = []
        for idx in range(len(subgroup_data)):
            row = subgroup_data.iloc[idx]
            result = self._calculate_wilcoxon_for_row(row)
            result['subgroup'] = idx + 1
            results.append(result)
        
        self.subgroups = pd.DataFrame(results)
        
        # Эффективный размер подгруппы (среднее количество ненулевых отклонений)
        n_eff = int(np.round(self.subgroups['n'].mean())) if self.subgroups['n'].mean() > 0 else self.sample_size
        
        # Теоретическая дисперсия W при H₀
        var_w = n_eff * (n_eff + 1) * (2 * n_eff + 1) / 6
        std_w = np.sqrt(var_w)
        
        cl = 0
        
        # Выбор метода расчета границ
        if self.use_exact and n_eff <= 20:
            # Точные границы для малых n
            max_w = n_eff * (n_eff + 1) // 2
            for w in range(0, max_w + 1):
                if w == 0:
                    p_value = 1.0
                else:
                    # Приблизительный расчет p-значения
                    p_value = 2 * sum(comb(n_eff, k) * (0.5 ** n_eff) for k in range(w, n_eff + 1))
                if p_value <= self.alpha:
                    ucl = w
                    lcl = -w
                    limit_type = 'exact'
                    break
            else:
                ucl = max_w
                lcl = -max_w
                limit_type = 'exact'
        else:
            # Нормальная аппроксимация
            z_critical = stats.norm.ppf(1 - self.alpha / 2)
            ucl = z_critical * std_w
            lcl = -z_critical * std_w
            limit_type = 'normal_approximation'
        
        self.control_limits = {
            'CL': cl,
            'UCL': ucl,
            'LCL': lcl,
            'target_value': self.target_value,
            'alpha': self.alpha,
            'std_w': std_w,
            'n_eff': n_eff,
            'limit_type': limit_type
        }
        
        self._find_violations()
        return self.control_limits
    
    def _find_violations(self):
        """Поиск нарушений на карте знако-ранговых сумм"""
        self.violations = []
        if self.subgroups is None or self.control_limits is None:
            return
        
        ucl = self.control_limits['UCL']
        lcl = self.control_limits['LCL']
        
        for _, row in self.subgroups.iterrows():
            if row['w'] > ucl or row['w'] < lcl:
                self.violations.append({
                    'subgroup': row['subgroup'],
                    'value': row['w'],
                    'rule': f'Выход за контрольные границы (|W| > {ucl:.2f})'
                })
    
    def plot(self, figsize=(14, 8), save_path: Optional[str] = None,
             show_zones: bool = True, title: Optional[str] = None,
             show_values: bool = True, value_format: str = '{:.1f}',
             value_fontsize: int = 9, value_offset: tuple = (0, 0.5)) -> Tuple[plt.Figure, plt.Axes]:
        """
        Построение графика карты знако-ранговых сумм
        
        Returns:
        --------
        Tuple[plt.Figure, plt.Axes]: Фигура и оси графика
        """
        if self.control_limits is None:
            self.calculate_limits()
        
        fig, ax = plt.subplots(figsize=figsize)
        
        subgroups = self.subgroups['subgroup'].values
        values = self.subgroups['w'].values
        
        ax.plot(subgroups, values, 'o-', color=self.color,
                markersize=8, linewidth=1.5,
                label='W = Σ sign(d) · rank(|d|)')
        
        cl = self.control_limits['CL']
        ucl = self.control_limits['UCL']
        lcl = self.control_limits['LCL']
        
        self._add_control_lines(ax, cl, ucl, lcl)
        
        if show_zones and ucl > cl:
            self._add_zones(ax, cl, ucl, lcl)
        
        if self.violations:
            v_subgroups = [v['subgroup'] for v in self.violations]
            v_values = [v['value'] for v in self.violations]
            ax.scatter(v_subgroups, v_values, color='red', s=150, zorder=5,
                      marker='o', label='Нарушения')
        
        if show_values:
            for x, y in zip(subgroups, values):
                color = 'red' if (y > ucl or y < lcl) else 'black'
                ax.text(x + value_offset[0], y + value_offset[1], value_format.format(y),
                       fontsize=value_fontsize, color=color,
                       ha='center', va='bottom' if value_offset[1] >= 0 else 'top',
                       bbox=dict(boxstyle='round,pad=0.2',
                               facecolor='white', edgecolor='none', alpha=0.7))
        
        ax.set_xlabel('Номер подгруппы', fontsize=12)
        ax.set_ylabel('W = Σ sign(d) · rank(|d|)', fontsize=12)
        
        if title is None:
            title = f'Карта знако-ранговых сумм (n={self.sample_size})'
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        ax.legend(loc='upper right')
        ax.grid(alpha=0.3)
        
        info_text = (
            f"μ₀: {self.target_value:.4f}\n"
            f"Тип границ: {self.control_limits['limit_type']}\n"
            f"σ_W: {self.control_limits['std_w']:.3f}\n"
            f"Подгрупп: {len(self.subgroups)}\n"
            f"Нарушений: {len(self.violations)}"
        )
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
                fontsize=9, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"График сохранен: {save_path}")
        
        return fig, ax
    
    def get_wilcoxon_test(self) -> Dict:
        """
        Выполнение теста Уилкоксона для проверки гипотезы о медиане
        
        H₀: медиана = target_value
        H₁: медиана ≠ target_value
        
        Returns:
        --------
        Dict: Результаты теста Уилкоксона
            - statistic: Статистика теста
            - p_value: p-значение
            - w_plus: Сумма положительных рангов
            - w_minus: Сумма отрицательных рангов
            - n: Количество наблюдений
            - target_value: Целевое значение
            - significant: Значимость результата
        """
        if self.subgroups is None:
            self.calculate_limits()
        
        # Сбор всех отклонений
        all_deviations = []
        for idx in range(len(self.data)):
            row = self.data.iloc[idx, :self.sample_size].dropna()
            deviations = row - self.target_value
            all_deviations.extend(deviations[deviations != 0].tolist())
        
        if len(all_deviations) == 0:
            return {'error': 'Нет ненулевых отклонений для теста'}
        
        # Выполнение теста Уилкоксона
        statistic, p_value = stats.wilcoxon(all_deviations, alternative='two-sided')
        
        # Вычисление W+ и W-
        abs_deviations = np.abs(all_deviations)
        ranks = stats.rankdata(abs_deviations)
        signs = np.sign(all_deviations)
        
        w_plus = np.sum(ranks[signs > 0])
        w_minus = np.sum(ranks[signs < 0])
        
        return {
            'statistic': statistic,
            'p_value': p_value,
            'w_plus': w_plus,
            'w_minus': w_minus,
            'n': len(all_deviations),
            'target_value': self.target_value,
            'significant': p_value < self.significance_level
        }
    
    def print_calculation_table(self, max_subgroups: int = 10):
        """
        Вывод таблицы расчетов для каждой подгруппы
        
        Parameters:
        -----------
        max_subgroups : int, default=10
            Максимальное количество подгрупп для отображения
        """
        if self.subgroups is None:
            self.calculate_limits()
        
        print(f"\n{'='*80}")
        print(f"ТАБЛИЦА РАСЧЕТОВ W ДЛЯ КАЖДОЙ ПОДГРУППЫ")
        print(f"{'='*80}")
        print(f"{'№':>4} | {'n':>4} | {'W+':>8} | {'W-':>8} | {'W':>8} | {'Статус':>10}")
        print(f"{'-'*4}-+-{'-'*4}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*10}")
        
        ucl = self.control_limits['UCL']
        lcl = self.control_limits['LCL']
        
        for idx, row in self.subgroups.iterrows():
            if idx >= max_subgroups:
                print(f"... и еще {len(self.subgroups) - max_subgroups} подгрупп")
                break
            
            subgroup = row['subgroup']
            n = row['n']
            w_plus = row['w_plus']
            w_minus = row['w_minus']
            w = row['w']
            
            if w > ucl or w < lcl:
                status = '⚠️ НАРУШЕНИЕ'
            else:
                status = '✅ OK'
            
            print(f"{subgroup:>4} | {n:>4} | {w_plus:>8.1f} | {w_minus:>8.1f} | {w:>8.1f} | {status:>10}")
        
        print(f"{'-'*4}-+-{'-'*4}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*10}")
        
        if self.control_limits is not None:
            print(f"\nКонтрольные границы: UCL = {ucl:.2f}, LCL = {lcl:.2f}")
            print(f"Тип границ: {self.control_limits['limit_type']}")
    
    def get_rank_matrix(self) -> pd.DataFrame:
        """
        Получение матрицы рангов для всех подгрупп
        
        Returns:
        --------
        pd.DataFrame: Матрица рангов (положительные и отрицательные)
        """
        if self.subgroups is None:
            self.calculate_limits()
        
        rank_matrix = []
        for idx in range(len(self.data)):
            row = self.data.iloc[idx, :self.sample_size].dropna()
            deviations = row - self.target_value
            non_zero = deviations[deviations != 0]
            
            if len(non_zero) == 0:
                rank_matrix.append([0] * self.sample_size)
                continue
            
            abs_deviations = np.abs(non_zero)
            ranks = stats.rankdata(abs_deviations)
            
            full_ranks = np.zeros(self.sample_size)
            non_zero_indices = deviations.index[deviations != 0]
            signs = np.sign(non_zero)
            
            for i, (idx_col, rank, sign) in enumerate(zip(non_zero_indices, ranks, signs)):
                col_pos = int(idx_col.replace('x', '')) - 1 if 'x' in idx_col else int(idx_col)
                full_ranks[col_pos] = sign * rank
            
            rank_matrix.append(full_ranks.tolist())
        
        columns = [f'x{i+1}' for i in range(self.sample_size)]
        df_ranks = pd.DataFrame(rank_matrix, columns=columns)
        df_ranks.insert(0, 'subgroup', range(1, len(df_ranks) + 1))
        return df_ranks
    
    def get_summary(self) -> Dict:
        """
        Получение сводной информации о карте знако-ранговых сумм
        
        Returns:
        --------
        Dict: Сводная информация
            - chart_type: 'Signed Rank'
            - target_value: Целевое значение
            - ucl, lcl: Контрольные границы
            - limit_type: Тип границ
            - sample_size: Размер подгруппы
            - total_subgroups: Количество подгрупп
            - total_violations: Количество нарушений
            - mean_w: Среднее значение W
            - violations: Список нарушений
        """
        if self.control_limits is None:
            self.calculate_limits()
        
        total = len(self.subgroups)
        
        return {
            'chart_type': 'Signed Rank',
            'target_value': self.target_value,
            'ucl': self.control_limits['UCL'],
            'lcl': self.control_limits['LCL'],
            'limit_type': self.control_limits['limit_type'],
            'sample_size': self.sample_size,
            'total_subgroups': total,
            'total_violations': len(self.violations),
            'mean_w': self.subgroups['w'].mean(),
            'violations': self.violations
        }