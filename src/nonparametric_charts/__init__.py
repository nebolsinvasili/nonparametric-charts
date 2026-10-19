"""nonparametric-charts — непараметрические контрольные карты Шухарта.

Публичный API пакета: знаковая (:class:`SignChart`) и знаково-ранговая
(:class:`SignedRankChart`) карты Шухарта для одномерных данных процесса,
базовый класс :class:`BaseControlChart`, а также утилиты загрузки,
предобработки данных и оформления графиков.

Пакет ставится и через ``pip``, и через ``poetry``:

    pip install .
    poetry install
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("nonparametric-charts")
except PackageNotFoundError:  # запуск из исходников без установки
    __version__ = "0.1.0"

from nonparametric_charts.base.base_chart import BaseControlChart
from nonparametric_charts.charts.sign_chart import SignChart
from nonparametric_charts.charts.signed_rank_chart import SignedRankChart
from nonparametric_charts.charts.cusum_sign_chart import CusumSignChart
from nonparametric_charts.charts.cusum_signed_rank_chart import CusumSignedRankChart

__all__ = [
    "__version__",
    "BaseControlChart",
    "SignChart",
    "SignedRankChart",
    "CusumSignChart",
    "CusumSignedRankChart",
]
