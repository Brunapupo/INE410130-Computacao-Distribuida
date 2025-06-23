import asyncio, json, sys
from broadcast import AtomicBroadcaster

class ReplicaServer:
    def __init__(self, proc_id: int, peers: list[tuple[str, int]]):
        self.id = proc_id
        self.store: dict[str, tuple[int, str]] = {}   # item → (versão, valor)
        self.last_committed = 0
        self.bcast = AtomicBroadcaster(proc_id, peers)

    async def start(self):
        await self.bcast.start()
        asyncio.create_task(self._deliver_loop())
        await self._client_listener()

    # ---------- entrega de commit_req vindos do broadcast ----------
    async def _deliver_loop(self):
        while True:
            msg = await self.bcast.deliver()
            if "commit_req" in msg["body"]:
                await self._apply_commit(msg["body"]["commit_req"])

    async def _apply_commit(self, tx):
        rs, ws = tx["rs"], tx["ws"]
        # certification test (Alg.4 linhas 8-12)
        for item, ver in rs.items():
            if self.store.get(item, (0,))[0] > ver:
                await self._reply(tx["client"], {"status": "abort"})
                return
        # se passou, aplica writes
        self.last_committed += 1
        for item, val in ws.items():
            cur_ver, _ = self.store.get(item, (0, None))
            self.store[item] = (cur_ver + 1, val)
        await self._reply(tx["client"], {"status": "commit"})

    # ---------- interface para clientes ----------
    async def _client_listener(self):
        serv = await asyncio.start_server(self._handle_client, "127.0.0.1", 0)
        self.cli_addr = serv.sockets[0].getsockname()
        print(f"Replica {self.id} escutando clientes em porta {self.cli_addr[1]}")
        async with serv: await serv.serve_forever()

    async def _handle_client(self, r, w):
        req = json.loads((await r.read(65536)).decode())
        if "read" in req:
            item = req["read"]
            ver, val = self.store.get(item, (0, None))
            w.write(json.dumps({"version": ver, "value": val}).encode())
            await w.drain(); w.close()
        elif "commit_fwd" in req:
            await self.bcast.broadcast({"commit_req": req["commit_fwd"]})
            w.close()

    # ---------- envia decisão ao cliente ----------
    async def _reply(self, addr, payload):
        try:
            reader, writer = await asyncio.open_connection(*addr)
            writer.write(json.dumps(payload).encode())
            await writer.drain()
            writer.close()
        except (ConnectionRefusedError, ConnectionResetError):
            # Cliente já fechou o callback: outra réplica entregou a decisão.
            pass

# ---------- entrada via CLI ----------
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python src/servidor.py <id_replica> <num_replicas>")
        sys.exit(1)
    proc_id = int(sys.argv[1]); n = int(sys.argv[2])
    peers = [("127.0.0.1", 9000 + i) for i in range(n)]
    asyncio.run(ReplicaServer(proc_id, peers).start())
