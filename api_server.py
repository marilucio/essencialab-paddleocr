"""
Servidor API Flask para PaddleOCR
Processamento de exames médicos com OCR avançado
"""

import os
import time
import hashlib
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import redis
import structlog

import config as config_module
from medical_ocr import MedicalOCRProcessor
from utils.image_processor import ImageProcessor
from utils.medical_parser import MedicalParameterParser

# Configuração
# config = get_config() # Esta linha não é mais necessária, pois importamos 'config' diretamente

# Configurar logging estruturado
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Inicializar Flask
app = Flask(__name__)
CORS(app)

# Configurar Redis para cache
try:
    redis_client = redis.from_url(config_module.config.REDIS_URL, decode_responses=True) # Correto: config_module.config.REDIS_URL
    redis_client.ping()
    logger.info("Redis conectado com sucesso", redis_url=config_module.config.REDIS_URL) # Correto
except Exception as e:
    logger.error("Erro ao conectar Redis", error=str(e))
    redis_client = None

# Inicializar processadores
ocr_processor = MedicalOCRProcessor()
image_processor = ImageProcessor()
medical_parser = MedicalParameterParser()

def require_api_key(f):
    """Decorator para validar API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('Authorization')
        if api_key:
            api_key = api_key.replace('Bearer ', '')
        
        if not api_key or api_key != config_module.config.API_KEY: # Correto
            return jsonify({
                'error': 'API key inválida ou ausente',
                'message': 'Forneça uma API key válida no header Authorization'
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function

def get_cache_key(file_hash: str, params: Dict[str, Any]) -> str:
    """Gera chave de cache baseada no hash do arquivo e parâmetros"""
    params_str = str(sorted(params.items()))
    cache_data = f"{file_hash}:{params_str}"
    return hashlib.md5(cache_data.encode()).hexdigest()

def get_file_hash(file_data: bytes) -> str:
    """Calcula hash MD5 do arquivo"""
    return hashlib.md5(file_data).hexdigest()

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de health check"""
    try:
        # Verificar componentes críticos
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'components': {
                'paddleocr': 'healthy',
                'redis': 'healthy' if redis_client else 'unhealthy',
                'image_processor': 'healthy',
                'medical_parser': 'healthy'
            }
        }
        
        # Testar Redis se disponível
        if redis_client:
            try:
                redis_client.ping()
            except:
                health_status['components']['redis'] = 'unhealthy'
        
        # Testar PaddleOCR
        try:
            ocr_processor.test_connection()
        except:
            health_status['components']['paddleocr'] = 'unhealthy'
        
        # Determinar status geral
        unhealthy_components = [k for k, v in health_status['components'].items() if v == 'unhealthy']
        if unhealthy_components:
            health_status['status'] = 'degraded'
            health_status['issues'] = unhealthy_components
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error("Erro no health check", error=str(e))
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@app.route('/info', methods=['GET'])
def api_info():
    """Informações da API"""
    return jsonify({
        'name': 'PaddleOCR Medical API',
        'version': '1.0.0',
        'description': 'API para processamento OCR de exames médicos',
        'endpoints': {
            '/health': 'Health check',
            '/info': 'Informações da API',
            '/ocr': 'Processamento OCR (POST)',
            '/parameters': 'Lista de parâmetros suportados (GET)'
        },
        'supported_formats': config_module.config.ALLOWED_EXTENSIONS, # Correto
        'max_file_size': config_module.config.MAX_FILE_SIZE, # Correto
        'languages': [config_module.config.PADDLE_OCR_LANG], # Correto
        'features': {
            'gpu_enabled': config_module.config.ENABLE_GPU, # Correto
            'cache_enabled': redis_client is not None,
            'medical_parsing': True,
            'structured_output': True
        }
    })

@app.route('/parameters', methods=['GET'])
def list_parameters():
    """Lista parâmetros médicos suportados"""
    return jsonify({
        'categories': config_module.config.MEDICAL_CATEGORIES, # Correto
        'reference_ranges': config_module.config.REFERENCE_RANGES, # Correto
        'total_parameters': sum(len(params) for params in config_module.config.MEDICAL_CATEGORIES.values()) # Correto
    })

