import asyncio, json
BUF = 65536

#classe representa um nó no sistema
class AtomicBroadcaster:
    def __init__(self, proc_id: int, replicas: list[tuple[str, int]], sequenciador: int = 0):
        self.id = proc_id #é o id dessa replica
        self.replicas = replicas #lista com os ip da porta das replicas
        self.seq = sequenciador # é o id da réplica que atua como sequenciador global
        self.contador = 0 #para numerar as mensagens                   
        self.fila_entrega = asyncio.Queue() #fila msg recebidas
        self._server = None #TCP usado para executar conexões

    #Inicia o sevirdor TCP/escuta as msgs das replicas
    async def start(self):
        self._server = await asyncio.start_server(self._handler, *self.replicas[self.id])
        asyncio.create_task(self._serve())

    #verifica se está replica é o sequenciador, se for, é enviado msgs para todas as replicas, fazendo o broadcast
    async def broadcast(self, body: dict):
        if self.id == self.seq:                       
            await self._multicast({"seq": self.contador, "body": body})
            self.contador += 1
        #Se não for o sequeciador, envia msgs apenas para a replica que é o sequenciador
        else:
            await self._send(self.replicas[self.seq], {"from": self.id, "body": body})

    #return da mensagem da fila
    async def deliver(self):
        return await self.fila_entrega.get()

    #metodos privados, instanciados sempre que uma replica se conectar
    #render e writer: ler os dados e enviar os dados
    async def _handler(self, reader, writer): 
        #lê os dados do TCP e os dados do JSON.
        dados = await reader.read(BUF)
        msg = json.loads(dados.decode())

        # Se eu sou o sequenciador e a mensagem ainda não tem número global id/seqquenciador, 
        # então reenvido a mensagem com número/id através do broadcast
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
