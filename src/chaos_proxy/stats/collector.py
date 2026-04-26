import time
import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Optional
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Статистика одного соединения"""
    bytes_sent: int = 0
    bytes_received: int = 0
    packets_sent: int = 0
    packets_received: int = 0
    packets_lost: int = 0
    total_delay: float = 0.0


class StatsCollector:
    """Сборщик статистики по всем соединениям"""

    def __init__(self, history_size: int = 100):
        self.history_size = history_size
        self._total_bytes_sent = 0
        self._total_bytes_received = 0
        self._total_packets_sent = 0
        self._total_packets_received = 0
        self._total_packets_lost = 0
        self._total_delay = 0.0
        self._start_time = time.time()
        self._recent_rates = deque(maxlen=history_size)  # (timestamp, bytes_sent, bytes_recv)

    def record_packet(self, direction: str, size: int, lost: bool = False, delay: float = 0.0):
        """Записать информацию о пакете"""
        now = time.time()
        
        if direction == "client->target":
            self._total_packets_sent += 1
            self._total_bytes_sent += size
            self._total_delay += delay
            if lost:
                self._total_packets_lost += 1
        else:
            self._total_packets_received += 1
            self._total_bytes_received += size
        
        # Для расчёта скорости
        self._recent_rates.append((now, self._total_bytes_sent, self._total_bytes_received))

    def get_stats(self) -> Dict:
        """Получить текущую статистику"""
        elapsed = time.time() - self._start_time
        
        # Расчёт скорости за последний период (через разницу в очереди)
        sent_rate = 0.0
        recv_rate = 0.0
        if len(self._recent_rates) >= 2:
            t1, b1_sent, b1_recv = self._recent_rates[0]
            t2, b2_sent, b2_recv = self._recent_rates[-1]
            dt = max(t2 - t1, 0.001)
            sent_rate = (b2_sent - b1_sent) / dt
            recv_rate = (b2_recv - b1_recv) / dt
        
        loss_rate = 0.0
        if self._total_packets_sent > 0:
            loss_rate = self._total_packets_lost / self._total_packets_sent
        
        return {
            "uptime": elapsed,
            "total_bytes_sent": self._total_bytes_sent,
            "total_bytes_received": self._total_bytes_received,
            "total_packets_sent": self._total_packets_sent,
            "total_packets_received": self._total_packets_received,
            "total_packets_lost": self._total_packets_lost,
            "loss_rate": loss_rate,
            "avg_delay": self._total_delay / max(self._total_packets_sent, 1),
            "send_rate_bps": sent_rate,
            "recv_rate_bps": recv_rate,
        }

    def reset(self):
        """Сбросить статистику"""
        self._total_bytes_sent = 0
        self._total_bytes_received = 0
        self._total_packets_sent = 0
        self._total_packets_received = 0
        self._total_packets_lost = 0
        self._total_delay = 0.0
        self._start_time = time.time()
        self._recent_rates.clear()