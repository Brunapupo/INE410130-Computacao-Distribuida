# server.py
import socket
import threading
import json

# import time # Removido, pois não é utilizado diretamente neste arquivo

class Server:
    """
    Representa um servidor replicado no sistema distribuído.
    Ele gerencia o banco de dados (db), responde a requisições de leitura
    e executa o teste de certificação para requisições de commit,
    conforme o Algoritmo 4 do PDF.
    Assume-se que os nodos não irão falhar, simplificando o tratamento de erros de rede.
    """
    def __init__(self, server_id, host, port):
        """
        Inicializa o servidor.

        Args:
            server_id (int): ID único do servidor.
            host (str): O endereço IP ou hostname onde o servidor irá escutar.
            port (int): A porta onde o servidor irá escutar.
        """
        self.server_id = server_id
        self.host = host
        self.port = port
        self.db = {} 
        # Um lock para proteger o acesso concorrente ao banco de dados
        # Essencial para evitar condições de corrida em um servidor multi-threaded.
        self.db_lock = threading.Lock() 

        # Inicializa alguns dados de exemplo no banco de dados com versão 0,
        # conforme linha 2 do Algoritmo 4 (para x e y).
        with self.db_lock:
            self.db['x'] = {'value': 'valor_inicial_x', 'version': 0}
            self.db['y'] = {'value': 'valor_inicial_y', 'version': 0}
        
    def start(self):
        """
        Inicia o servidor, ligando o socket e escutando por conexões.
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5) # Permite até 5 conexões pendentes
        print(f"Servidor {self.server_id} escutando em {self.host}:{self.port}")

        while True:
            # Aceita uma nova conexão (pode ser de um cliente para leitura ou do sequenciador para commit)
            conn, addr = server_socket.accept()
            #print(f"Servidor {self.server_id}: Conexão aceita de {addr}")
            # Cria uma nova thread para lidar com esta conexão, permitindo concorrência
            client_handler_thread = threading.Thread(target=self.handle_message, args=(conn, addr))
            client_handler_thread.start()

    def handle_message(self, conn, addr):
        """
        Lida com as mensagens recebidas de uma conexão, decodifica-as
        e as direciona para a função de tratamento apropriada.
        Esta função é executada em uma thread separada para cada conexão.

        Args:
            conn (socket.socket): O objeto socket para comunicação.
            addr (tuple): O endereço (IP, porta) do remetente.
        """
        data_recebida = conn.recv(4096).decode('utf-8')
        if not data_recebida:
            conn.close()
            return

        mensagem = json.loads(data_recebida)
        tipo_mensagem = mensagem.get('type')

        # Direciona a mensagem para a função de tratamento apropriada
        if tipo_mensagem == 'read_request':
            item = mensagem.get('item')
            client_id = mensagem.get('cid')
            self.handle_read_request(conn, item, client_id)
        elif tipo_mensagem == 'commit_request':
            cid = mensagem.get('cid')
            t_id = mensagem.get('t_id')
            rs = mensagem.get('rs')
            ws = mensagem.get('ws')
            self.handle_commit_request(conn, cid, t_id, rs, ws)
        else:
            print(f"Servidor {self.server_id}: Mensagem inesperada de {addr}: {tipo_mensagem}")
        
        conn.close() # Fecha a conexão após processar a requisição

    def handle_read_request(self, conn, item, client_id):
        """
        Processa uma requisição de leitura de um cliente.
        Corresponde às linhas 4-5 do Algoritmo 4.

        Args:
            conn (socket.socket): O socket para enviar a resposta de volta ao cliente.
            item (str): O item que o cliente deseja ler.
            client_id (int): O ID do cliente que fez a requisição.
        """
        with self.db_lock: # Protege o acesso ao DB para leitura
            val = self.db.get(item, {}).get('value', None)
            version = self.db.get(item, {}).get('version', -1) # -1 se não encontrado

            response = {'type': 'read_response', 'item': item, 'value': val, 'version': version}
            conn.sendall(json.dumps(response).encode('utf-8'))
            #print(f"Servidor {self.server_id}: Enviou resposta de leitura para '{item}' (valor: {val}, versão: {version}) para o cliente {client_id}.")

    def handle_commit_request(self, conn, cid, t_id, rs, ws):
        """
        Processa uma requisição de commit de uma transação.
        Corresponde às linhas 6-20 do Algoritmo 4 (teste de certificação e aplicação).

        Args:
            conn (socket.socket): O socket para enviar o resultado (commit/abort) de volta.
            cid (int): ID do cliente que iniciou a transação.
            t_id (int): ID da transação.
            rs (list): Read Set da transação (lista de {'item': item, 'value': val, 'version': ver}).
            ws (list): Write Set da transação (lista de {'item': item, 'value': val}).
        """
        abort_transaction = False
        
        with self.db_lock: # Protege o acesso ao DB durante o teste de certificação e atualização
            # Teste de Certificação (linhas 8-12 do Algoritmo 4)
            for item_info_rs in rs:
                item_rs = item_info_rs['item']
                versao_cliente = item_info_rs['version']
                
                # Obtém a versão atual do item no banco de dados do servidor
                db_item_data = self.db.get(item_rs, {})
                versao_db = db_item_data.get('version', -1)

                # Verifica se a versão no DB é maior que a versão lida pelo cliente (leitura obsoleta)
                if versao_db > versao_cliente:
                    abort_transaction = True
                    print(f"Servidor {self.server_id}: Conflito detectado para '{item_rs}'. Versão DB ({versao_db}) > versão cliente ({versao_cliente}). Abortando transação {t_id}.")
                    break # Sai do loop de verificação, pois já há um motivo para abortar

            resultado_mensagem = {'type': 'outcome', 't_id': t_id}

            if abort_transaction:
                resultado_mensagem['result'] = 'abort'
                print(f"Servidor {self.server_id}: Transação {t_id} (Cliente {cid}) ABORTADA.")
            else:
                resultado_mensagem['result'] = 'commit'
                # Aplica as atualizações do Write Set (linhas 16-19 do Algoritmo 4)
                for item_info_ws in ws:
                    item_ws = item_info_ws['item']
                    novo_valor = item_info_ws['value']
                    
                    # Atualiza a versão do item no DB e o valor
                    # Incrementa a versão do item. Se o item não existia, começa com 0.
                    nova_versao = self.db.get(item_ws, {}).get('version', -1) + 1 
                    self.db[item_ws] = {'value': novo_valor, 'version': nova_versao}
                    #print(f"Servidor {self.server_id}: Atualizou '{item_ws}' para '{novo_valor}', versão {nova_versao}.")
                
                print(f"Servidor {self.server_id}: Transação {t_id} (Cliente {cid}) EFETIVADA.")
        
        # Envia o resultado (commit/abort) de volta para o sequenciador (que retransmitirá ao cliente)
        conn.sendall(json.dumps(resultado_mensagem).encode('utf-8'))
        print(f"Estado atual do DB do Servidor {self.server_id}: {self.db}")

