import asyncio
import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DelayInjector:
    """Инжектор задержек для пакетов"""

    def __init__(self, fixed_delay: float = 0.0, min_delay: float = 0.0, max_delay: float = 0.0):
        """
        Args:
            fixed_delay: Фиксированная задержка в секундах
            min_delay: Минимальная задержка для случайного диапазона
            max_delay: Максимальная задержка для случайного диапазона
        """
        self.fixed_delay = fixed_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._use_random = (min_delay > 0 or max_delay > 0) and fixed_delay == 0

    async def apply(self, data: bytes, direction: str = "") -> bytes:
        """
        Применить задержку к пакету.
        
        Args:
            data: Данные пакета
            direction: Направление (для логирования)
        
        Returns:
            Те же данные (без изменений)
        """
        if self.fixed_delay > 0:
            delay = self.fixed_delay
            logger.debug(f"{direction}: фиксированная задержка {delay:.3f}с")
            await asyncio.sleep(delay)
            
        elif self._use_random:
            delay = random.uniform(self.min_delay, self.max_delay)
            logger.debug(f"{direction}: случайная задержка {delay:.3f}с (диапазон {self.min_delay}-{self.max_delay})")
            await asyncio.sleep(delay)
        
        return data

    def has_delay(self) -> bool:
        """Есть ли активная задержка"""
        return self.fixed_delay > 0 or self._use_random

    def update_config(self, fixed_delay: Optional[float] = None, 
                      min_delay: Optional[float] = None, 
                      max_delay: Optional[float] = None):
        """Обновить конфигурацию задержек"""
        if fixed_delay is not None:
            self.fixed_delay = fixed_delay
        if min_delay is not None:
            self.min_delay = min_delay
        if max_delay is not None:
            self.max_delay = max_delay
        
        self._use_random = (self.min_delay > 0 or self.max_delay > 0) and self.fixed_delay == 0