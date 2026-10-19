"""
Базовый абстрактный класс для контрольных карт Шухарта

Этот модуль определяет общий интерфейс для всех контрольных карт:
- Единый API для расчета границ, построения графиков и получения сводок
- Загрузка коэффициентов Шухарта
- Вспомогательные методы для визуализации
- Поиск нарушений по правилам Вестерн-Электрик
"""

import os
import json
from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Tuple, Any
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


class BaseControlChart(ABC):
    """
    Базовый абстрактный класс для контрольных карт Шухарта
    
    Определяет единый интерфейс для всех контрольных карт:
    - calculate_limits() - расчет контрольных границ
    - plot() - построение графика
    - get_summary() - получение сводной информации
    - get_data() - получение данных подгрупп
    
    Attributes:
    -----------
    data : pd.DataFrame
        Исходные данные (каждая строка - подгруппа)
    sample_size : int
        Размер подгруппы (n)
    subgroups : pd.DataFrame
        Рассчитанные статистики по подгруппам
    control_limits : Dict
        Контрольные границы
    violations : List[Dict]
        Список нарушений
    chart_type : str
        Тип карты
    coefficients : Dict
        Коэффициенты Шухарта
    """
    
    def __init__(self, data: pd.DataFrame, sample_size: int, 
                 coefficients_file: Optional[str] = None):
        """
        Инициализация базовой контрольной карты
        
        Parameters:
        -----------
        data : pd.DataFrame
            Данные для построения карты (каждая строка - подгруппа)
        sample_size : int
            Размер подгруппы (n)
        coefficients_file : str, optional
            Путь к файлу с коэффициентами
        """
        self.data = data
        self.sample_size = sample_size
        self.subgroups = None
        self.control_limits = None
        self.violations = []
        self.chart_type = "Base"
        self.color = '#2E86AB'
        
        # Загрузка коэффициентов
        self.coefficients = self._load_coefficients(coefficients_file)
        
        # Настройка стиля для графиков
        self._setup_style()
    
    def _load_coefficients(self, file_path: Optional[str] = None) -> Dict:
        """
        Загрузка коэффициентов из JSON файла
        
        Поиск файла происходит в следующем порядке:
        1. Указанный путь
        2. Переменная окружения NONPARAMETRIC_CHARTS_COEFFICIENTS
        3. Стандартные пути в проекте
        4. Текущая директория
        
        Returns:
        --------
        Dict: Словарь с коэффициентами для разных n
        """
        if file_path is None:
            file_path = os.environ.get('NONPARAMETRIC_CHARTS_COEFFICIENTS', 'coefficients.json')
        
        # Поиск файла в различных местах
        search_paths = [
            file_path,
            os.path.join('data', 'coefficients', 'coefficients.json'),
            os.path.join('..', 'data', 'coefficients', 'coefficients.json'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                        'data', 'coefficients', 'coefficients.json'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                    'utils', 'coefficients.json')
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                file_path = path
                break
        else:
            raise FileNotFoundError(
                f"Файл коэффициентов не найден. Проверьте пути: {search_paths}"
            )
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            raise ValueError(f"Ошибка парсинга JSON в файле {file_path}")
    
    def get_coefficient(self, key: str) -> float:
        """
        Получение коэффициента для заданного размера подгруппы
        
        Parameters:
        -----------
        key : str
            Ключ коэффициента ('A2', 'D3', 'D4', 'B3', 'B4', 'A4')
        
        Returns:
        --------
        float: Значение коэффициента
        
        Raises:
        -------
        ValueError: Если коэффициенты не найдены
        """
        n_str = str(self.sample_size)
        if n_str not in self.coefficients:
            raise ValueError(
                f"Коэффициенты для n={self.sample_size} не найдены. "
                f"Доступные размеры: {list(self.coefficients.keys())}"
            )
        if key not in self.coefficients[n_str]:
            raise ValueError(
                f"Коэффициент {key} не найден для n={self.sample_size}. "
                f"Доступные: {list(self.coefficients[n_str].keys())}"
            )
        return self.coefficients[n_str][key]
    
    def _setup_style(self):
        """
        Настройка стиля для отображения графиков.

        Использует минималистичный LaTeX-стиль проекта
        (:mod:`src.utils.plot_style`): serif-шрифт и математика Computer Modern,
        без «мусора», сдержанная палитра. При недоступности модуля откатывается
        к безопасным настройкам matplotlib.
        """
        try:
            from src.utils.plot_style import apply_minimal_latex_style
        except ImportError:
            apply_minimal_latex_style = None

        if apply_minimal_latex_style is not None:
            apply_minimal_latex_style()
            return

        # Fallback: базовые настройки без внешнего модуля.
        plt.style.use('default')
        plt.rcParams['font.family'] = 'serif'
        plt.rcParams['figure.dpi'] = 300
    
    @abstractmethod
    def calculate_limits(self, **kwargs) -> Dict:
        """
        Расчет контрольных границ
        
        Этот метод должен быть переопределен в каждом подклассе.
        
        Returns:
        --------
        Dict: Контрольные границы и параметры
            - CL: Центральная линия
            - UCL: Верхняя контрольная граница
            - LCL: Нижняя контрольная граница
            - Дополнительные параметры в зависимости от типа карты
        """
        pass
    
    @abstractmethod
    def plot(self, **kwargs) -> Tuple[plt.Figure, plt.Axes]:
        """
        Построение графика контрольной карты
        
        Этот метод должен быть переопределен в каждом подклассе.
        
        Parameters:
        -----------
        figsize : tuple, default=(14, 6)
            Размер фигуры
        save_path : str, optional
            Путь для сохранения графика
        show_zones : bool, default=True
            Показывать зоны Вестерн-Электрик
        title : str, optional
            Заголовок графика
        show_values : bool, default=True
            Показывать значения на точках
        value_format : str, default='{:.3f}'
            Формат отображения значений
        value_fontsize : int, default=9
            Размер шрифта для значений
        value_offset : tuple, default=(0, 0.05)
            Смещение текста значений
        
        Returns:
        --------
        Tuple[plt.Figure, plt.Axes]: Фигура и оси графика
        """
        pass
    
    @abstractmethod
    def get_summary(self) -> Dict:
        """
        Получение сводной информации о карте
        
        Этот метод должен быть переопределен в каждом подклассе.
        
        Returns:
        --------
        Dict: Сводная информация
            - chart_type: Тип карты
            - sample_size: Размер подгруппы
            - total_subgroups: Общее количество подгрупп
            - points_outside: Количество точек вне границ
            - percent_outside: Процент точек вне границ
            - violations: Список нарушений
            - Специфичные параметры для каждого типа карты
        """
        pass
    
    def get_data(self) -> pd.DataFrame:
        """Получение данных подгрупп"""
        if self.subgroups is None:
            self.calculate_limits()
        return self.subgroups.copy()
    
    def get_control_limits(self) -> Dict:
        """Получение контрольных границ"""
        if self.control_limits is None:
            self.calculate_limits()
        return self.control_limits.copy()
    
    def get_violations(self) -> List[Dict]:
        """Получение списка нарушений"""
        return self.violations.copy()
    
    def _find_violations(self):
        """
        Поиск точек вне контрольных границ
        
        Базовый метод, может быть переопределен для специфичных правил
        """
        self.violations = []
        if self.subgroups is None or self.control_limits is None:
            return
        
        ucl = self.control_limits.get('UCL')
        lcl = self.control_limits.get('LCL')
        
        if ucl is None or lcl is None:
            return
        
        for _, row in self.subgroups.iterrows():
            value = row.get('statistic')
            if value is None:
                continue
            if value > ucl or value < lcl:
                self.violations.append({
                    'subgroup': row.get('subgroup', 0),
                    'value': value,
                    'rule': 'Выход за контрольные границы'
                })
    
    def _add_control_lines(self, ax, cl: float, ucl: float, lcl: float, 
                          label_cl: str = 'CL', label_ucl: str = 'UCL', 
                          label_lcl: str = 'LCL'):
        """
        Добавление контрольных линий на график
        
        Parameters:
        -----------
        ax : matplotlib.axes.Axes
            Оси графика
        cl : float
            Центральная линия
        ucl : float
            Верхняя контрольная граница
        lcl : float
            Нижняя контрольная граница
        label_cl, label_ucl, label_lcl : str
            Метки для линий
        """
        ax.axhline(y=cl, color='green', linestyle='-', 
                   linewidth=2, label=f'{label_cl} = {cl:.3f}')
        ax.axhline(y=ucl, color='red', linestyle='--', 
                   linewidth=2, label=f'{label_ucl} = {ucl:.3f}')
        ax.axhline(y=lcl, color='red', linestyle='--', 
                   linewidth=2, label=f'{label_lcl} = {lcl:.3f}')
    
    def _add_zones(self, ax, cl: float, ucl: float, lcl: float):
        """
        Добавление зон Вестерн-Электрик
        
        Зоны:
        - Зона A: ±2σ до ±3σ (желтая)
        - Зона B: ±1σ до ±2σ (оранжевая)
        - Зона C: центр до ±1σ (светло-зеленая)
        
        Parameters:
        -----------
        ax : matplotlib.axes.Axes
            Оси графика
        cl : float
            Центральная линия
        ucl : float
            Верхняя контрольная граница
        lcl : float
            Нижняя контрольная граница
        """
        if ucl <= cl or lcl >= cl:
            return
        
        zone_width = (ucl - cl) / 3
        
        ax.axhspan(cl + 2*zone_width, ucl, alpha=0.1, color='yellow', label='Зона A (2σ…3σ)')
        ax.axhspan(lcl, cl - 2*zone_width, alpha=0.1, color='yellow')
        ax.axhspan(cl + zone_width, cl + 2*zone_width, alpha=0.1, color='orange', label='Зона B (1σ…2σ)')
        ax.axhspan(cl - 2*zone_width, cl - zone_width, alpha=0.1, color='orange')
        ax.axhspan(cl - zone_width, cl + zone_width, alpha=0.1, color='lightgreen', label='Зона C (0…1σ)')
    
    def _add_values_on_points(self, ax, x_values: np.ndarray, y_values: np.ndarray,
                             cl: float, ucl: float, lcl: float,
                             value_format: str = '{:.3f}', fontsize: int = 9,
                             offset: tuple = (0, 0.05)):
        """
        Добавление значений на точки графика
        
        Цветовая кодировка:
        - Красный: вне контрольных границ
        - Темно-оранжевый: в зоне A (2σ-3σ)
        - Оранжевый: в зоне B (1σ-2σ)
        - Темно-зеленый: в зоне C (0-1σ)
        
        Parameters:
        -----------
        ax : matplotlib.axes.Axes
            Оси графика
        x_values, y_values : np.ndarray
            Координаты точек
        cl, ucl, lcl : float
            Контрольные границы
        value_format : str
            Формат отображения
        fontsize : int
            Размер шрифта
        offset : tuple
            Смещение текста (dx, dy)
        """
        dx, dy = offset
        zone_width = (ucl - cl) / 3 if ucl > cl else 1
        
        for x, y in zip(x_values, y_values):
            # Определение зоны для цвета
            if y > ucl or y < lcl:
                color = 'red'
                weight = 'bold'
            elif y > cl + 2*zone_width or y < cl - 2*zone_width:
                color = 'darkorange'
                weight = 'bold'
            elif y > cl + zone_width or y < cl - zone_width:
                color = 'orange'
                weight = 'normal'
            else:
                color = 'darkgreen'
                weight = 'normal'
            
            ax.text(x + dx, y + dy, value_format.format(y),
                   fontsize=fontsize, color=color, fontweight=weight,
                   ha='center', va='bottom' if dy >= 0 else 'top',
                   bbox=dict(boxstyle='round,pad=0.2',
                           facecolor='white', edgecolor='none', alpha=0.7))
    
    def check_western_electric_rules(self, values: np.ndarray, 
                                     cl: float, ucl: float, lcl: float) -> List[Dict]:
        """
        Проверка правил Вестерн-Электрик
        
        Правила:
        1. Точка за пределами 3σ (контрольных границ)
        2. 2 из 3 точек в зоне A (2σ-3σ)
        3. 4 из 5 точек в зоне B (1σ-2σ)
        4. 8 точек с одной стороны от CL
        
        Parameters:
        -----------
        values : np.ndarray
            Массив значений
        cl : float
            Центральная линия
        ucl : float
            Верхняя контрольная граница
        lcl : float
            Нижняя контрольная граница
        
        Returns:
        --------
        List[Dict]: Список нарушений с указанием правила
        """
        violations = []
        n = len(values)
        
        if n < 8:
            return violations
        
        zone_width = (ucl - cl) / 3 if ucl > cl else 1
        
        # Правило 1: Точка за пределами 3σ
        for i, v in enumerate(values, 1):
            if v > ucl or v < lcl:
                violations.append({
                    'subgroup': i,
                    'value': v,
                    'rule': 'Правило 1: Точка за пределами контрольных границ'
                })
        
        # Правило 2: 2 из 3 точек в зоне A
        if zone_width > 0:
            for i in range(2, n):
                zone_a_upper = cl + 2 * zone_width
                zone_a_lower = cl - 2 * zone_width
                points_in_zone_a = 0
                for j in range(max(0, i-2), i+1):
                    if values[j] > zone_a_upper or values[j] < zone_a_lower:
                        points_in_zone_a += 1
                if points_in_zone_a >= 2:
                    violations.append({
                        'subgroup': i + 1,
                        'value': values[i],
                        'rule': f'Правило 2: 2 из 3 точек в зоне A'
                    })
        
        # Правило 3: 4 из 5 точек в зоне B
        if zone_width > 0:
            for i in range(3, n):
                zone_b_upper = cl + zone_width
                zone_b_lower = cl - zone_width
                points_in_zone_b = 0
                for j in range(max(0, i-4), i+1):
                    if values[j] > zone_b_upper or values[j] < zone_b_lower:
                        points_in_zone_b += 1
                if points_in_zone_b >= 4:
                    violations.append({
                        'subgroup': i + 1,
                        'value': values[i],
                        'rule': f'Правило 3: 4 из 5 точек в зоне B'
                    })
        
        # Правило 4: 8 точек с одной стороны от CL
        for i in range(7, n):
            above_cl = all(values[j] > cl for j in range(i-7, i+1))
            below_cl = all(values[j] < cl for j in range(i-7, i+1))
            if above_cl or below_cl:
                violations.append({
                    'subgroup': i + 1,
                    'value': values[i],
                    'rule': f'Правило 4: 8 точек с одной стороны от CL'
                })
        
        return violations