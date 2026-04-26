import asyncio

async def handle(reader, writer):
    while True:
        data = await reader.read(1024)
        if not data:
            break
        writer.write(b'pong')
        await writer.drain()
    writer.close()

async def main():
    server = await asyncio.start_server(handle, '127.0.0.1', 9999)
    print("Эхо-сервер запущен на порту 9999 (keep-alive)")
    await server.serve_forever()

asyncio.run(main())