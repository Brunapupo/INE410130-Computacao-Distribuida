# maintest.py
import threading 
import time     
import sys       
import os        

from client import Client
from server import Server
from sequencer import Sequencer

SERVER_HOST = '127.0.0.1' 
SERVER_PORTS = [8001, 8002, 8003] 
SEQUENCER_HOST = '127.0.0.1' 
SEQUENCER_PORT = 9000 
# Lista de tuplas (host, porta) para todos os servidores
SERVER_ADDRESSES = [(SERVER_HOST, p) for p in SERVER_PORTS]
# Tupla (host, porta) do sequenciador
SEQUENCER_ADDRESS = (SEQUENCER_HOST, SEQUENCER_PORT)

# Variáveis globais para armazenar as threads do sequenciador e dos servidores.
# Elas são globais para que possam ser iniciadas apenas uma vez e persistam durante os testes.
global_sequencer_thread = None
global_server_threads = []

def setup_global_environment():
    """
    Configura o ambiente global (inicia o sequenciador e os servidores) uma única vez.
    """
    global global_sequencer_thread, global_server_threads
    print("--- Configurando ambiente global (Sequenciador e Servidores) ---")
    
    # Inicia o Sequenciador em uma thread separada
    global_sequencer_thread = threading.Thread(target=Sequencer(SEQUENCER_HOST, SEQUENCER_PORT, SERVER_ADDRESSES).start)
    global_sequencer_thread.daemon = True # Define a thread como daemon para que termine com o programa principal
    global_sequencer_thread.start()
    time.sleep(0.1) 

    # Inicia cada Servidor Replicado em sua própria thread separada
    for i, port in enumerate(SERVER_PORTS):
        #cria um obj e uma instancia da classe server
        thread = threading.Thread(target=Server(i + 1, SERVER_HOST, port).start) 
        thread.daemon = True # Define a thread como daemon
        global_server_threads.append(thread) # Adiciona a thread à lista global
        thread.start()
    time.sleep(0.2) 
    print("Ambiente global configurado e pronto para testes.\n")


def client_transaction_runner(client_instance, operations):
    """
    Função que será executada por cada thread de cliente.
    Ela orquestra as operações da transação para uma instância de cliente.
    """
    # Incrementa o ID da transação para esta execução específica do cliente
    client_instance.transaction_id += 1
    # Reinicia os conjuntos de leitura (rs) e escrita (ws) para a nova transação
    client_instance.ws = []
    client_instance.rs = []

    print(f"--- Cliente {client_instance.client_id}: Iniciando Transação {client_instance.transaction_id} ---")
    
    # final_result será determinado pela chamada a client_instance.commit()
    
    # Itera sobre cada operação definida para esta transação (Fase de Execução)
    for op_type, *args in operations:
        item = args[0] if args and op_type not in ['sleep', 'commit'] else None
        
        if op_type == 'read':
            client_instance.read(item) # Chama o método de leitura do cliente
        elif op_type == 'write':
            value = args[1] # O valor é o segundo argumento para operações de escrita
            client_instance.write(item, value) # Chama o método de escrita do cliente
        elif op_type == 'sleep':
            delay = args[0] # O atraso é o primeiro argumento para operações de sleep
            print(f"Cliente {client_instance.client_id} (Transação {client_instance.transaction_id}): Aguardando {delay} segundos...")
            time.sleep(delay) # Pausa a execução da thread
        elif op_type == 'commit':
            # A operação 'commit' na lista apenas indica a intenção.
            # A chamada real ao commit (que decide se envia ou aborta) será feita após o loop.
            pass 
        else:
            print(f"Cliente {client_instance.client_id} (Transação {client_instance.transaction_id}): Operação desconhecida: {op_type}")
            # Se uma operação desconhecida for encontrada, a transação não pode continuar
            # e a chamada a commit() abaixo provavelmente resultará em aborto local (WS vazio)
            break 

    # --- FASE DE TÉRMINO: Chamada da função commit do cliente ---
    # A função commit do cliente agora contém a lógica de decisão de enviar para broadcast ou abortar localmente.
    final_result = client_instance.commit()

    # --- Registro do tempo e print final do resultado ---
    timestamp_fim = time.time()
    print(f"--- Cliente {client_instance.client_id}: Transação {client_instance.transaction_id} Finalizada com resultado: {final_result}. Fim: {timestamp_fim:.4f} ---")
    return final_result # Retorna o resultado final da transação

