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

from flask import Flask, request, jsonify, make_response # send_file não é usado, removido
from flask_cors import CORS
import redis
import structlog

import config as config_module
from medical_ocr import MedicalOCRProcessor
from utils.image_processor import ImageProcessor
from utils.medical_parser import MedicalParameterParser

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

# Configurar Flask-CORS
CORS(app, resources={
    r"/ocr*": {"origins": "https://essencialab.app", "supports_credentials": True},
    r"/parameters": {"origins": "https://essencialab.app", "supports_credentials": True},
    r"/batch*": {"origins": "https://essencialab.app", "supports_credentials": True},
    r"/health": {"origins": "*", "supports_credentials": True},
    r"/info": {"origins": "*", "supports_credentials": True},
    r"/test": {"origins": "*", "supports_credentials": True} # Mantendo rota de teste por enquanto
})

# Configurar Redis para cache
try:
    redis_client = redis.from_url(config_module.config.REDIS_URL, decode_responses=True)
    redis_client.ping()
    logger.info("Redis conectado com sucesso", redis_url=config_module.config.REDIS_URL)
except Exception as e:
    logger.error("Erro ao conectar Redis", error=str(e), exc_info=True)
    redis_client = None

# Inicializar processadores de forma lazy (apenas quando necessário)
ocr_processor: Optional[MedicalOCRProcessor] = None
image_processor: Optional[ImageProcessor] = None
medical_parser: Optional[MedicalParameterParser] = None

def get_ocr_processor() -> MedicalOCRProcessor:
    global ocr_processor
    if ocr_processor is None:
        logger.info("Inicializando MedicalOCRProcessor...")
        ocr_processor = MedicalOCRProcessor()
        logger.info("MedicalOCRProcessor inicializado.")
    return ocr_processor

def get_image_processor() -> ImageProcessor:
    global image_processor
    if image_processor is None:
        logger.info("Inicializando ImageProcessor...")
        image_processor = ImageProcessor()
        logger.info("ImageProcessor inicializado.")
    return image_processor

def get_medical_parser() -> MedicalParameterParser:
    global medical_parser
    if medical_parser is None:
        logger.info("Inicializando MedicalParameterParser...")
        medical_parser = MedicalParameterParser()
        logger.info("MedicalParameterParser inicializado.")
    return medical_parser

