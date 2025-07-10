# client.py
import socket
import json
import random

class Client:
    """
    Representa um cliente que executa transações no sistema distribuído.
    Implementa as fases de execução e término da transação conforme o Algoritmo 3 do PDF.
    Assume-se que os nodos não irão falhar.
    """
    def __init__(self, client_id, server_addresses, sequencer_address):
        """
        Inicializa o cliente.

        Args:
            client_id (str): ID único do cliente (ex: "T1", "T2").
            server_addresses (list): Lista de tuplas (host, porta) dos servidores replicados.
            sequencer_address (tuple): Tupla (host, porta) do sequenciador.
        """
        self.client_id = client_id
        self.server_addresses = server_addresses
        self.sequencer_address = sequencer_address
        self.ws = []  # Write Set: [{'item': item, 'value': val}]
        self.rs = []  # Read Set: [{'item': item, 'value': val, 'version': ver}]
        self.transaction_id = 0  

    def _choose_server(self):
        """
        Escolhe aleatoriamente um dos servidores replicados.
        Corresponde à linha 2 do Algoritmo 3.

        Returns:
            tuple: Endereço (host, porta) do servidor escolhido.
        """
        return random.choice(self.server_addresses)

    def read(self, item):
        """
        Executa uma operação de leitura para um item.
        Corresponde às linhas 6-12 do Algoritmo 3.
        Esta é a comunicação 1:1 com um servidor.

        Args:
            item (str): O nome do item a ser lido.
        """
    
        # Verifica se o item já está no Write Set (ws)
        for entry in self.ws:
            if entry['item'] == item:
                return 

        # Se não estiver no WS, solicita o item de um servidor
        current_server = self._choose_server()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(current_server) # Conexão 1:1 com o servidor

            message = {
                'type': 'read_request', 
                'item': item, 
                'cid': self.client_id
                }
            
            sock.sendall(json.dumps(message).encode('utf-8'))
            response_data = sock.recv(4096).decode('utf-8')
            response = json.loads(response_data)
            # Adiciona o item, valor e versão ao Read Set (rs)
            self.rs.append({'item': item, 'value': response['value'], 'version': response['version']})
            #print(f"Cliente {self.client_id} (Transação {self.transaction_id}): Leu '{item}' (valor: {response['value']}, versão: {response['version']}) do servidor {current_server}.")


    def write(self, item, value):
        """
        Executa uma operação de escrita para um item.
        Corresponde às linhas 4-5 do Algoritmo 3.

        Args:
            item (str): O nome do item a ser escrito.
            value (any): O novo valor para o item.
        """
        # Adiciona o item e seu novo valor ao Write Set (ws)
        self.ws.append({'item': item, 'value': value})
        #print(f"Cliente {self.client_id} (Transação {self.transaction_id}): Adicionou escrita '{item}={value}' ao WS.") # Comentado para menos prints

    def commit(self):
        """
        Processa a fase de término da transação.
        Decide se envia para broadcast (se houver escritas no WS) ou aborta localmente.
        Corresponde à lógica de decisão do cliente no final do Algoritmo 3.

        Returns:
            str: O resultado final da transação ('commit' ou 'abort').
        """
        # Se o Write Set (ws) tem alguma escrita (ou seja, 'tiver valor'), tenta commitar via sequenciador
        if len(self.ws) > 0: # Verifica explicitamente se o WS não está vazio
            
            # Lógica de envio ao sequenciador (linhas 15-16 do Algoritmo 3)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(self.sequencer_address) # Conecta ao SEQUENCIADOR (para broadcast)
                commit_request = {
                    'type': 'commit_request',
                    'cid': self.client_id,
                    't_id': self.transaction_id,
                    'rs': self.rs,
                    'ws': self.ws
                }
                sock.sendall(json.dumps(commit_request).encode('utf-8')) # Envia requisição via difusão atômica (simulada pelo sequenciador)
                #print(f"Cliente {self.client_id} (Transação {self.transaction_id}): Enviou solicitação de commit ao sequenciador.") # Comentado para menos prints
                # Espera pelo resultado (commit/abort) do sequenciador/servidor
                outcome_data = sock.recv(4096).decode('utf-8')
                outcome = json.loads(outcome_data)
                
                return outcome['result'] 
        else:
            print(f"Cliente {self.client_id} (Transação {self.transaction_id}): Abort localmente (WS vazio, nada para commitar).")
            return 'abort' 

