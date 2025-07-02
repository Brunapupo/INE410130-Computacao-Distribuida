import asyncio, json
BUF = 65536

class AtomicBroadcaster:
    def __init__(self, proc_id: int, replicas: list[tuple[str, int]], sequenciador: int = 0):
        self.id = proc_id 
        self.replicas = replicas 
        self.seq = sequenciador 
        self.contador = 0             
        self.fila_entrega = asyncio.Queue() 
        self._server = None 

    async def start(self):
        self._server = await asyncio.start_server(self._handler, *self.replicas[self.id])
        asyncio.create_task(self._serve())
    
    async def broadcast(self, body: dict):
        if self.id == self.seq:                       
            await self._multicast({"seq": self.contador, "body": body})
            self.contador += 1
        else:
            await self._send(self.replicas[self.seq], {"from": self.id, "body": body})

    async def deliver(self):
        return await self.fila_entrega.get()

    async def _handler(self, reader, writer): 
        dados = await reader.read(BUF)
        msg = json.loads(dados.decode())

    
        if self.id == self.seq and "body" in msg and "seq" not in msg:
            await self.broadcast(msg["body"])
        else:
            await self.fila_entrega.put(msg)

        writer.close()

    async def _multicast(self, msg):
        await asyncio.gather(*[self._send(p, msg) for p in self.replicas])
    
    #envia a msg via TCP para replica de destino
    async def _send(self, destino, msg):
        r, w = await asyncio.open_connection(*destino)
        w.write(json.dumps(msg).encode())
        await w.drain()
        w.close()

    # Mantem o servidor TCP ativo escutando conexões das replicas
    async def _serve(self):
        async with self._server:
            await self._server.serve_forever()
