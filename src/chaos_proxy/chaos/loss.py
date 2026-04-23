import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PacketLossInjector:
    """Инжектор потери пакетов"""

    def __init__(self, loss_rate: float = 0.0):
        """
        Args:
            loss_rate: Вероятность потери пакета (0.0 - 1.0)
        """
        self.loss_rate = max(0.0, min(1.0, loss_rate))

    async def apply(self, data: bytes, direction: str = "") -> Optional[bytes]:
        """
        Применить потерю пакета.
        
        Args:
            data: Данные пакета
            direction: Направление (для логирования)
        
        Returns:
            Данные, если пакет не потерян, иначе None
        """
        if self.loss_rate <= 0:
            return data
        
        if random.random() < self.loss_rate:
            logger.info(f"{direction}: ПАКЕТ ПОТЕРЯН (rate={self.loss_rate})")
            return None
        
        return data

    def has_loss(self) -> bool:
        """Есть ли активная потеря пакетов"""
        return self.loss_rate > 0

    def update_rate(self, loss_rate: float):
        """Обновить вероятность потери"""
        self.loss_rate = max(0.0, min(1.0, loss_rate))