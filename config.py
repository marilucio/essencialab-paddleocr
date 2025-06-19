# Adicionar esta função no final do config.py

def validate_config() -> bool:
    """Valida as configurações"""
    try:
        # Verificar diretórios - com fallback para Railway
        try:
            os.makedirs(config.TEMP_DIR, exist_ok=True)
            os.makedirs(config.UPLOAD_DIR, exist_ok=True)
            
            # Railway pode não ter permissão para criar logs/ 
            log_dir = os.path.dirname(config.LOG_FILE)
            if log_dir and log_dir != '.':
                try:
                    os.makedirs(log_dir, exist_ok=True)
                except OSError:
                    # Fallback para logs no temp
                    config.LOG_FILE = './temp/paddleocr.log'
                    
        except OSError:
            # Se não conseguir criar diretórios, usar /tmp
            config.TEMP_DIR = '/tmp'
            config.UPLOAD_DIR = '/tmp'
            config.LOG_FILE = '/tmp/paddleocr.log'
        
        # Verificar valores críticos
        if config.MAX_FILE_SIZE <= 0:
            config.MAX_FILE_SIZE = 10485760  # 10MB default
        
        if config.CONFIDENCE_THRESHOLD < 0 or config.CONFIDENCE_THRESHOLD > 1:
            config.CONFIDENCE_THRESHOLD = 0.7  # Default
        
        return True
        
    except Exception as e:
        print(f"Erro na validação da configuração: {e}")
        return False