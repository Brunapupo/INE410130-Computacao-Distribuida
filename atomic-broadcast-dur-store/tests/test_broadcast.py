import asyncio, sys, os

# adiciona ../src ao PYTHONPATH para achar broadcast.py
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from broadcast import AtomicBroadcaster

async def main():
    # pares = lista de (host, porta) das réplicas
    pares = [("127.0.0.1", 9100), ("127.0.0.1", 9101)]

    # réplica 0 será o sequencer
    bc0 = AtomicBroadcaster(proc_id=0, peers=pares)
    bc1 = AtomicBroadcaster(proc_id=1, peers=pares)

    # inicializa os dois nós em paralelo
    await asyncio.gather(bc0.start(), bc1.start())

    # difunde uma mensagem simples
    await bc0.broadcast({"msg": "olá mundo"})

    # cada réplica deve entregar a mesma mensagem, na mesma ordem
    print("Entrega réplica 0:", await bc0.deliver())
    print("Entrega réplica 1:", await bc1.deliver())

if __name__ == "__main__":
    asyncio.run(main())
