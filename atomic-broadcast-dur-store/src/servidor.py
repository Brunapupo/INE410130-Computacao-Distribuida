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
        self.abcast = AtomicBroadcaster(id, replicas)
        self.abcast.handler = self.broadcast_handler
        self.sock = socket.socket()                                   
        self.sock.bind((host, port))
        self.sock.listen()

    def serve_forever(self):
        while True:
            client_socket, _ = self.sock.accept()
            threading.Thread(target=self.client_handler, args=(client_socket,), daemon=True).start()

    def client_handler(self, client_socket):
        data = json.loads(client_socket.recv(65536).decode())
        if data[0] == "read":
            _, client_id, item = data
            self.handle_read(item, client_id, client_socket)
        client_socket.close()

    def send_to_client(self, client_socket, message):
        client_socket.sendall(json.dumps(message).encode())

    def broadcast_handler(self, raw_message):
        data = json.loads(raw_message.decode())
        if data[0] == "com_req":
            _, client_id, t_id, rs_raw, ws_raw = data
            rs = [ReadEntry(item, version) for (item, _, version) in rs_raw]
            ws = [WriteEntry(item, value) for (item, value) in ws_raw]
            self.handle_commit(client_id, t_id, rs, ws)

    #linhas 4-5 
    def handle_read(self, item, client_id, client_socket):
        if item == 'x':
            val, ver = self.x_val, self.x_ver
        else:
            val, ver = self.y_val, self.y_ver
        #envia ao cliente/client_id
        self.send_to_client(client_socket, (val, ver))

    #linhas 6-20
    def handle_commit(self, client_id, t_id, rs, ws):
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
                self.abcast.send(json.dumps(["abort", client_id, t_id]).encode())
                print(f"[{self.id}] ABORTED transaction  {t_id} from client {client_id}")  
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

            self.abcast.send(json.dumps(["commit", client_id, t_id]).encode())  
            print(f"[{self.id}] COMMITTED transaction {t_id} from client {client_id}") 
