"""
Configuração otimizada do Gunicorn para PaddleOCR
Focada em performance e estabilidade para processamento de OCR
"""

import os
import multiprocessing

# Configurações de bind
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Workers - usar apenas 1 worker para evitar problemas de memória com PaddleOCR
workers = int(os.getenv('WORKERS', '1'))

# Tipo de worker - sync é melhor para processamento pesado de OCR
worker_class = "sync"

# Timeout - aumentado para processamento de arquivos grandes
timeout = int(os.getenv('TIMEOUT', '600'))  # 10 minutos
keepalive = 5

# Preload - carrega a aplicação antes de fazer fork dos workers
preload_app = True

# Reciclagem de workers para evitar vazamentos de memória
max_requests = int(os.getenv('MAX_REQUESTS', '1000'))
max_requests_jitter = int(os.getenv('MAX_REQUESTS_JITTER', '100'))

# Configurações de memória
worker_tmp_dir = "/dev/shm"  # Usar RAM para arquivos temporários (se disponível)

# Logging
loglevel = os.getenv('LOG_LEVEL', 'info').lower()
accesslog = "-"  # stdout
errorlog = "-"   # stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Configurações de processo
user = None
group = None
tmp_upload_dir = None

# Hooks para otimização
def on_starting(server):
    """Hook executado quando o servidor está iniciando"""
    server.log.info("🚀 Iniciando servidor PaddleOCR otimizado")

def when_ready(server):
    """Hook executado quando o servidor está pronto"""
    server.log.info("✅ Servidor PaddleOCR pronto para receber requisições")

def worker_int(worker):
    """Hook executado quando um worker recebe SIGINT"""
    worker.log.info("🔄 Worker recebeu sinal de interrupção")

def pre_fork(server, worker):
    """Hook executado antes de fazer fork de um worker"""
    server.log.info(f"🔧 Preparando worker {worker.pid}")

def post_fork(server, worker):
    """Hook executado após fazer fork de um worker"""
    server.log.info(f"🎯 Worker {worker.pid} iniciado")

def post_worker_init(worker):
    """Hook executado após inicialização do worker"""
    worker.log.info(f"⚡ Worker {worker.pid} inicializado e pronto")

def worker_abort(worker):
    """Hook executado quando um worker é abortado"""
    worker.log.error(f"❌ Worker {worker.pid} foi abortado")

def pre_exec(server):
    """Hook executado antes de exec"""
    server.log.info("🔄 Executando pre_exec hook")

# Configurações de graceful shutdown
graceful_timeout = 30