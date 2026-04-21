import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ChaosProxy:
    """Основной класс прокси-сервера"""

    def __init__(self, target_host: str, target_port: int, listen_port: int):
        self.target_host = target_host
        self.target_port = target_port
        self.listen_port = listen_port
        self.server: Optional[asyncio.Server] = None
        self._running = False
        self._active_connections = set()

    async def start(self):
        """Запуск прокси-сервера"""
        self._running = True
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
            task_client_to_target = asyncio.create_task(
                self._forward_data(client_reader, target_writer, "client->target")
            )
            task_target_to_client = asyncio.create_task(
                self._forward_data(target_reader, client_writer, "target->client")
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
        direction: str
    ):
        """Пересылка данных из reader в writer"""
        try:
            while self._running:
                # Читаем данные
                data = await reader.read(4096)
                if not data:
                    logger.debug(f"{direction}: соединение закрыто (EOF)")
                    break

                logger.debug(f"{direction}: получено {len(data)} байт")

                # Отправляем данные (пока без изменений)
                writer.write(data)
                await writer.drain()

        except ConnectionResetError:
            logger.debug(f"{direction}: соединение сброшено клиентом")
        except asyncio.CancelledError:
            logger.debug(f"{direction}: задача отменена")
        except Exception as e:
            logger.error(f"{direction}: ошибка {e}")