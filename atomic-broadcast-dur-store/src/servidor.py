import json, socket, threading
from broadcast import AtomicBroadcaster

class ReadEntry:
    def __init__(self, item: str, version: int):
        self._item = item
        self._version = version

    def getItemSrv(self):
        return self._item

    def getVersion(self):
        return self._version


class WriteEntry:
    def __init__(self, item: str, value):
        self._item = item
        self._value = value

    def getItemSrv(self):
        return self._item

    def getVal(self):
        return self._value

class Server:
    def __init__(self, id, host, port, replicas ):
        self.id = id
        self.x_val, self.x_ver = None, 0
        self.y_val, self.y_ver = None, 0
        self.lastCommitted = 0
        self.host = host
        self.port = port

    #  # inicia broadcast
    #     self.abcast = AtomicBroadcaster(id, replicas)
    #     self.abcast.start_server(self.broadcast_handler)

    #     # inicia socket para leitura direta
    #     self.sock = socket.socket()
    #     self.sock.bind((host, port))
    #     self.sock.listen()

    # # escuta conexões diretas (leitura)
    # def serve_forever(self):
    #     while True:
    #         conn, _ = self.sock.accept()
    #         threading.Thread(target=self.client_handler, args=(conn,), daemon=True).start()

    # # trata conexões diretas
    # def client_handler(self, conn):
    #     data = json.loads(conn.recv(65536).decode())
    #     if data[0] == "read":
    #         _, cid, item = data
    #         self.handle_read(item, cid, conn)
    #     conn.close()

    # def send_to_client(self, conn, message):
    #     conn.sendall(json.dumps(message).encode())

    #linhas 4-5 
    def handle_read(self, item, cid):
        if item == 'x':
            val, ver = self.x_val, self.x_ver
        else:
            val, ver = self.y_val, self.y_ver
        #envia ao cliente/cid
        self.send_to_client(cid, (val, ver))

    #linhas 6-20
    def handle_commit(self, cid, t_id, rs, ws):
        i = 0
        j = 0 
        abort = False
        while rs[i].getItemSrv() is not None:
            item = rs[i].getItemSrv()  
            if item == 'x':
                ver_local = self.x_ver
            else: 
                ver_local = self.y_ver
            #linhas 1-9 - teste de versão atualizada
            #Protocolo DUR 
            if ver_local > rs[i].getVersion():
                self.send_to_client(cid, ("abort", t_id))  
                abort = True                               
                break                                      
            i += 1
        #Atualiza
        if not abort:
            self.lastCommitted += 1 

            while ws[j].getItemSrv() is not None:
                item = ws[j].getItemSrv()
                val = ws[j].getVal()

                if item == "x":
                    self.x_ver += 1
                    self.x_val  = val            
                else:  
                    self.y_ver += 1
                    self.y_val  = val
                j += 1       

            self.send_to_client(cid, ("commit", t_id))    
