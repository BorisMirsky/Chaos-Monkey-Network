import asyncio
import logging
from typing import Optional, List

from chaos_proxy.chaos import DelayInjector
from chaos_proxy.chaos import DelayInjector, PacketLossInjector
from chaos_proxy.chaos import DelayInjector, PacketLossInjector, RuleEngine
from chaos_proxy.stats import StatsCollector, StatsDisplay





logger = logging.getLogger(__name__)


class ChaosProxy:
    """Основной класс прокси-сервера"""

    def __init__(self, target_host: str, target_port: int, listen_port: int,
                 fixed_delay: float = 0.0, min_delay: float = 0.0, max_delay: float = 0.0,
                 loss_rate: float = 0.0, rules: Optional[List] = None,
                 enable_stats: bool = True):
        self.target_host = target_host
        self.target_port = target_port
        self.listen_port = listen_port
        self.fixed_delay = fixed_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.loss_rate = loss_rate
        self.rules = rules or []
        self.server: Optional[asyncio.Server] = None
        self._running = False
        self._active_connections = set()
        self.enable_stats = enable_stats
        self.stats_collector = StatsCollector() if enable_stats else None
        self.stats_display: Optional[StatsDisplay] = None

    async def start(self):
        """Запуск прокси-сервера"""
        self._running = True
        if self.enable_stats and self.stats_display:
            await self.stats_display.start()
        self.server = await asyncio.start_server(
            self._handle_client,
            host="127.0.0.1",
            port=self.listen_port,
        )
        logger.info(f"Прокси запущен на 127.0.0.1:{self.listen_port} -> {self.target_host}:{self.target_port}")
        await self.server.serve_forever()

    async def stop(self):
        """Остановка прокси-сервера"""
        self._running = False
        if self.stats_display:
            await self.stats_display.stop()
        # Закрываем все активные соединения
        for task in self._active_connections:
            task.cancel()
        if self._active_connections:
            await asyncio.gather(*self._active_connections, return_exceptions=True)
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("Прокси остановлен")

    async def _handle_client(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        """Обработка одного клиентского подключения"""
        client_addr = client_writer.get_extra_info("peername")
        logger.debug(f"Новое подключение от {client_addr}")

        target_reader = None
        target_writer = None
        
        try:
            # Подключаемся к целевому серверу
            target_reader, target_writer = await asyncio.open_connection(
                self.target_host, self.target_port
            )
            logger.debug(f"Подключение к {self.target_host}:{self.target_port} установлено")

            # Создаём задачи для двунаправленной передачи
            # Получаем порт клиента
            client_port = client_writer.get_extra_info("peername")[1]
            
            task_client_to_target = asyncio.create_task(
                self._forward_data(client_reader, target_writer, "client->target", client_port)
            )
            task_target_to_client = asyncio.create_task(
                self._forward_data(target_reader, client_writer, "target->client", client_port)
            )



            # Добавляем задачи в множество активных
            self._active_connections.add(task_client_to_target)
            self._active_connections.add(task_target_to_client)
            
            # Ждём завершения любой из задач (или обеих)
            done, pending = await asyncio.wait(
                [task_client_to_target, task_target_to_client],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Отменяем оставшиеся задачи
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Удаляем задачи из множества
            self._active_connections.discard(task_client_to_target)
            self._active_connections.discard(task_target_to_client)

        except ConnectionRefusedError:
            logger.error(f"Не удалось подключиться к {self.target_host}:{self.target_port}")
        except asyncio.CancelledError:
            logger.debug(f"Подключение от {client_addr} отменено")
        except Exception as e:
            logger.error(f"Ошибка при обработке клиента {client_addr}: {e}")
        finally:
            # Закрываем соединения
            if target_writer:
                target_writer.close()
                await target_writer.wait_closed()
            client_writer.close()
            await client_writer.wait_closed()
            logger.debug(f"Подключение от {client_addr} закрыто")


    async def _forward_data(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        direction: str,
        client_port: int
    ):
        """Пересылка данных с задержками, потерями и статистикой"""
        import time
        
        delay_injector = DelayInjector(
            fixed_delay=self.fixed_delay,
            min_delay=self.min_delay,
            max_delay=self.max_delay
        )
        loss_injector = PacketLossInjector(self.loss_rate)
        rule_engine = RuleEngine(self.rules) if self.rules else None
        
        try:
            while self._running:
                data = await reader.read(4096)
                if not data:
                    break

                should_apply = True
                if rule_engine:
                    should_apply = rule_engine.should_apply_chaos(
                        data, direction, self.target_port, client_port
                    )
                
                lost = False
                delay_applied = 0.0
                original_size = len(data)
                
                if should_apply:
                    start_time = time.time()
                    
                    # Потеря пакетов
                    data = await loss_injector.apply(data, direction)
                    if data is None:
                        lost = True
                    
                    # Задержка
                    if data and delay_injector.has_delay():
                        data = await delay_injector.apply(data, direction)
                    
                    delay_applied = time.time() - start_time
                
                # Запись статистики
                if self.stats_collector and data is not None:
                    self.stats_collector.record_packet(
                        direction, original_size, lost=lost, delay=delay_applied
                    )
                
                # Отправка
                if data is not None:
                    writer.write(data)
                    await writer.drain()

        except Exception as e:
            logger.debug(f"{direction}: ошибка {e}")