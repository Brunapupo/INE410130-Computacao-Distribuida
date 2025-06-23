import asyncio, json
BUF = 65536

class AtomicBroadcaster:
    def __init__(self, proc_id: int, peers: list[tuple[str, int]], sequencer: int = 0):
        self.id = proc_id
        self.peers = peers
        self.seq = sequencer
        self.contador = 0                    # variável em PT-BR
        self.fila_entrega = asyncio.Queue()  # idem
        self._server = None

    async def start(self):
        # socket de escuta para este processo
        self._server = await asyncio.start_server(self._handler, *self.peers[self.id])
        asyncio.create_task(self._serve())

    async def broadcast(self, body: dict):
        if self.id == self.seq:                       # este nó é o sequencer?
            await self._multicast({"seq": self.contador, "body": body})
            self.contador += 1
        else:
            await self._send(self.peers[self.seq], {"from": self.id, "body": body})

    async def deliver(self):
        return await self.fila_entrega.get()

    # ---------------- internos ----------------
    async def _handler(self, reader, writer):
        dados = await reader.read(BUF)
        msg = json.loads(dados.decode())

        # Se eu for o sequencer e a msg ainda não tem número, numero e redistribuo
        if self.id == self.seq and "body" in msg and "seq" not in msg:
            await self.broadcast(msg["body"])
        else:
            await self.fila_entrega.put(msg)

        writer.close()

    async def _multicast(self, msg):
        await asyncio.gather(*[self._send(p, msg) for p in self.peers])

    async def _send(self, destino, msg):
        r, w = await asyncio.open_connection(*destino)
        w.write(json.dumps(msg).encode())
        await w.drain()
        w.close()

    async def _serve(self):
        async with self._server:
            await self._server.serve_forever()
