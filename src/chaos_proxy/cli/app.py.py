import typer
from typing import Optional

app = typer.Typer(
    name="chaos-proxy",
    help="Эмулятор сетевых задержек и потерь пакетов (Network Chaos Monkey)",
    add_completion=False,
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
    typer.echo(f"Запуск Chaos Proxy:")
    typer.echo(f"  Целевой сервер: {target}")
    typer.echo(f"  Локальный порт: {listen_port}")
    typer.echo(f"  Вероятность потери: {loss}")
    
    if delay > 0:
        typer.echo(f"  Фиксированная задержка: {delay}с")
    elif min_delay > 0 or max_delay > 0:
        typer.echo(f"  Случайная задержка: {min_delay}-{max_delay}с")
    else:
        typer.echo(f"  Задержка: выключена")
    
    # TODO: реализация прокси


@app.command()
def stats():
    """Показать статистику работы (пакеты, потери, задержки)"""
    typer.echo("Статистика будет доступна после запуска прокси")
    # TODO: реализация


@app.command()
def stop():
    """Остановить работающий прокси"""
    typer.echo("Остановка прокси...")
    # TODO: реализация


def main():
    app()


if __name__ == "__main__":
    main()