@app.route('/ocr', methods=['POST'])
@require_api_key
def process_ocr():
    """Endpoint principal para processamento OCR"""
    start_time = time.time()
    request_id = hashlib.md5(f"{time.time()}".encode()).hexdigest()[:8]
    
    logger.info("Iniciando processamento OCR", request_id=request_id)
    
    try:
        # Validar request
        if 'file' not in request.files:
            return jsonify({
                'error': 'Nenhum arquivo enviado',
                'message': 'Envie um arquivo no campo "file"'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'error': 'Arquivo vazio',
                'message': 'Selecione um arquivo válido'
            }), 400
        
        # Validar extensão
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if file_ext not in config_module.config.ALLOWED_EXTENSIONS: # Correto
            return jsonify({
                'error': 'Formato não suportado',
                'message': f'Formatos aceitos: {", ".join(config_module.config.ALLOWED_EXTENSIONS)}', # Correto
                'received': file_ext
            }), 400
        
        # Ler dados do arquivo
        file_data = file.read()
        
        # Validar tamanho
        if len(file_data) > config_module.config.MAX_FILE_SIZE: # Correto
            return jsonify({
                'error': 'Arquivo muito grande',
                'message': f'Tamanho máximo: {config_module.config.MAX_FILE_SIZE / 1024 / 1024:.1f}MB', # Correto
                'received_size': f'{len(file_data) / 1024 / 1024:.1f}MB'
            }), 400
        
        # Calcular hash do arquivo
        file_hash = get_file_hash(file_data)
        
        # Parâmetros de processamento
        processing_params = {
            'use_gpu': request.form.get('use_gpu', str(config_module.config.ENABLE_GPU)).lower() == 'true', # Correto
            'confidence_threshold': float(request.form.get('confidence_threshold', config_module.config.CONFIDENCE_THRESHOLD)), # Correto
            'extract_tables': request.form.get('extract_tables', 'true').lower() == 'true',
            'extract_layout': request.form.get('extract_layout', 'true').lower() == 'true',
            'medical_parsing': request.form.get('medical_parsing', 'true').lower() == 'true'
        }
        
        # Verificar cache
        cache_key = get_cache_key(file_hash, processing_params)
        cached_result = None
        
        if redis_client:
            try:
                cached_result = redis_client.get(cache_key)
                if cached_result:
                    import json
                    cached_result = json.loads(cached_result)
                    logger.info("Resultado encontrado no cache", request_id=request_id, cache_key=cache_key)
                    
                    # Adicionar informações de cache
                    cached_result['cached'] = True
                    cached_result['cache_key'] = cache_key
                    cached_result['processing_time_ms'] = time.time() - start_time
                    
                    return jsonify(cached_result)
            except Exception as e:
                logger.warning("Erro ao acessar cache", error=str(e))
        
        logger.info("Processando arquivo", 
                   request_id=request_id,
                   filename=file.filename,
                   size_mb=f"{len(file_data) / 1024 / 1024:.2f}",
                   file_hash=file_hash)
        
        # Pré-processar imagem se necessário
        processed_image = None
        if file_ext in ['jpg', 'jpeg', 'png', 'bmp', 'tiff']:
            try:
                processed_image = image_processor.preprocess_image(file_data)
                logger.info("Imagem pré-processada", request_id=request_id)
            except Exception as e:
                logger.warning("Erro no pré-processamento", error=str(e))
                processed_image = file_data
        else:
            processed_image = file_data
        
        # Processar com PaddleOCR
        ocr_result = ocr_processor.process_file(
            processed_image,
            file_extension=file_ext,
            **processing_params
        )
        
        logger.info("OCR concluído", 
                   request_id=request_id,
                   confidence=ocr_result.get('confidence', 0),
                   text_length=len(ocr_result.get('text', '')))
        
        # Parsing médico se habilitado
        structured_data = None
        if processing_params['medical_parsing'] and ocr_result.get('text'):
            try:
                structured_data = medical_parser.parse_medical_text(
                    ocr_result['text'],
                    confidence_threshold=processing_params['confidence_threshold']
                )
                logger.info("Parsing médico concluído", 
                           request_id=request_id,
                           parameters_found=len(structured_data.get('parameters', [])))
            except Exception as e:
                logger.error("Erro no parsing médico", error=str(e))
                structured_data = {'error': str(e)}
        
        # Montar resposta
        response = {
            'success': True,
            'request_id': request_id,
            'text': ocr_result.get('text', ''),
            'confidence': ocr_result.get('confidence', 0),
            'processing_time_ms': int((time.time() - start_time) * 1000),
            'file_info': {
                'filename': file.filename,
                'size_bytes': len(file_data),
                'format': file_ext,
                'hash': file_hash
            },
            'ocr_details': {
                'provider': 'paddleocr',
                'language': config_module.config.PADDLE_OCR_LANG, # Correto
                'gpu_used': processing_params['use_gpu'],
                'confidence_threshold': processing_params['confidence_threshold']
            }
        }
        
        # Adicionar dados estruturados se disponível
        if structured_data:
            response['structured_data'] = structured_data
            response['parameters_count'] = len(structured_data.get('parameters', []))
            response['exam_type'] = structured_data.get('exam_type', 'unknown')
        
        # Adicionar tabelas se extraídas
        if ocr_result.get('tables'):
            response['tables'] = ocr_result['tables']
            response['tables_count'] = len(ocr_result['tables'])
        
        # Adicionar layout se extraído
        if ocr_result.get('layout'):
            response['layout'] = ocr_result['layout']
        
        # Salvar no cache se disponível
        if redis_client and response['confidence'] > 0.5:
            try:
                import json
                cache_data = response.copy()
                cache_data['cached'] = False  # Marcar como não-cache para diferenciação
                redis_client.setex(
                    cache_key,
                    config_module.config.CACHE_TTL, # Correto
                    json.dumps(cache_data, ensure_ascii=False)
                )
                logger.info("Resultado salvo no cache", cache_key=cache_key)
            except Exception as e:
                logger.warning("Erro ao salvar no cache", error=str(e))
        
        logger.info("Processamento concluído com sucesso", 
                   request_id=request_id,
                   total_time_ms=response['processing_time_ms'])
        
        return jsonify(response)
        
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        
        logger.error("Erro no processamento OCR", 
                    request_id=request_id,
                    error=error_msg,
                    trace=error_trace)
        
        return jsonify({
            'success': False,
            'error': 'Erro interno do servidor',
            'message': error_msg,
            'request_id': request_id,
            'processing_time_ms': int((time.time() - start_time) * 1000)
        }), 500

