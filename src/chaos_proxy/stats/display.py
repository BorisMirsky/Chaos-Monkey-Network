import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class StatsDisplay:
    """Отображение статистики в реальном времени"""

    def __init__(self, collector, refresh_interval: float = 1.0):
        self.collector = collector
        self.refresh_interval = refresh_interval
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Запустить обновление статистики"""
        self._running = True
        self._task = asyncio.create_task(self._display_loop())

    async def stop(self):
        """Остановить обновление статистики"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _display_loop(self):
        """Цикл обновления статистики в консоли"""
        while self._running:
            stats = self.collector.get_stats()
            self._print_stats(stats)
            await asyncio.sleep(self.refresh_interval)

    def _print_stats(self, stats: dict):
        """Вывести статистику в консоль"""
        # Очищаем предыдущие N строк (простой способ — не очищать, а выводить каждую секунду)
        uptime = stats["uptime"]
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        
        # Форматирование скоростей
        def format_rate(rate: float) -> str:
            if rate > 1024 * 1024:
                return f"{rate / 1024 / 1024:.1f} MB/s"
            elif rate > 1024:
                return f"{rate / 1024:.1f} KB/s"
            else:
                return f"{rate:.1f} B/s"
        
        print("\n" + "=" * 60)
        print(f"Статистика Chaos Proxy (время работы: {hours:02d}:{minutes:02d}:{seconds:02d})")
        print("=" * 60)
        print(f"Отправлено:   {stats['total_packets_sent']} пакетов ({format_rate(stats['send_rate_bps'])})")
        print(f"Получено:     {stats['total_packets_received']} пакетов")
        print(f"Потеряно:     {stats['total_packets_lost']} пакетов ({stats['loss_rate']*100:.1f}%)")
        print(f"Средняя задержка: {stats['avg_delay']*1000:.1f} мс")
        print(f"Всего данных: {stats['total_bytes_sent'] / 1024:.1f} KB отправлено, "
              f"{stats['total_bytes_received'] / 1024:.1f} KB получено")
        print("=" * 60)