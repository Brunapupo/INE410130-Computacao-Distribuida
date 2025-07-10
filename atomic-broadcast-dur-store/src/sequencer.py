# sequencer.py
import socket
import threading
import json
import time

class Sequencer:
    """
    Representa o sequenciador no sistema distribuído.
    Ele recebe requisições de commit dos clientes, atribui um número de sequência
    e as retransmite para todos os servidores replicados, garantindo uma ordem total.
    """
    def __init__(self, host, port, server_addresses):
        """
        Inicializa o sequenciador.

        Args:
            host (str): O endereço IP ou hostname onde o sequenciador irá escutar.
            port (int): A porta onde o sequenciador irá escutar.
            server_addresses (list): Lista de tuplas (host, porta) de todos os servidores replicados.
        """
        self.host = host
        self.port = port
        self.server_addresses = server_addresses
        self.sequence_num = 0  # Contador para atribuir números de sequência às mensagens de commit
        self.lock = threading.Lock() # Um lock para proteger o contador de sequência e garantir atomicidade

        print(f"Sequenciador inicializado em {self.host}:{self.port}")

    def start(self):
        """
        Inicia o sequenciador, ligando o socket e escutando por conexões de clientes.
        """
        sequencer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sequencer_socket.bind((self.host, self.port))
        sequencer_socket.listen(5) # Permite até 5 conexões de clientes pendentes
        print(f"Sequenciador escutando em {self.host}:{self.port}")

        while True:
            # Aceita uma nova conexão de um cliente
            conn, addr = sequencer_socket.accept()
            # Cria uma nova thread para lidar com a requisição de commit deste cliente,
            # permitindo que múltiplos clientes se conectem concorrentemente.
            client_handler_thread = threading.Thread(target=self.handle_client_commit_request, args=(conn, addr))
            client_handler_thread.start()

    def handle_client_commit_request(self, client_conn, client_addr):
        """
        Lida com uma requisição de commit recebida de um cliente.
        Esta função é executada em uma thread separada para cada cliente conectado.

        Args:
            client_conn (socket.socket): O objeto socket para comunicação com o cliente.
            client_addr (tuple): O endereço (IP, porta) do cliente.
        """
        data_recebida = client_conn.recv(4096).decode('utf-8')
        if not data_recebida:
            return

        mensagem_cliente = json.loads(data_recebida)
        
        # Verifica se a mensagem é uma requisição de commit do cliente
        if mensagem_cliente.get('type') == 'commit_request':
            with self.lock:
                self.sequence_num += 1 # Atribui um número de sequência único e crescente
                numero_sequencia_atual = self.sequence_num

            # Prepara a mensagem para difusão, incluindo o número de sequência para ordem global
            mensagem_sequenciada = {
                'sequence_num': numero_sequencia_atual,
                'original_message': mensagem_cliente,
                # Guarda o endereço do cliente original para retransmitir o resultado do commit
                'client_addr_para_resultado': client_addr
            }
            print(f"Sequenciador: Requisição de commit recebida de {client_addr}. Atribuído sequência: {numero_sequencia_atual}")
            
            # Realiza a difusão atômica (simulada) para todos os servidores
            self.atomic_broadcast(mensagem_sequenciada, client_conn)
        else:
            print(f"Sequenciador: Mensagem inesperada de {client_addr}: {mensagem_cliente.get('type')}. Esperado 'commit_request'.")
        
        # A conexão do cliente será fechada pelo próprio cliente após receber o resultado.
        # O sequenciador mantém a conexão aberta apenas o tempo suficiente para retransmitir o resultado.
        pass

    def atomic_broadcast(self, mensagem_sequenciada, cliente_original_conn):
        """
        Difusão atômica retransmitindo a mensagem sequenciada para todos os servidores.
        Garante que todos os servidores recebam as mensagens na mesma ordem global.

        Args:
            mensagem_sequenciada (dict): A mensagem de commit com o número de sequência.
            cliente_original_conn (socket.socket): O socket do cliente original para enviar o resultado de volta.
        """
        resultado_recebido = False
        resultado_mensagem = None

        # Itera sobre todos os endereços de servidores registrados para enviar a mensagem de commit
        for host_servidor, porta_servidor in self.server_addresses:
            # Abre uma nova conexão socket para cada servidor
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_servidor:
                socket_servidor.connect((host_servidor, porta_servidor))
                
                # Envia a mensagem original de commit para o servidor.
                # O servidor usará a ordem de chegada garantida pelo sequenciador.
                socket_servidor.sendall(json.dumps(mensagem_sequenciada['original_message']).encode('utf-8'))
                #print(f"Sequenciador: Retransmitiu requisição de commit (seq {mensagem_sequenciada['sequence_num']}) para o servidor {host_servidor}:{porta_servidor}")

                # Espera pelo resultado do commit do servidor (commit ou abort)
                resposta_servidor_data = socket_servidor.recv(4096).decode('utf-8')
                if resposta_servidor_data:
                    resultado_mensagem = json.loads(resposta_servidor_data)
                    #print(f"Sequenciador: Recebeu resultado do servidor {host_servidor}:{porta_servidor}: {resultado_mensagem['result']}")
                    
                    # Retransmite o resultado (commit/abort) de volta para o cliente original
                    cliente_original_conn.sendall(json.dumps(resultado_mensagem).encode('utf-8'))
                    resultado_recebido = True
                    break # Para esta simulação simples, o primeiro resultado de um servidor é suficiente para informar o cliente

        if not resultado_recebido:
            # Se nenhum servidor respondeu (em um cenário onde nodos não falham, isso indicaria um erro de lógica),
            # o sequenciador informa o cliente original que a transação foi abortada.
            resultado_falso = {'type': 'outcome', 't_id': mensagem_sequenciada['original_message']['t_id'], 'result': 'abort'}
            cliente_original_conn.sendall(json.dumps(resultado_falso).encode('utf-8'))
            print(f"Sequenciador: Nenhum servidor respondeu. Notificando cliente {mensagem_sequenciada['original_message']['cid']} de aborto.")

