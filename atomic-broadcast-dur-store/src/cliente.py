import asyncio, json, random, sys

class TransactionClient:
    def __init__(self, server_addr):
        self.server = server_addr          # endereço (host, porta) da réplica
        self.rs, self.ws = {}, {}          # read-set e write-set
        self.result = None

    async def read(self, item):
        if item in self.ws:                # valor já escrito localmente
            return self.ws[item]
        reader, writer = await asyncio.open_connection(*self.server)
        writer.write(json.dumps({"read": item}).encode())
        await writer.drain()
        ans = json.loads((await reader.read(65536)).decode())
        writer.close()
        self.rs[item] = ans["version"]
        return ans["value"]

    def write(self, item, value):
        self.ws[item] = value

    async def commit(self):
        # -------- prepara servidor callback p/ receber decisão --------
        callback_port = random.randint(20000, 60000)
        loop = asyncio.get_running_loop()
        result_future = loop.create_future()            # Future para a decisão

        async def _callback(reader, writer):
            data = await reader.read(65536)
            res = json.loads(data.decode())
            if not result_future.done():                # evita InvalidStateError
                result_future.set_result(res["status"])
            writer.close()

        cb_server = await asyncio.start_server(
            _callback, "127.0.0.1", callback_port
        )

        # -------- envia commit_fwd para a réplica --------
        tx = {
            "rs": self.rs,
            "ws": self.ws,
            "client": ("127.0.0.1", callback_port)
        }
        r, w = await asyncio.open_connection(*self.server)
        w.write(json.dumps({"commit_fwd": tx}).encode())
        await w.drain()
        w.close()

        # -------- espera a réplica conectar e responder --------
        status = await result_future

        cb_server.close()
        await cb_server.wait_closed()

        self.result = status
        return status

# ---------------- demo rápido ----------------
async def main(porta):
    cli = TransactionClient(("127.0.0.1", porta))
    await cli.read("x")
    cli.write("x", "42")
    print("Commit:", await cli.commit())

if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1])))
