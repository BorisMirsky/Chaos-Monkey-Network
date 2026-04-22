import asyncio
import typer
import logging
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
            max_delay=max_delay
        )
        asyncio.run(_run_proxy())
    except KeyboardInterrupt:
        typer.echo("\nОстановка прокси...")
    except Exception as e:
        typer.echo(f"Ошибка: {e}", err=True)
        raise typer.Exit(code=1)


async def _run_proxy():
    """Запуск прокси в асинхронном режиме"""
    global _proxy
    await _proxy.start()


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