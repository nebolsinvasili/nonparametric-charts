import os
import pandas as pd
import numpy as np
from typing import Optional, List, Tuple, Dict, Any
import re


class DataLoader:
    """
    Класс для загрузки данных из файлов с автоматическим преобразованием чисел
    """
    
    def __init__(self, file_path: str, separator: Optional[str] = None,
                 header: int = 0, encoding: str = 'utf-8',
                 decimal: str = ','):
        """
        Инициализация загрузчика данных
        
        Parameters:
        -----------
        file_path : str
            Путь к файлу с данными
        separator : str, optional
            Разделитель в файле (автоопределение если None)
        header : int
            Строка с заголовками (0 - первая строка)
        encoding : str
            Кодировка файла
        decimal : str
            Десятичный разделитель (',' или '.')
        """
        self.file_path = file_path
        self.separator = separator
        self.header = header
        self.encoding = encoding
        self.decimal = decimal
        
        self.raw_data = None
        self._detected_encoding = None
        self._detected_separator = None
        self._numeric_columns = []
        
    def load(self) -> pd.DataFrame:
        """
        Загрузка данных из файла с автоматическим преобразованием в числа
        
        Returns:
        --------
        pd.DataFrame: Загруженные данные с числовыми значениями
        """
        # Проверка существования файла
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Файл {self.file_path} не найден")
        
        # Определение разделителя
        if self.separator is None:
            self._detected_separator = self._detect_separator()
        else:
            self._detected_separator = self.separator
        
        # Загрузка данных как строк
        self.raw_data = self._load_raw_data()
        
        # Преобразование данных в числовой формат
        self._convert_to_numeric()
        
        return self.raw_data
    
    def _load_raw_data(self) -> pd.DataFrame:
        """
        Загрузка сырых данных без преобразования типов
        """
        encodings = [self.encoding, 'utf-8', 'cp1251', 'latin1', 'utf-16', 'cp866']
        last_error = None
        
        for enc in encodings:
            try:
                # Загружаем все как строки, чтобы контролировать преобразование
                df = pd.read_csv(
                    self.file_path,
                    sep=self._detected_separator,
                    header=self.header,
                    encoding=enc,
                    dtype=str,
                    keep_default_na=False
                )
                self._detected_encoding = enc
                return df
            except Exception as e:
                last_error = e
                continue
        
        raise ValueError(f"Не удалось загрузить файл. Последняя ошибка: {last_error}")
    
    def _convert_to_numeric(self):
        """
        Преобразование строк в числовые значения
        """
        if self.raw_data is None:
            return
        
        # Проходим по всем колонкам
        for col in self.raw_data.columns:
            # Пробуем преобразовать колонку в числа
            try:
                # Заменяем запятую на точку для десятичных чисел
                if self.decimal == ',':
                    # Удаляем пробелы и заменяем запятую на точку
                    self.raw_data[col] = self.raw_data[col].str.replace(' ', '', regex=False)
                    self.raw_data[col] = self.raw_data[col].str.replace(',', '.', regex=False)
                
                # Преобразуем в числовой тип
                self.raw_data[col] = pd.to_numeric(self.raw_data[col], errors='coerce')
                
                # Если преобразование прошло успешно, добавляем в список числовых колонок
                self._numeric_columns.append(col)
                
            except Exception as e:
                # Если не удалось преобразовать, оставляем как строку
                pass
    
    def _detect_separator(self) -> str:
        """
        Автоматическое определение разделителя в файле
        """
        try:
            with open(self.file_path, 'r', encoding=self.encoding) as f:
                first_line = f.readline()
        except UnicodeDecodeError:
            # Пробуем другие кодировки
            for enc in ['cp1251', 'latin1', 'utf-16']:
                try:
                    with open(self.file_path, 'r', encoding=enc) as f:
                        first_line = f.readline()
                        self.encoding = enc
                        break
                except:
                    continue
            else:
                raise ValueError("Не удалось определить кодировку файла")
        
        separators = ['\t', ';', ',', '|']
        counts = {}
        
        # Ищем разделители, игнорируя запятые в числах
        for sep in separators:
            if sep == ',':
                # Для запятой считаем только те, которые не являются частью чисел
                # (упрощенно: считаем запятые, после которых есть пробел или конец строки)
                pattern = r',(?=\s|$)'
                counts[sep] = len(re.findall(pattern, first_line))
            else:
                counts[sep] = first_line.count(sep)
        
        # Выбираем разделитель с максимальным количеством вхождений
        max_sep = max(counts, key=counts.get)
        
        # Если разделитель не найден
        if counts[max_sep] == 0:
            return ','  # По умолчанию запятая
        
        return max_sep
    
    def get_numeric_columns(self) -> List[str]:
        """Получение списка числовых колонок"""
        return self._numeric_columns
    
    def get_detected_encoding(self) -> Optional[str]:
        """Получение определенной кодировки"""
        return self._detected_encoding
    
    def get_detected_separator(self) -> Optional[str]:
        """Получение определенного разделителя"""
        return self._detected_separator
    
    def __repr__(self) -> str:
        """Строковое представление"""
        return (f"DataLoader(file='{self.file_path}', "
                f"separator='{self.separator or 'auto'}', "
                f"encoding='{self.encoding}', "
                f"decimal='{self.decimal}')")


