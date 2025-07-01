import asyncio, json, random, sys

class ClienteTransacao:
    def __init__(self, endereco_servidor):
        self.servidor = endereco_servidor              
        self.conjunto_leitura = {}                
        self.conjunto_escrita = {}                      
        self.resultado = None #status final do commit

    async def ler(self, item):
        if item in self.conjunto_escrita:
            return self.conjunto_escrita[item]
        
        leitor, escritor = await asyncio.open_connection(*self.servidor)
        escritor.write(json.dumps({"read": item}).encode())
        await escritor.drain()

        resposta = json.loads((await leitor.read(65536)).decode())
        escritor.close()

        self.conjunto_leitura[item] = resposta["version"]
        return resposta["value"]

    def escrever(self, item, valor):
        self.conjunto_escrita[item] = valor

    async def commit(self):
        porta_callback = random.randint(20000, 60000)
        loop = asyncio.get_running_loop()
        futuro_resultado = loop.create_future()

        async def _callback(leitor, escritor):
            dados = await leitor.read(65536)
            resposta = json.loads(dados.decode())
            print("[callback recebido]", resposta)
            if not futuro_resultado.done():
                futuro_resultado.set_result(resposta["status"])
            escritor.close()

        servidor_callback = await asyncio.start_server(_callback, "127.0.0.1", porta_callback)

        transacao = {
            "rs": self.conjunto_leitura,
            "ws": self.conjunto_escrita,
            "client": ("127.0.0.1", porta_callback)
        }

        leitor, escritor = await asyncio.open_connection(*self.servidor)
        escritor.write(json.dumps({"commit_fwd": transacao}).encode())
        await escritor.drain()
        escritor.close()

        status = await futuro_resultado

        servidor_callback.close()
        await servidor_callback.wait_closed()

        self.resultado = status
        return status


async def main(porta):
    cliente = ClienteTransacao(("127.0.0.1", porta))
    await cliente.ler("x")
    cliente.escrever("x", "42")
    print("Commit:", await cliente.commit())

if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1])))