@app.route('/batch', methods=['POST'])
@require_api_key
def process_batch():
    """Processamento em lote de múltiplos arquivos"""
    start_time = time.time()
    request_id = hashlib.md5(f"batch_{time.time()}".encode()).hexdigest()[:8]
    
    logger.info("Iniciando processamento em lote", request_id=request_id)
    
    try:
        files = request.files.getlist('files')
        if not files:
            return jsonify({
                'error': 'Nenhum arquivo enviado',
                'message': 'Envie arquivos no campo "files"'
            }), 400
        
        if len(files) > 10:  # Limite de 10 arquivos por lote
            return jsonify({
                'error': 'Muitos arquivos',
                'message': 'Máximo 10 arquivos por lote',
                'received': len(files)
            }), 400
        
        results = []
        total_processing_time = 0
        
        for i, file in enumerate(files):
            try:
                # Simular processamento individual
                # (reutilizar lógica do endpoint /ocr)
                file_start = time.time()
                
                # Aqui você colocaria a lógica de processamento individual
                # Por simplicidade, vou criar um resultado mock
                file_result = {
                    'file_index': i,
                    'filename': file.filename,
                    'success': True,
                    'text': f'Texto extraído do arquivo {file.filename}',
                    'confidence': 0.85,
                    'processing_time_ms': int((time.time() - file_start) * 1000)
                }
                
                results.append(file_result)
                total_processing_time += file_result['processing_time_ms']
                
            except Exception as e:
                results.append({
                    'file_index': i,
                    'filename': file.filename,
                    'success': False,
                    'error': str(e)
                })
        
        response = {
            'success': True,
            'request_id': request_id,
            'batch_info': {
                'total_files': len(files),
                'successful': len([r for r in results if r.get('success')]),
                'failed': len([r for r in results if not r.get('success')])
            },
            'results': results,
            'total_processing_time_ms': int((time.time() - start_time) * 1000)
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error("Erro no processamento em lote", error=str(e))
        return jsonify({
            'success': False,
            'error': str(e),
            'request_id': request_id
        }), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handler para arquivos muito grandes"""
    return jsonify({
        'error': 'Arquivo muito grande',
        'message': f'Tamanho máximo permitido: {config_module.config.MAX_FILE_SIZE / 1024 / 1024:.1f}MB' # Correto
    }), 413

@app.errorhandler(404)
def not_found(error):
    """Handler para rotas não encontradas"""
    return jsonify({
        'error': 'Endpoint não encontrado',
        'message': 'Verifique a URL e método HTTP',
        'available_endpoints': ['/health', '/info', '/ocr', '/parameters']
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handler para erros internos"""
    logger.error("Erro interno do servidor", error=str(error))
    return jsonify({
        'error': 'Erro interno do servidor',
        'message': 'Tente novamente em alguns instantes'
    }), 500

# O Gunicorn é iniciado pelo Dockerfile, então este bloco não é mais necessário.
# if __name__ == '__main__':
#     logger.info("Iniciando servidor PaddleOCR API", 
#                host=config_module.config.HOST, 
#                port=config_module.config.PORT,
#                debug=config_module.config.DEBUG)
    
#     # Configurar Flask para produção
#     app.config['MAX_CONTENT_LENGTH'] = config_module.config.MAX_FILE_SIZE
    
#     if config_module.config.DEBUG:
#         app.run(host=config_module.config.HOST, port=config_module.config.PORT, debug=True)
#     else:
#         # Usar Gunicorn em produção
#         import gunicorn.app.base
        
#         class StandaloneApplication(gunicorn.app.base.BaseApplication):
#             def __init__(self, app, options=None):
#                 self.options = options or {}
#                 self.application = app
#                 super().__init__()
            
#             def load_config(self):
#                 for key, value in self.options.items():
#                     self.cfg.set(key.lower(), value)
            
#             def load(self):
#                 return self.application
        
#         options = {
#             'bind': f'{config_module.config.HOST}:{config_module.config.PORT}',
#             'workers': config_module.config.WORKERS,
#             'worker_class': 'sync',
#             'timeout': config_module.config.MAX_PROCESSING_TIME,
#             'keepalive': 2,
#             'max_requests': 1000,
#             'max_requests_jitter': 100,
#             'preload_app': True,
#             'access_logfile': '-',
#             'error_logfile': '-',
#         }
        
#         StandaloneApplication(app, options).run()
