"""
Configurações do serviço PaddleOCR
"""
import os
from typing import Optional, List, Dict # Adicionado List e Dict para type hinting
from dataclasses import dataclass, field # Adicionado field

@dataclass
class Config:
    """Configurações principais do serviço"""
    
    # API Configuration
    API_KEY: str = os.getenv('PADDLEOCR_API_KEY', os.getenv('API_KEY', 'paddleocr-key-2024'))
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', '5000')) # Ajustado para 5000 para corresponder ao Dockerfile
    DEBUG: bool = os.getenv('DEBUG', 'false').lower() == 'true'
    WORKERS: int = int(os.getenv('WORKERS', '2'))
    
    # Redis Configuration
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379')
    REDIS_DB: int = int(os.getenv('REDIS_DB', '0'))
    CACHE_TTL: int = int(os.getenv('CACHE_TTL', '3600'))  # 1 hora
    
    # PaddleOCR Configuration
    PADDLE_OCR_LANG: str = os.getenv('PADDLE_OCR_LANG', 'pt')
    ENABLE_GPU: bool = os.getenv('ENABLE_GPU', 'false').lower() == 'true'
    USE_ANGLE_CLS: bool = os.getenv('USE_ANGLE_CLS', 'true').lower() == 'true'
    USE_SPACE_CHAR: bool = os.getenv('USE_SPACE_CHAR', 'true').lower() == 'true'
    
    # File Processing
    MAX_FILE_SIZE: int = int(os.getenv('MAX_FILE_SIZE', '10485760'))  # 10MB
    ALLOWED_EXTENSIONS: List[str] = field(default_factory=lambda: ['jpg', 'jpeg', 'png', 'pdf', 'bmp', 'tiff'])
    TEMP_DIR: str = os.getenv('TEMP_DIR', './temp')
    UPLOAD_DIR: str = os.getenv('UPLOAD_DIR', './uploads')
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', './logs/paddleocr.log')
    LOG_MAX_SIZE: int = int(os.getenv('LOG_MAX_SIZE', '10485760'))  # 10MB
    LOG_BACKUP_COUNT: int = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    
    # Processing Configuration
    CONFIDENCE_THRESHOLD: float = float(os.getenv('CONFIDENCE_THRESHOLD', '0.7'))
    MIN_TEXT_LENGTH: int = int(os.getenv('MIN_TEXT_LENGTH', '3'))
    MAX_PROCESSING_TIME: int = int(os.getenv('MAX_PROCESSING_TIME', '300'))  # 5 minutos
    
    # Medical Parameters Configuration
    MEDICAL_CATEGORIES: Dict[str, List[str]] = field(default_factory=lambda: {
        'hematologia': [
            'hemoglobina', 'hematócrito', 'leucócitos', 'neutrófilos', 
            'linfócitos', 'monócitos', 'eosinófilos', 'basófilos', 
            'plaquetas', 'vhs', 'pcr'
        ],
        'bioquímica': [
            'glicose', 'glicemia', 'colesterol total', 'hdl', 'ldl', 
            'triglicerídeos', 'ácido úrico', 'proteínas totais', 
            'albumina', 'globulinas'
        ],
        'função_renal': [
            'creatinina', 'ureia', 'ácido úrico', 'clearance', 
            'tfg', 'microalbuminúria'
        ],
        'função_hepática': [
            'alt', 'ast', 'ggt', 'fosfatase alcalina', 'bilirrubina total',
            'bilirrubina direta', 'bilirrubina indireta'
        ],
        'hormonal': [
            'tsh', 't3', 't4', 't4 livre', 'cortisol', 'insulina',
            'testosterona', 'estradiol', 'progesterona', 'prolactina'
        ],
        'eletrólitos': [
            'sódio', 'potássio', 'cloro', 'cálcio', 'magnésio', 
            'fósforo', 'ferro', 'ferritina'
        ],
        'vitaminas': [
            'vitamina d', 'vitamina b12', 'ácido fólico', 'vitamina a',
            'vitamina e', 'vitamina c'
        ]
    })
    
    # Unidades conhecidas
    KNOWN_UNITS: List[str] = field(default_factory=lambda: [
        'g/dL', '%', '/mm³', 'mg/dL', 'mUI/L', 'ng/mL', 'pg/mL', 'UI/L', 'U/L', 'mL/min/1.73m2', 'mEq/L'
    ])

    # Reference Ranges (valores de referência padrão)
    REFERENCE_RANGES: Dict[str, Dict[str, any]] = field(default_factory=lambda: {
        'hemoglobina': {'min': 12.0, 'max': 16.0, 'unit': 'g/dL'},
        'hematócrito': {'min': 36.0, 'max': 48.0, 'unit': '%'},
        'leucócitos': {'min': 4000, 'max': 11000, 'unit': '/mm³'},
        'plaquetas': {'min': 150000, 'max': 450000, 'unit': '/mm³'},
        'glicose': {'min': 70, 'max': 99, 'unit': 'mg/dL'},
        'colesterol total': {'min': 0, 'max': 200, 'unit': 'mg/dL'},
        'hdl': {'min': 40, 'max': 999, 'unit': 'mg/dL'},
        'ldl': {'min': 0, 'max': 130, 'unit': 'mg/dL'},
        'triglicerídeos': {'min': 0, 'max': 150, 'unit': 'mg/dL'},
        'creatinina': {'min': 0.6, 'max': 1.2, 'unit': 'mg/dL'},
        'ureia': {'min': 15, 'max': 45, 'unit': 'mg/dL'},
        'tsh': {'min': 0.4, 'max': 4.0, 'unit': 'mUI/L'},
        'alt': {'min': 0, 'max': 41, 'unit': 'U/L'},
        'ast': {'min': 0, 'max': 40, 'unit': 'U/L'},
    })
    
    # Text Patterns for Parameter Extraction
    PARAMETER_PATTERNS: Dict[str, List[str]] = field(default_factory=lambda: {
        'hemoglobina': [
            r'(?:hemoglobina|hb)\s*:?\s*(\d+[,.]?\d*)\s*(?:g\/dl|mg\/dl)?',
            r'hb\s*(\d+[,.]?\d*)',
            r'hemoglobina\s*(\d+[,.]?\d*)'
        ],
        'hematócrito': [
            r'(?:hematócrito|ht|hct)\s*:?\s*(\d+[,.]?\d*)\s*%?',
            r'ht\s*(\d+[,.]?\d*)',
            r'hematócrito\s*(\d+[,.]?\d*)'
        ],
        'leucócitos': [
            r'(?:leucócitos|glóbulos brancos|wbc)\s*:?\s*(\d+[,.]?\d*)\s*(?:\/mm³|mil\/mm³|k\/ul)?',
            r'leucócitos\s*(\d+[,.]?\d*)',
            r'glóbulos brancos\s*(\d+[,.]?\d*)'
        ],
        'plaquetas': [
            r'(?:plaquetas|plt)\s*:?\s*(\d+[,.]?\d*)\s*(?:\/mm³|mil\/mm³|k\/ul)?',
            r'plaquetas\s*(\d+[,.]?\d*)',
            r'plt\s*(\d+[,.]?\d*)'
        ],
        'glicose': [
            r'(?:glicose|glicemia|glucose)\s*:?\s*(\d+[,.]?\d*)\s*(?:mg\/dl)?',
            r'glicose\s*(\d+[,.]?\d*)',
            r'glicemia\s*(\d+[,.]?\d*)'
        ],
        'colesterol_total': [
            r'(?:colesterol total|col total)\s*:?\s*(\d+[,.]?\d*)\s*(?:mg\/dl)?',
            r'colesterol total\s*(\d+[,.]?\d*)',
            r'col total\s*(\d+[,.]?\d*)'
        ],
        'hdl': [
            r'(?:hdl|hdl-c)\s*:?\s*(\d+[,.]?\d*)\s*(?:mg\/dl)?',
            r'hdl\s*(\d+[,.]?\d*)',
            r'hdl-c\s*(\d+[,.]?\d*)'
        ],
        'ldl': [
            r'(?:ldl|ldl-c)\s*:?\s*(\d+[,.]?\d*)\s*(?:mg\/dl)?',
            r'ldl\s*(\d+[,.]?\d*)',
            r'ldl-c\s*(\d+[,.]?\d*)'
        ],
        'triglicerídeos': [
            r'(?:triglicerídeos|triglicerides|tg)\s*:?\s*(\d+[,.]?\d*)\s*(?:mg\/dl)?',
            r'triglicerídeos\s*(\d+[,.]?\d*)',
            r'triglicerides\s*(\d+[,.]?\d*)'
        ],
        'creatinina': [
            r'(?:creatinina|creat)\s*:?\s*(\d+[,.]?\d*)\s*(?:mg\/dl)?',
            r'creatinina\s*(\d+[,.]?\d*)',
            r'creat\s*(\d+[,.]?\d*)'
        ],
        'ureia': [
            r'(?:ureia|uréia|bun)\s*:?\s*(\d+[,.]?\d*)\s*(?:mg\/dl)?',
            r'ureia\s*(\d+[,.]?\d*)',
            r'uréia\s*(\d+[,.]?\d*)'
        ],
        'tsh': [
            r'(?:tsh)\s*:?\s*(\d+[,.]?\d*)\s*(?:mui\/l|miu\/ml)?',
            r'tsh\s*(\d+[,.]?\d*)'
        ]
    })

