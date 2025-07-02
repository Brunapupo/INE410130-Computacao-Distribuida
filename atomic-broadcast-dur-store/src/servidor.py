import asyncio, json, sys
from broadcast import AtomicBroadcaster

class ServidorReplica:
    def __init__(self, id_replicas: int, replicas: list[tuple[str, int]]):
        self.id = id_replicas  # ID desta réplica
        self.armazenamento: dict[str, tuple[int, str]] = {}  #dicionario chave
        self.ultimo_commit = 0  #contador de commits
        self.difusor = AtomicBroadcaster(id_replicas, replicas)  #modulo de difusao atomica

    #inicia o servidor e o listener  do clientes
    async def iniciar(self):
        await self.difusor.start()
        asyncio.create_task(self._loop_entrega())
        await self._escutar_clientes()

    #Procolo DUR propaga os commits em ordem global
    async def _loop_entrega(self):
        while True:
            msg = await self.difusor.deliver()
            if "commit_req" in msg["body"]:
                await self._aplicar_commit(msg["body"]["commit_req"])

    async def _aplicar_commit(self, transacao):
        rs, ws = transacao["rs"], transacao["ws"]

    
        for item, versao in rs.items():
            if self.armazenamento.get(item, (0,))[0] > versao:
                await self._responder(transacao["client"], {"status": "abort"})
                return
        # se passou na certificação, aplica a escrita e atualiza. [UPADATE REPLICATION]
        self.ultimo_commit += 1
        for item, valor in ws.items():
            versao_atual, _ = self.armazenamento.get(item, (0, None))
            self.armazenamento[item] = (versao_atual + 1, valor)

        await self._responder(transacao["client"], {"status": "commit"})
    
    #funcoes para escutar resposta do cliente
    async def _escutar_clientes(self):
        servidor = await asyncio.start_server(self._tratar_cliente, "127.0.0.1", 0)
        self.endereco_cliente = servidor.sockets[0].getsockname()
        print(f"Réplica {self.id} escutando clientes na porta {self.endereco_cliente[1]}")
        async with servidor:
            await servidor.serve_forever()

    async def _tratar_cliente(self, leitor, escritor):
        req = json.loads((await leitor.read(65536)).decode())
        if "read" in req:
            item = req["read"]
            versao, valor = self.armazenamento.get(item, (0, None))
            escritor.write(json.dumps({"version": versao, "value": valor}).encode())
            await escritor.drain(); escritor.close()
        elif "commit_fwd" in req:
            await self.difusor.broadcast({"commit_req": req["commit_fwd"]})
            escritor.close()

    async def _responder(self, endereco, resposta):
        try:
            leitor, escritor = await asyncio.open_connection(*endereco)
            escritor.write(json.dumps(resposta).encode())
            await escritor.drain()
            escritor.close()
        except (ConnectionRefusedError, ConnectionResetError):
            pass

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python src/servidor.py <id_replicas> <num_replicas>")
        sys.exit(1)

    id_replicas = int(sys.argv[1])
    num_replicas = int(sys.argv[2])
    replicas = [("127.0.0.1", 9000 + i) for i in range(num_replicas)]#multiplas replicas

    asyncio.run(ServidorReplica(id_replicas, replicas).iniciar())