# Definição dos Testes
def teste_concorrencia_2():
    """
    Cenário de concorrência com 2 clientes.
    """
    print(f"======== EXECUTANDO TESTE: teste_concorrencia_2 ========\n")
    seq_addr = SEQUENCER_ADDRESS
    sv_addrs = SERVER_ADDRESSES


    t1_ops = [
        ("read", "x"),
        ("write", "y", "valor_y_t1"),
        ("commit",) # T1 tenta commitar suas operações
    ]

    t2_ops = [
        ("read", "y"),
        ("read", "x"),
        ("sleep", 0.2), # T2 espera um pouco, permitindo que T1 possa avançar
        ("write", "z", "valor_z_t2"),
        ("commit",) # T2 tenta commitar
    ]

    # Cria instâncias dos objetos Client
    client1_instance = Client("T1", sv_addrs, seq_addr)
    client2_instance = Client("T2", sv_addrs, seq_addr)

    # Cria threads para cada cliente, passando a função client_transaction_runner
    # e as operações específicas para cada transação.
    client1_thread = threading.Thread(target=client_transaction_runner, args=(client1_instance, t1_ops))
    client2_thread = threading.Thread(target=client_transaction_runner, args=(client2_instance, t2_ops))

    client1_thread.start() # Inicia a thread do Cliente 1
    client2_thread.start() # Inicia a thread do Cliente 2

    client1_thread.join() # Espera a thread do Cliente 1 terminar sua execução
    client2_thread.join() # Espera a thread do Cliente 2 terminar sua execução
    print(f"\n======== FIM DO TESTE: teste_concorrencia_2 ========\n")


def teste_concorrencia_3():
    """
    Cenário de concorrência com 3 clientes.
    """
    print(f"======== EXECUTANDO TESTE: teste_concorrencia_3 ========\n")
    seq_addr = SEQUENCER_ADDRESS
    sv_addrs = SERVER_ADDRESSES

    t1_ops = [
        ("write", "a", 1), 
        ("commit",)
    ]

    t2_ops = [
        ("read", "a"), 
        ("write", "b", 2), 
        ("commit",)
    ]

    t3_ops = [
        ("read", "b"), 
        ("write", "c", 3), 
        ("commit",)
    ]

    client1_instance = Client("T1", sv_addrs, seq_addr)
    client2_instance = Client("T2", sv_addrs, seq_addr)
    client3_instance = Client("T3", sv_addrs, seq_addr)

    client1_thread = threading.Thread(target=client_transaction_runner, args=(client1_instance, t1_ops))
    client2_thread = threading.Thread(target=client_transaction_runner, args=(client2_instance, t2_ops,))
    client3_thread = threading.Thread(target=client_transaction_runner, args=(client3_instance, t3_ops,))

    client1_thread.start()
    client2_thread.start()
    client3_thread.start()

    client1_thread.join()
    client2_thread.join()
    client3_thread.join()
    print(f"\n======== FIM DO TESTE: teste_concorrencia_3 ========\n")


def teste_independentes():
    """
    Cenário com transações independentes (não devem causar conflitos).
    """
    print(f"======== EXECUTANDO TESTE: teste_independentes ========\n")
    seq_addr = SEQUENCER_ADDRESS
    sv_addrs = SERVER_ADDRESSES

    t1_ops = [
        ("write", "p", 100), 
        ("commit",)
    ]

    t2_ops = [
        ("write", "q", 200), 
        ("commit",)
    ]

    client1_instance = Client("T1", sv_addrs, seq_addr)
    client2_instance = Client("T2", sv_addrs, seq_addr)

    client1_thread = threading.Thread(target=client_transaction_runner, args=(client1_instance, t1_ops))
    client2_thread = threading.Thread(target=client_transaction_runner, args=(client2_instance, t2_ops,))

    client1_thread.start()
    client2_thread.start()

    client1_thread.join()
    client2_thread.join()
    print(f"\n======== FIM DO TESTE: teste_independentes ========\n")


def teste_leitura_obsoleta():
    """
    Cenário onde uma transação tenta commitar com uma leitura obsoleta (deve abortar).
    """
    print(f"======== EXECUTANDO TESTE: teste_leitura_obsoleta ========\n")
    seq_addr = SEQUENCER_ADDRESS
    sv_addrs = SERVER_ADDRESSES

    # T1 altera x; T2 lê versão antiga e tenta confirmar depois, resultando em aborto
    t1_ops = [
        ("write", "x", 99), 
        ("sleep", 0.2)
        ("commit",)
    ]

    t2_ops = [
        ("read", "x"),       # T2 lê 'x' (versão inicial)
        ("sleep", 0.3),      # Dá tempo para T1 commitar e alterar 'x'
        ("commit",)          # T2 tenta commitar, mas 'x' estará obsoleto
    ]

    client1_instance = Client("T1", sv_addrs, seq_addr)
    client2_instance = Client("T2", sv_addrs, seq_addr)

    client1_thread = threading.Thread(target=client_transaction_runner, args=(client1_instance, t1_ops))
    client2_thread = threading.Thread(target=client_transaction_runner, args=(client2_instance, t2_ops,))

    client1_thread.start()
    client2_thread.start()

    client1_thread.join()
    client2_thread.join()
    print(f"\n======== FIM DO TESTE: teste_leitura_obsoleta ========\n")


#são projetados para demonstrar o comportamento do protocolo DUR (Deferred Update Replication) em diferentes cenários de concorrência. 
if __name__ == "__main__":
    setup_global_environment()
    time.sleep(5) 

    teste_concorrencia_2()
    time.sleep(5) 

    teste_concorrencia_3()
    time.sleep(5)

    teste_independentes()
    time.sleep(5)

    teste_leitura_obsoleta()
    time.sleep(5)

    print("--- Todos os testes concluídos ---")
    print("O programa principal está terminando. As threads de servidor e sequenciador (daemon) serão encerradas.")

