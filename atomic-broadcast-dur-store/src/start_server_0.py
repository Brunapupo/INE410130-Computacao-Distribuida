import asyncio
from servidor import Server

if __name__ == "__main__":
    replicas = [("127.0.0.1", 9000), ("127.0.0.1", 9001)]
    servidor = Server(0, "127.0.0.1", 9000, replicas)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.create_task(servidor.abcast.start())         # inicia o broadcast
    loop.run_in_executor(None, servidor.serve_forever)  # escuta clientes
    loop.run_forever()