# Instância global de configuração
config = Config()

def get_config() -> Config:
    """Retorna a instância de configuração"""
    return config

# Adicionar esta função no final do config.py
def validate_config() -> bool:
    """Valida as configurações"""
    global config # Precisamos declarar config como global para modificá-la aqui
    try:
        # Verificar diretórios - com fallback para Railway
        # Usar os diretórios padrão definidos na classe Config inicialmente
        temp_dir_to_check = config.TEMP_DIR
        upload_dir_to_check = config.UPLOAD_DIR
        log_file_to_check = config.LOG_FILE
        
        try:
            os.makedirs(temp_dir_to_check, exist_ok=True)
            os.makedirs(upload_dir_to_check, exist_ok=True)
            
            log_dir = os.path.dirname(log_file_to_check)
            if log_dir and log_dir != '.': # Evitar tentar criar '.' se LOG_FILE for apenas um nome de arquivo
                os.makedirs(log_dir, exist_ok=True)
                
        except OSError:
            # Se não conseguir criar diretórios, usar /tmp e atualizar a instância config
            print(f"OSError ao criar diretórios. Usando /tmp e atualizando config.")
            config.TEMP_DIR = '/tmp'
            config.UPLOAD_DIR = '/tmp'
            config.LOG_FILE = '/tmp/paddleocr.log'
            # Tentar criar /tmp (geralmente já existe e é gravável)
            os.makedirs(config.TEMP_DIR, exist_ok=True)
            os.makedirs(config.UPLOAD_DIR, exist_ok=True)
            # Não precisamos criar o diretório para /tmp/paddleocr.log pois /tmp já existe
        
        # Verificar valores críticos
        if config.MAX_FILE_SIZE <= 0:
            print(f"MAX_FILE_SIZE inválido ({config.MAX_FILE_SIZE}). Resetando para 10MB.")
            config.MAX_FILE_SIZE = 10485760  # 10MB default
        
        if not (0 <= config.CONFIDENCE_THRESHOLD <= 1):
            print(f"CONFIDENCE_THRESHOLD inválido ({config.CONFIDENCE_THRESHOLD}). Resetando para 0.7.")
            config.CONFIDENCE_THRESHOLD = 0.7  # Default
        
        return True
        
    except Exception as e:
        print(f"Erro na validação da configuração: {e}")
        return False

# Validar configuração na importação
if not validate_config():
    # Considerar se realmente queremos um RuntimeError aqui,
    # pois pode impedir o início do app se a validação falhar por permissões,
    # mesmo que tenhamos fallbacks.
    # Por agora, vamos apenas logar o erro se validate_config já imprime.
    print("AVISO: Validação da configuração encontrou problemas. A aplicação pode não funcionar como esperado.")
    # raise RuntimeError("Configuração inválida")
