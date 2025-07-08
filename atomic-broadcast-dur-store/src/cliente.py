import json
import random
import socket
import sys

class Transaction:
    def __init__(self, ops):
        self.ops = ops
        self.id  = random.randint(1, 10**6)

    def getOp(self, i):
        return self.ops[i][0]

    def getItem(self, i):
        return self.ops[i][1] if len(self.ops[i]) > 1 else None

    def getValue(self, i):
        return self.ops[i][2] if len(self.ops[i]) > 2 else None

class TransactionClient:
    def __init__(self, cid, t, abcast):
        self.cid = cid
        self.t = t
        self.ws = set()
        self.rs = set()
        self.i = 0 
        self.abcast = abcast

    #Escolha aleatoria em um dos servidores.
    def execute(self, s):
            while self.t.getOp(self.i) != "commit" and self.t.getOp(self.i) != "abort":

                if self.t.getOp(self.i) == "write":
                    self.ws.add((self.t.getItem(self.i), self.t.getValue(self.i)))

                if self.t.getOp(self.i) == "read":
                    if any(x for x in self.ws if x[0] == self.t.getItem(self.i)):
                        v = next(v for (k, v) in self.ws if k == self.t.getItem(self.i))
                    else:
                        s.send(json.dumps(["read", self.cid, self.t.getItem(self.i)]).encode()) #formate json
                        val, version = json.loads(s.receive().decode())
                        self.rs.add((self.t.getItem(self.i), v, version)) 

                self.i += 1
            
            #Commit or abort
            if self.t.getOp(self.i) == "commit":
                self.abcast.send(json.dumps(["com_req", self.cid, self.t.id, list(self.rs), list(self.ws)]).encode())
                res = self.abcast.receive(self.cid)
                return res
            else:
                return "abort"

if __name__ == "__main__":
    replicas = [("127.0.0.1", 9000), ("127.0.0.1", 9001)]

    # Cliente 1 (Transação T1)
    t1_ops = [
        ("read",  "x"),
        ("write", "y", 10),
        ("commit",)
    ]
    abcast1 = AtomicBroadcaster("C1", replicas, "127.0.0.1", 8000)
    tx1 = Transaction(t1_ops)
    client1 = TransactionClient("C1", tx1, abcast1)

    # Supondo socket direto (ponto-a-ponto) já criado para servidor escolhido
    s1 = socket.socket()
    s1.connect(("127.0.0.1", 9000))  # servidor aleatório escolhido para T1

    result1 = client1.execute(s1)
    print("Resultado T1:", result1)
    s1.close()

    # Cliente 2 (Transação T2)
    t2_ops = [
        ("read", "y"),
        ("read", "x"),
        ("read", "z"),
        ("commit",)
    ]
    abcast2 = AtomicBroadcaster("C2", replicas, "127.0.0.1", 8001)
    tx2 = Transaction(t2_ops)
    client2 = TransactionClient("C2", tx2, abcast2)

    s2 = socket.socket()
    s2.connect(("127.0.0.1", 9001))  # servidor aleatório escolhido para T2

    result2 = client2.execute(s2)
    print("Resultado T2:", result2)
    s2.close()


