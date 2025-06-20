#!/usr/bin/env python3
"""
Script de inicialização otimizado para Railway
Inicia o servidor com configurações especiais para contornar timeouts
"""

import os
import sys
import time
import signal
import logging
from gunicorn.app.base import BaseApplication
from api_server import app
import config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StandaloneApplication(BaseApplication):
    """Aplicação Gunicorn customizada"""
    
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()
    
    def load_config(self):
        for key, value in self.options.items():
            self.cfg.set(key.lower(), value)
    
    def load(self):
        return self.application

def handle_sigterm(signum, frame):
    """Handler para SIGTERM gracioso"""
    logger.info("Recebido SIGTERM, iniciando shutdown gracioso...")
    sys.exit(0)

def pre_warm_paddleocr():
    """Pré-aquece o PaddleOCR em background"""
    try:
        logger.info("Pré-aquecendo PaddleOCR em background...")
        from medical_ocr import MedicalOCRProcessor
        
        # Inicializar mas não bloquear
        processor = MedicalOCRProcessor()
        logger.info("Processador OCR criado com sucesso")
        
    except Exception as e:
        logger.warning(f"Falha no pré-aquecimento do PaddleOCR: {e}")

def main():
    """Função principal"""
    # Registrar handler para SIGTERM
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    # Configurações do Railway
    port = int(os.environ.get('PORT', 5000))
    
    logger.info(f"Iniciando servidor na porta {port}")
    
    # Pré-aquecer PaddleOCR em background (não bloquear)
    pre_warm_paddleocr()
    
    # Configurações otimizadas do Gunicorn para Railway
    options = {
        'bind': f'0.0.0.0:{port}',
        'workers': 1,  # Railway funciona melhor com 1 worker
        'worker_class': 'sync',
        'timeout': 300,  # Timeout alto para processamento OCR
        'graceful_timeout': 120,
        'keepalive': 5,
        'max_requests': 1000,
        'max_requests_jitter': 100,
        'preload_app': False,  # Não fazer preload para evitar timeout
        'access_logfile': '-',
        'error_logfile': '-',
        'log_level': 'info',
        'worker_tmp_dir': '/dev/shm',  # Usar memória para worker heartbeat
        # Configurações especiais para Railway
        'limit_request_line': 0,
        'limit_request_fields': 100,
        'limit_request_field_size': 0,
    }
    
    # Criar e executar aplicação
    StandaloneApplication(app, options).run()

if __name__ == '__main__':
    main()