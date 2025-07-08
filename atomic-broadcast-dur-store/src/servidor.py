import json, socket, threading
from broadcast import AtomicBroadcaster

class Server:
    def __init__(self, id ):
        self.id = id
        self.x_val, self.x_ver = None, 0
        self.y_val, self.y_ver = None, 0
        self.lastCommitted = 0

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
        while rs[i].getItem() is not None:
            item = rs[i].getItem()  
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

            while ws[j].getItem() is not None:
                item = ws[j].getItem()
                val = ws[j].getVal()

                if item == "x":
                    self.x_ver += 1
                    self.x_val  = val            
                else:  
                    self.y_ver += 1
                    self.y_val  = val
                j += 1       

            self.send_to_client(cid, ("commit", t_id))    

