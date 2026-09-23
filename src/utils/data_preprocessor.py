import os
import pandas as pd
import numpy as np
from typing import Optional, List, Tuple, Dict, Any
import re

from .data_loader import DataLoader


class DataPreprocessor:
    """
    Класс для предобработки и подготовки данных
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        Инициализация препроцессора данных
        
        Parameters:
        -----------
        data : pd.DataFrame
            Исходные данные для обработки
        """
        self.original_data = data.copy()
        self.processed_data = data.copy()
        self.sample_size = 0
        self.num_subgroups = 0
        self.data_columns = []
        self.index_column = None
        
        # Выполняем базовую предобработку
        self._detect_parameters()
    
    def _detect_parameters(self):
        """
        Автоматическое определение параметров данных
        """
        if self.processed_data is None:
            return
        
        # Определяем колонки с данными (исключая индексный столбец)
        self.data_columns = self._get_data_columns()
        
        # Определяем размер подгруппы (количество измерений)
        self.sample_size = len(self.data_columns)
        
        # Определяем количество подгрупп
        self.num_subgroups = self.processed_data.shape[0]
        
        # Определяем столбец с индексами
        self._detect_index_column()
    
    def _detect_index_column(self):
        """
        Определение столбца с индексами подгрупп
        """
        if self.processed_data is None or len(self.processed_data.columns) == 0:
            return
        
        first_col = self.processed_data.columns[0]
        if self._is_index_column(first_col):
            self.index_column = first_col
    
    def _get_data_columns(self) -> List[str]:
        """
        Получение списка колонок с данными (исключая столбец с номерами)
        """
        if self.processed_data is None or len(self.processed_data.columns) == 0:
            return []
        
        first_col = self.processed_data.columns[0]
        
        # Проверяем, является ли первый столбец столбцом с номерами
        if self._is_index_column(first_col):
            return list(self.processed_data.columns[1:])
        
        return list(self.processed_data.columns)
    
    def _is_index_column(self, col: str) -> bool:
        """
        Проверка, является ли столбец индексным (номера подгрупп)
        """
        values = self.processed_data[col].dropna()
        if len(values) == 0:
            return False
        
        # Проверяем, что значения числовые
        try:
            values = pd.to_numeric(values)
        except:
            return False
        
        # Проверяем, что значения - это последовательные числа, начиная с 1
        if len(values) > 0:
            # Проверяем первые несколько значений
            check_count = min(10, len(values))
            expected = list(range(1, check_count + 1))
            actual = values.iloc[:check_count].tolist()
            
            # Проверяем с допуском на возможные несоответствия
            if all(abs(actual[i] - expected[i]) < 0.01 for i in range(check_count)):
                return True
        
        return False
    
    def get_processed_data(self) -> pd.DataFrame:
        """Получение обработанных данных"""
        return self.processed_data
    
    def get_original_data(self) -> pd.DataFrame:
        """Получение оригинальных данных"""
        return self.original_data
    
    def get_data_for_chart(self, remove_index_col: bool = True) -> Tuple[pd.DataFrame, int]:
        """
        Получение данных для построения контрольной карты
        
        Returns:
        --------
        Tuple[pd.DataFrame, int]: (Данные, размер подгруппы)
        """
        if self.processed_data is None:
            raise ValueError("Данные не обработаны")
        
        df = self.processed_data.copy()
        
        # Удаляем столбец с индексами, если он есть
        if remove_index_col and self.index_column is not None:
            df = df.drop(columns=[self.index_column])
        
        return df, self.sample_size
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики по данным
        """
        if self.processed_data is None:
            raise ValueError("Данные не обработаны")
        
        data_values = self.processed_data[self.data_columns]
        
        stats = {
            'sample_size': self.sample_size,
            'num_subgroups': self.num_subgroups,
            'num_measurements': len(self.data_columns),
            'total_cells': self.num_subgroups * len(self.data_columns),
            'empty_cells': data_values.isna().sum().sum(),
            'index_column': self.index_column,
            'data_columns': self.data_columns,
            'column_stats': {}
        }
        
        # Статистика по каждой колонке
        for col in self.data_columns:
            col_data = data_values[col].dropna()
            if len(col_data) > 0:
                stats['column_stats'][col] = {
                    'mean': col_data.mean(),
                    'median': col_data.median(),
                    'std': col_data.std(),
                    'min': col_data.min(),
                    'max': col_data.max(),
                    'q1': col_data.quantile(0.25),
                    'q3': col_data.quantile(0.75),
                    'count': len(col_data),
                    'missing': data_values[col].isna().sum()
                }
        
        # Общая статистика
        all_values = data_values.values.flatten()
        all_values = all_values[~np.isnan(all_values)]
        if len(all_values) > 0:
            stats['overall'] = {
                'mean': np.mean(all_values),
                'median': np.median(all_values),
                'std': np.std(all_values),
                'min': np.min(all_values),
                'max': np.max(all_values),
                'q1': np.percentile(all_values, 25),
                'q3': np.percentile(all_values, 75)
            }
        
        return stats
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Получение краткой сводки по данным
        """
        return {
            'sample_size': self.sample_size,
            'num_subgroups': self.num_subgroups,
            'num_measurements': len(self.data_columns),
            'data_columns': self.data_columns,
            'index_column': self.index_column,
            'data_shape': self.processed_data.shape,
            'missing_values': self.processed_data.isna().sum().sum()
        }
    
    def __repr__(self) -> str:
        """Строковое представление"""
        return (f"DataPreprocessor(n_subgroups={self.num_subgroups}, "
                f"sample_size={self.sample_size}, "
                f"n_columns={len(self.data_columns)})")


class DataPipeline:
    """
    Класс-конвейер для загрузки и предобработки данных
    """
    
    def __init__(self, file_path: str, separator: Optional[str] = None,
                 header: int = 0, encoding: str = 'utf-8',
                 decimal: str = ','):
        """
        Инициализация конвейера обработки данных
        """
        self.loader = DataLoader(file_path, separator, header, encoding, decimal)
        self.preprocessor = None
        self._loaded = False
    
    def load_and_process(self) -> 'DataPipeline':
        """
        Загрузка и предобработка данных
        """
        # Загрузка данных
        data = self.loader.load()
        
        # Предобработка
        self.preprocessor = DataPreprocessor(data)
        self._loaded = True
        
        return self
    
    def get_data_for_chart(self, remove_index_col: bool = True) -> Tuple[pd.DataFrame, int]:
        """
        Получение данных для построения контрольной карты
        """
        if not self._loaded or self.preprocessor is None:
            raise ValueError("Данные не загружены. Сначала вызовите load_and_process()")
        
        return self.preprocessor.get_data_for_chart(remove_index_col)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики по данным"""
        if not self._loaded or self.preprocessor is None:
            raise ValueError("Данные не загружены. Сначала вызовите load_and_process()")
        
        return self.preprocessor.get_statistics()
    
    def get_loader(self) -> DataLoader:
        """Получение загрузчика данных"""
        return self.loader
    
    def get_preprocessor(self) -> DataPreprocessor:
        """Получение препроцессора данных"""
        return self.preprocessor
    
    def __repr__(self) -> str:
        """Строковое представление"""
        status = "loaded" if self._loaded else "not loaded"
        return f"DataPipeline(file='{self.loader.file_path}', status='{status}')"
    