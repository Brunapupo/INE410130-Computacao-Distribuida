import json
import random
import socket
import sys

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
                        return v
                    else:
                        s.send(("read", self.t.getItem(self.i), self.cid))
                        v, version = s.receive(self.cid)
                        self.rs.add((self.t.getItem(self.i), v, version)) #abort

                self.i += 1

            if self.t.getOp(self.i) == "commit":
                self.abcast.send(("com_req", self.cid, self.t.id, self.rs, self.ws))
                res = self.abcast.receive(self.cid)
                return res
            else:
                return "abort"
