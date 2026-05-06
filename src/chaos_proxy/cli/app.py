import asyncio
import logging
import signal
import typer
from typing import Optional

from chaos_proxy.core import ChaosProxy

app = typer.Typer(
    name="chaos-proxy",
    help="Эмулятор сетевых задержек и потерь пакетов (Network Chaos Monkey)",
    add_completion=False,
)

# Глобальный объект прокси
_proxy: Optional[ChaosProxy] = None

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)


@app.command()
def start(
    target: str = typer.Option(..., "--target", "-t", help="Целевой сервер (host:port)"),
    listen_port: int = typer.Option(8888, "--port", "-p", help="Локальный порт для прослушивания"),
    loss: float = typer.Option(0.0, "--loss", "-l", help="Вероятность потери пакета (0.0 - 1.0)"),
    delay: float = typer.Option(0.0, "--delay", "-d", help="Фиксированная задержка в секундах"),
    min_delay: float = typer.Option(0.0, "--min-delay", help="Минимальная задержка (для случайного диапазона)"),
    max_delay: float = typer.Option(0.0, "--max-delay", help="Максимальная задержка (для случайного диапазона)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробное логирование"),
):
    """Запустить Chaos Proxy"""
    global _proxy

    # Устанавливаем уровень логирования
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Разбираем target
    try:
        target_host, target_port_str = target.split(":")
        target_port = int(target_port_str)
    except ValueError:
        typer.echo(f"Ошибка: некорректный формат target. Ожидается host:port, получено {target}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Запуск Chaos Proxy:")
    typer.echo(f"  Целевой сервер: {target_host}:{target_port}")
    typer.echo(f"  Локальный порт: {listen_port}")
    typer.echo(f"  Вероятность потери: {loss}")
    
    if delay > 0:
        typer.echo(f"  Фиксированная задержка: {delay}с")
    elif min_delay > 0 or max_delay > 0:
        typer.echo(f"  Случайная задержка: {min_delay}-{max_delay}с")
    else:
        typer.echo(f"  Задержка: выключена")
    
    typer.echo("")
    typer.echo("Прокси запущен. Нажмите Ctrl+C для остановки.")
    typer.echo("")

    try:
        _proxy = ChaosProxy(
            target_host, target_port, listen_port,
            fixed_delay=delay,
            min_delay=min_delay,
            max_delay=max_delay,
            loss_rate=loss,
            enable_stats=True
        )
        asyncio.run(_run_proxy())
    except KeyboardInterrupt:
        typer.echo("\nОстановка прокси...")
    except Exception as e:
        typer.echo(f"Ошибка: {e}", err=True)
        raise typer.Exit(code=1)


async def _run_proxy():
    """Запуск прокси в асинхронном режиме с graceful shutdown"""
    global _proxy
    
    # Создаём событие для сигнала остановки
    stop_event = asyncio.Event()
    
    # Обработчик Ctrl+C
    def signal_handler():
        # Не создаём задачу прямо из обработчика сигнала
        stop_event.set()
    
    async def wait_for_stop():
        await stop_event.wait()
        typer.echo("\nПолучен сигнал остановки...")
        await _proxy.stop()
    
    # Регистрируем обработчики сигналов (для Unix)
    loop = asyncio.get_running_loop()
    try:
        loop.add_signal_handler(signal.SIGINT, signal_handler)
        loop.add_signal_handler(signal.SIGTERM, signal_handler)
    except NotImplementedError:
        # Windows: обрабатываем Ctrl+C через asyncio
        pass
    
    # Запускаем прокси
    proxy_task = asyncio.create_task(_proxy.start())
    
    # Ждём сигнала остановки
    stop_task = asyncio.create_task(wait_for_stop())
    
    # Ждём первого завершившегося
    done, pending = await asyncio.wait(
        [proxy_task, stop_task],
        return_when=asyncio.FIRST_COMPLETED
    )
    
    # Отменяем оставшуюся задачу
    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    # Если прокси ещё работает, останавливаем
    if not proxy_task.done():
        await _proxy.stop()
        await proxy_task


@app.command()
def stats():
    """Показать статистику работы"""
    typer.echo("Статистика будет доступна в следующих версиях")
    # TODO: реализация


@app.command()
def stop():
    """Остановить работающий прокси"""
    global _proxy
    if _proxy:
        typer.echo("Остановка прокси...")
        # TODO: реализация graceful shutdown
    else:
        typer.echo("Прокси не запущен")


def main():
    app()


if __name__ == "__main__":
    main()