def require_api_key(f):
    """Decorator para validar API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('Authorization')
        if api_key:
            api_key = api_key.replace('Bearer ', '')
        
        if not api_key or api_key != config_module.config.API_KEY:
            logger.warn("Tentativa de acesso com API key inválida ou ausente", received_key=api_key)
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
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0', # Versão da API
            'components': {
                'paddleocr': 'ready', # Assumimos que está pronto se a app iniciou; a inicialização é lazy
                'redis': 'healthy' if redis_client else 'unhealthy',
                'image_processor': 'ready',
                'medical_parser': 'ready'
            }
        }
        if redis_client:
            try:
                redis_client.ping()
            except Exception:
                logger.error("Health check: Falha no ping do Redis", exc_info=True)
                health_status['components']['redis'] = 'unhealthy'
        
        unhealthy_components = [k for k, v in health_status['components'].items() if v == 'unhealthy']
        if unhealthy_components:
            health_status['status'] = 'degraded'
            health_status['issues'] = unhealthy_components
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
    except Exception as e:
        logger.error("Erro no health check", error=str(e), exc_info=True)
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
            '/parameters': 'Lista de parâmetros suportados (GET)',
            '/batch': 'Processamento em lote (POST)',
            '/test': 'Rota de teste simples (se mantida)'
        },
        'supported_formats': config_module.config.ALLOWED_EXTENSIONS,
        'max_file_size': config_module.config.MAX_FILE_SIZE,
        'languages': [config_module.config.PADDLE_OCR_LANG],
        'features': {
            'gpu_enabled': config_module.config.ENABLE_GPU,
            'cache_enabled': redis_client is not None,
            'medical_parsing': True, # Assumindo que a funcionalidade completa está restaurada
            'structured_output': True # Assumindo que a funcionalidade completa está restaurada
        }
    })

@app.route('/test', methods=['GET']) 
def test_route():
    logger.info("Rota /test acessada") 
    return jsonify({'message': 'Servidor está no ar! OCR Restaurado (esperançosamente).', 'timestamp': datetime.utcnow().isoformat()})

@app.route('/parameters', methods=['GET']) 
@require_api_key 
def list_parameters():
    """Lista parâmetros médicos suportados"""
    return jsonify({
        'categories': config_module.config.MEDICAL_CATEGORIES,
        'reference_ranges': config_module.config.REFERENCE_RANGES,
        'total_parameters': sum(len(params) for params in config_module.config.MEDICAL_CATEGORIES.values())
    })

@app.route('/ocr', methods=['POST']) 
@require_api_key 
def process_ocr():
    """Endpoint principal para processamento OCR"""
    start_time = time.time()
    request_id = hashlib.md5(f"{time.time()}".encode()).hexdigest()[:8]
    logger.info("Iniciando processamento OCR", request_id=request_id)
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado', 'message': 'Envie um arquivo no campo "file"'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Arquivo vazio', 'message': 'Selecione um arquivo válido'}), 400
        
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if file_ext not in config_module.config.ALLOWED_EXTENSIONS:
            return jsonify({'error': 'Formato não suportado', 'message': f'Formatos aceitos: {", ".join(config_module.config.ALLOWED_EXTENSIONS)}', 'received': file_ext}), 400
        
        file_data = file.read()
        if len(file_data) > config_module.config.MAX_FILE_SIZE:
            return jsonify({'error': 'Arquivo muito grande', 'message': f'Tamanho máximo: {config_module.config.MAX_FILE_SIZE / 1024 / 1024:.1f}MB', 'received_size': f'{len(file_data) / 1024 / 1024:.1f}MB'}), 400
        
        file_hash = get_file_hash(file_data)
        processing_params = {
            'use_gpu': request.form.get('use_gpu', str(config_module.config.ENABLE_GPU)).lower() == 'true',
            'confidence_threshold': float(request.form.get('confidence_threshold', config_module.config.CONFIDENCE_THRESHOLD)),
            'extract_tables': request.form.get('extract_tables', 'true').lower() == 'true',
            'extract_layout': request.form.get('extract_layout', 'true').lower() == 'true',
            'medical_parsing': request.form.get('medical_parsing', 'true').lower() == 'true'
        }
        
        cache_key = get_cache_key(file_hash, processing_params)
        if redis_client:
            try:
                cached_result_str = redis_client.get(cache_key)
                if cached_result_str:
                    import json # Mover import para dentro do if para evitar import desnecessário
                    cached_result = json.loads(cached_result_str)
                    logger.info("Resultado encontrado no cache", request_id=request_id, cache_key=cache_key)
                    cached_result['cached'] = True
                    cached_result['cache_key'] = cache_key
                    # Não recalcular processing_time_ms para cache, ou usar um valor fixo/indicativo
                    return jsonify(cached_result)
            except Exception as e:
                logger.warning("Erro ao acessar cache", error=str(e), exc_info=True)
        
        logger.info("Processando arquivo", request_id=request_id, filename=file.filename, size_mb=f"{len(file_data) / 1024 / 1024:.2f}", file_hash=file_hash)
        
        processed_image_data = file_data
        if file_ext in ['jpg', 'jpeg', 'png', 'bmp', 'tiff']:
            try:
                img_proc = get_image_processor()
                processed_image_data = img_proc.preprocess_image(file_data)
                logger.info("Imagem pré-processada", request_id=request_id)
            except Exception as e:
                logger.warning("Erro no pré-processamento da imagem", error=str(e), exc_info=True)
                # Continuar com os dados originais do arquivo se o pré-processamento falhar
        
        ocr_proc_instance = get_ocr_processor()
        ocr_result = ocr_proc_instance.process_file(processed_image_data, file_extension=file_ext, **processing_params)
        logger.info("OCR concluído", request_id=request_id, confidence=ocr_result.get('confidence', 0), text_length=len(ocr_result.get('text', '')))
        
        structured_data = None
        if processing_params['medical_parsing'] and ocr_result.get('text'):
            try:
                med_parser_instance = get_medical_parser()
                structured_data = med_parser_instance.parse_medical_text(ocr_result['text'], confidence_threshold=processing_params['confidence_threshold'])
                logger.info("Parsing médico concluído", request_id=request_id, parameters_found=len(structured_data.get('parameters', [])))
            except Exception as e:
                logger.error("Erro no parsing médico", error=str(e), exc_info=True)
                structured_data = {'error': f'Erro no parsing médico: {str(e)}'}
        
        response_data = {
            'success': True,
            'request_id': request_id,
            'text': ocr_result.get('text', ''),
            'confidence': ocr_result.get('confidence', 0),
            'processing_time_ms': int((time.time() - start_time) * 1000),
            'file_info': {'filename': file.filename, 'size_bytes': len(file_data), 'format': file_ext, 'hash': file_hash},
            'ocr_details': {'provider': 'paddleocr', 'language': config_module.config.PADDLE_OCR_LANG, 'gpu_used': processing_params['use_gpu'], 'confidence_threshold': processing_params['confidence_threshold']}
        }
        if structured_data:
            response_data['structured_data'] = structured_data
        if ocr_result.get('tables'):
            response_data['tables'] = ocr_result['tables']
        if ocr_result.get('layout'):
            response_data['layout'] = ocr_result['layout']
        
        if redis_client and response_data['confidence'] > 0.5: # Usar confidence da resposta montada
            try:
                import json # Mover import para dentro do if
                # Não adicionar 'cached' ou 'cache_key' ao que é salvo no cache
                redis_client.setex(cache_key, config_module.config.CACHE_TTL, json.dumps(response_data, ensure_ascii=False))
                logger.info("Resultado salvo no cache", cache_key=cache_key)
            except Exception as e:
                logger.warning("Erro ao salvar no cache", error=str(e), exc_info=True)
        
        logger.info("Processamento OCR concluído com sucesso", request_id=request_id, total_time_ms=response_data['processing_time_ms'])
        return jsonify(response_data)
        
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        logger.error("Erro crítico no processamento OCR", request_id=request_id, error=error_msg, trace=error_trace, exc_info=True)
        return jsonify({'success': False, 'error': 'Erro interno do servidor durante OCR', 'message': error_msg, 'request_id': request_id, 'processing_time_ms': int((time.time() - start_time) * 1000)}), 500

def _process_single_file_for_batch(file_obj, index: int, processing_params: Dict[str, Any]) -> Dict[str, Any]:
    """Função auxiliar para processar um único arquivo dentro de um lote."""
    file_start_time = time.time()
    try:
        if file_obj.filename == '':
            return {'file_index': index, 'filename': 'N/A', 'success': False, 'error': 'Arquivo vazio'}

        file_ext = file_obj.filename.rsplit('.', 1)[1].lower() if '.' in file_obj.filename else ''
        if file_ext not in config_module.config.ALLOWED_EXTENSIONS:
            return {'file_index': index, 'filename': file_obj.filename, 'success': False, 'error': f'Formato não suportado: {file_ext}'}

        file_data = file_obj.read()
        if len(file_data) > config_module.config.MAX_FILE_SIZE:
            return {'file_index': index, 'filename': file_obj.filename, 'success': False, 'error': 'Arquivo muito grande'}

        processed_image_data = file_data
        if file_ext in ['jpg', 'jpeg', 'png', 'bmp', 'tiff']:
            img_proc = get_image_processor()
            processed_image_data = img_proc.preprocess_image(file_data)

        ocr_proc_instance = get_ocr_processor()
        ocr_result = ocr_proc_instance.process_file(processed_image_data, file_extension=file_ext, **processing_params)
        
        structured_data = None
        if processing_params['medical_parsing'] and ocr_result.get('text'):
            med_parser_instance = get_medical_parser()
            structured_data = med_parser_instance.parse_medical_text(ocr_result['text'], confidence_threshold=processing_params['confidence_threshold'])

        result = {
            'file_index': index,
            'filename': file_obj.filename,
            'success': True,
            'text': ocr_result.get('text', ''),
            'confidence': ocr_result.get('confidence', 0),
            'processing_time_ms': int((time.time() - file_start_time) * 1000)
        }
        if structured_data:
            result['structured_data'] = structured_data
        return result
    except Exception as e:
        logger.error(f"Erro ao processar arquivo {file_obj.filename} no lote", error=str(e), exc_info=True)
        return {'file_index': index, 'filename': file_obj.filename, 'success': False, 'error': str(e), 'processing_time_ms': int((time.time() - file_start_time) * 1000)}

@app.route('/batch', methods=['POST']) 
@require_api_key 
def process_batch():
    """Processamento em lote de múltiplos arquivos"""
    start_time = time.time()
    request_id = hashlib.md5(f"batch_{time.time()}".encode()).hexdigest()[:8]
    logger.info("Iniciando processamento em lote", request_id=request_id)
    
    try:
        files = request.files.getlist('files') # Alterado de 'file' para 'files'
        if not files:
            return jsonify({'error': 'Nenhum arquivo enviado', 'message': 'Envie arquivos no campo "files"'}), 400
        
        if len(files) > config_module.config.BATCH_MAX_FILES: # Usar config para max files
            return jsonify({'error': 'Muitos arquivos', 'message': f'Máximo {config_module.config.BATCH_MAX_FILES} arquivos por lote', 'received': len(files)}), 400
        
        processing_params = {
            'use_gpu': request.form.get('use_gpu', str(config_module.config.ENABLE_GPU)).lower() == 'true',
            'confidence_threshold': float(request.form.get('confidence_threshold', config_module.config.CONFIDENCE_THRESHOLD)),
            'extract_tables': request.form.get('extract_tables', 'true').lower() == 'true', # Manter, pode ser útil
            'extract_layout': request.form.get('extract_layout', 'true').lower() == 'true', # Manter
            'medical_parsing': request.form.get('medical_parsing', 'true').lower() == 'true'
        }

        results = [_process_single_file_for_batch(f, i, processing_params) for i, f in enumerate(files)]
        
        successful_count = sum(1 for r in results if r.get('success'))
        failed_count = len(results) - successful_count

        response = {
            'success': True, # Sucesso da requisição batch, não necessariamente de todos os arquivos
            'request_id': request_id,
            'batch_info': {'total_files': len(files), 'successful': successful_count, 'failed': failed_count},
            'results': results,
            'total_processing_time_ms': int((time.time() - start_time) * 1000)
        }
        return jsonify(response)
    except Exception as e:
        logger.error("Erro crítico no processamento em lote", error=str(e), trace=traceback.format_exc(), exc_info=True)
        return jsonify({'success': False, 'error': 'Erro interno no processamento em lote', 'message': str(e), 'request_id': request_id}), 500

@app.errorhandler(413) 
def request_entity_too_large(error):
    """Handler para arquivos muito grandes"""
    logger.warning("Erro 413: Request entity too large") 
    return jsonify({
        'error': 'Arquivo muito grande', 
        'message': f'Tamanho máximo permitido: {config_module.config.MAX_FILE_SIZE / 1024 / 1024:.1f}MB' 
    }), 413

@app.errorhandler(404) 
def not_found(error):
    """Handler para rotas não encontradas"""
    return jsonify({
        'error': 'Endpoint não encontrado',
        'message': 'Verifique a URL e método HTTP',
        'available_endpoints': ['/health', '/info', '/ocr', '/parameters', '/batch', '/test'] # Atualizado
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handler para erros internos"""
    logger.error("Erro 500: Erro interno do servidor", error_details=str(error), exc_info=True) 
    return jsonify({
        'error': 'Erro interno do servidor' 
    }), 500
