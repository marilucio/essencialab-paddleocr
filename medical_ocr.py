"""
Processador principal PaddleOCR para exames médicos
Integração com PaddleOCR 2.7+ e PP-Structure
"""

import os
import io
import time
import tempfile
from typing import Dict, Any, List, Optional, Union
import numpy as np
from PIL import Image
import cv2
import fitz  # PyMuPDF
from pdf2image import convert_from_bytes

try:
    from paddleocr import PaddleOCR, draw_ocr
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    print("PaddleOCR não disponível. Instale com: pip install paddleocr")

import config as config_module # Alterado para importar o módulo inteiro
import structlog

logger = structlog.get_logger()
# config = get_config() # Esta linha não é mais necessária

class MedicalOCRProcessor:
    """Processador principal para OCR de exames médicos"""
    
    def __init__(self):
        self.config = config_module.config # Usar a instância importada
        self.ocr_engine = None
        self.structure_engine = None
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Inicializa os engines do PaddleOCR"""
        if not PADDLEOCR_AVAILABLE:
            logger.warning("PaddleOCR não disponível - usando modo mock")
            return
        
        try:
            # Inicializar PaddleOCR principal
            self.ocr_engine = PaddleOCR(
                use_angle_cls=self.config.USE_ANGLE_CLS,
                lang=self.config.PADDLE_OCR_LANG,
                use_gpu=self.config.ENABLE_GPU,
                show_log=False,
                use_space_char=self.config.USE_SPACE_CHAR
            )
            
            # Inicializar PP-Structure para layout e tabelas
            try:
                from paddleocr import PPStructure
                self.structure_engine = PPStructure(
                    use_gpu=self.config.ENABLE_GPU,
                    show_log=False,
                    lang=self.config.PADDLE_OCR_LANG,
                    layout=True,
                    table=True,
                    ocr=True
                )
                logger.info("PP-Structure inicializado com sucesso")
            except Exception as e:
                logger.warning("PP-Structure não disponível", error=str(e))
                self.structure_engine = None
            
            logger.info("PaddleOCR inicializado com sucesso", 
                       gpu_enabled=self.config.ENABLE_GPU,
                       language=self.config.PADDLE_OCR_LANG)
            
        except Exception as e:
            logger.error("Erro ao inicializar PaddleOCR", error=str(e))
            self.ocr_engine = None
            self.structure_engine = None
    
    def test_connection(self):
        """Testa se o PaddleOCR está funcionando"""
        if not self.ocr_engine:
            raise Exception("PaddleOCR não inicializado")
        
        # Criar imagem de teste simples
        test_image = np.ones((100, 300, 3), dtype=np.uint8) * 255
        cv2.putText(test_image, 'TEST', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        try:
            result = self.ocr_engine.ocr(test_image, cls=False)
            return True
        except Exception as e:
            raise Exception(f"Teste do PaddleOCR falhou: {str(e)}")
    
    def process_file(self, 
                    file_data: Union[bytes, str], 
                    file_extension: str = 'jpg',
                    **kwargs) -> Dict[str, Any]:
        """
        Processa arquivo com PaddleOCR
        
        Args:
            file_data: Dados do arquivo (bytes) ou caminho (str)
            file_extension: Extensão do arquivo
            **kwargs: Parâmetros adicionais
        
        Returns:
            Dict com resultados do OCR
        """
        start_time = time.time()
        
        try:
            if file_extension.lower() == 'pdf':
                return self._process_pdf(file_data, **kwargs)
            else:
                return self._process_image(file_data, **kwargs)
                
        except Exception as e:
            logger.error("Erro no processamento", error=str(e))
            return {
                'text': '',
                'confidence': 0.0,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def _process_pdf(self, file_data: bytes, **kwargs) -> Dict[str, Any]:
        """Processa arquivo PDF"""
        start_time = time.time()
        
        try:
            # Primeiro, tentar extrair texto diretamente
            direct_text = self._extract_pdf_text_direct(file_data)
            
            if direct_text and len(direct_text.strip()) > 100:
                logger.info("PDF com texto pesquisável detectado")
                return {
                    'text': direct_text,
                    'confidence': 0.95,
                    'method': 'direct_text_extraction',
                    'processing_time': time.time() - start_time,
                    'pages_processed': 1
                }
            
            # Se não há texto suficiente, converter para imagens e fazer OCR
            logger.info("Convertendo PDF para imagens para OCR")
            images = self._pdf_to_images(file_data)
            
            all_results = []
            combined_text = ""
            total_confidence = 0
            
            for i, image in enumerate(images):
                logger.info(f"Processando página {i+1}/{len(images)}")
                
                page_result = self._process_image_array(image, **kwargs)
                all_results.append(page_result)
                
                if page_result.get('text'):
                    combined_text += f"\n--- Página {i+1} ---\n"
                    combined_text += page_result['text']
                    combined_text += "\n"
                
                total_confidence += page_result.get('confidence', 0)
            
            avg_confidence = total_confidence / len(images) if images else 0
            
            return {
                'text': combined_text.strip(),
                'confidence': avg_confidence,
                'method': 'ocr_from_images',
                'processing_time': time.time() - start_time,
                'pages_processed': len(images),
                'page_results': all_results
            }
            
        except Exception as e:
            logger.error("Erro no processamento de PDF", error=str(e))
            raise
    
    def _extract_pdf_text_direct(self, file_data: bytes) -> str:
        """Extrai texto diretamente do PDF se disponível"""
        try:
            doc = fitz.open(stream=file_data, filetype="pdf")
            text = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                if page_text.strip():
                    text += f"\n--- Página {page_num + 1} ---\n"
                    text += page_text
            
            doc.close()
            return text.strip()
            
        except Exception as e:
            logger.warning("Erro na extração direta de texto do PDF", error=str(e))
            return ""
    
    def _pdf_to_images(self, file_data: bytes) -> List[np.ndarray]:
        """Converte PDF para lista de imagens"""
        try:
            # Usar pdf2image para conversão
            images = convert_from_bytes(
                file_data,
                dpi=300,  # Alta resolução para melhor OCR
                fmt='RGB'
            )
            
            # Converter PIL Images para numpy arrays
            np_images = []
            for img in images:
                np_img = np.array(img)
                np_images.append(np_img)
            
            return np_images
            
        except Exception as e:
            logger.error("Erro na conversão PDF para imagens", error=str(e))
            raise
    
    def _process_image(self, file_data: bytes, **kwargs) -> Dict[str, Any]:
        """Processa arquivo de imagem"""
        try:
            # Converter bytes para numpy array
            image_array = np.frombuffer(file_data, np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            if image is None:
                raise ValueError("Não foi possível decodificar a imagem")
            
            return self._process_image_array(image, **kwargs)
            
        except Exception as e:
            logger.error("Erro no processamento de imagem", error=str(e))
            raise
    
    def _process_image_array(self, image: np.ndarray, **kwargs) -> Dict[str, Any]:
        """Processa array numpy de imagem"""
        start_time = time.time()
        
        if not self.ocr_engine:
            return self._mock_ocr_result(image, **kwargs)
        
        try:
            # Parâmetros de processamento
            extract_tables = kwargs.get('extract_tables', True)
            extract_layout = kwargs.get('extract_layout', True)
            confidence_threshold = kwargs.get('confidence_threshold', self.config.CONFIDENCE_THRESHOLD)
            
            result = {
                'text': '',
                'confidence': 0.0,
                'words': [],
                'lines': [],
                'processing_time': 0
            }
            
            # Usar PP-Structure se disponível e solicitado
            if self.structure_engine and (extract_tables or extract_layout):
                try:
                    structure_result = self._process_with_structure(image, **kwargs)
                    result.update(structure_result)
                except Exception as e:
                    logger.warning("Erro no PP-Structure, usando OCR básico", error=str(e))
                    basic_result = self._process_with_basic_ocr(image, confidence_threshold)
                    result.update(basic_result)
            else:
                # OCR básico
                basic_result = self._process_with_basic_ocr(image, confidence_threshold)
                result.update(basic_result)
            
            result['processing_time'] = time.time() - start_time
            return result
            
        except Exception as e:
            logger.error("Erro no processamento da imagem", error=str(e))
            raise
    
    def _process_with_structure(self, image: np.ndarray, **kwargs) -> Dict[str, Any]:
        """Processa imagem com PP-Structure para layout e tabelas"""
        try:
            # Processar com PP-Structure
            structure_result = self.structure_engine(image)
            
            text_parts = []
            tables = []
            layout_elements = []
            all_words = []
            confidences = []
            
            for region in structure_result:
                region_type = region.get('type', 'text')
                region_bbox = region.get('bbox', [0, 0, 0, 0])
                region_confidence = region.get('confidence', 0.0)
                
                if region_confidence > 0:
                    confidences.append(region_confidence)
                
                # Processar diferentes tipos de região
                if region_type == 'text':
                    if 'res' in region:
                        for line in region['res']:
                            if isinstance(line, list) and len(line) >= 2:
                                line_text = line[1]
                                line_confidence = line[0] if isinstance(line[0], (int, float)) else 0.8
                                
                                if line_confidence >= kwargs.get('confidence_threshold', 0.7):
                                    text_parts.append(line_text)
                                    
                                    # Adicionar palavras individuais
                                    words = line_text.split()
                                    for word in words:
                                        all_words.append({
                                            'text': word,
                                            'confidence': line_confidence,
                                            'bbox': region_bbox  # Simplificado
                                        })
                
                elif region_type == 'table':
                    table_data = self._extract_table_data(region)
                    if table_data:
                        tables.append(table_data)
                        # Adicionar texto da tabela ao texto geral
                        table_text = self._table_to_text(table_data)
                        text_parts.append(f"\n[TABELA]\n{table_text}\n[/TABELA]\n")
                
                # Adicionar elemento de layout
                layout_elements.append({
                    'type': region_type,
                    'bbox': region_bbox,
                    'confidence': region_confidence,
                    'content': region.get('res', '')
                })
            
            # Combinar texto
            combined_text = '\n'.join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return {
                'text': combined_text,
                'confidence': avg_confidence,
                'words': all_words,
                'tables': tables,
                'layout': layout_elements,
                'method': 'pp_structure'
            }
            
        except Exception as e:
            logger.error("Erro no PP-Structure", error=str(e))
            raise
    
    def _process_with_basic_ocr(self, image: np.ndarray, confidence_threshold: float) -> Dict[str, Any]:
        """Processa imagem com OCR básico do PaddleOCR"""
        try:
            # OCR básico
            ocr_result = self.ocr_engine.ocr(image, cls=True)
            
            if not ocr_result or not ocr_result[0]:
                return {
                    'text': '',
                    'confidence': 0.0,
                    'words': [],
                    'method': 'basic_ocr'
                }
            
            text_parts = []
            all_words = []
            confidences = []
            
            for line in ocr_result[0]:
                if len(line) >= 2:
                    bbox = line[0]  # Coordenadas da bounding box
                    text_info = line[1]  # (texto, confiança)
                    
                    if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                        text = text_info[0]
                        confidence = text_info[1]
                        
                        if confidence >= confidence_threshold:
                            text_parts.append(text)
                            confidences.append(confidence)
                            
                            # Adicionar palavras individuais
                            words = text.split()
                            for word in words:
                                all_words.append({
                                    'text': word,
                                    'confidence': confidence,
                                    'bbox': bbox
                                })
            
            combined_text = '\n'.join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return {
                'text': combined_text,
                'confidence': avg_confidence,
                'words': all_words,
                'method': 'basic_ocr'
            }
            
        except Exception as e:
            logger.error("Erro no OCR básico", error=str(e))
            raise
    
    def _extract_table_data(self, table_region: Dict) -> Optional[Dict]:
        """Extrai dados estruturados de uma tabela"""
        try:
            if 'res' not in table_region:
                return None
            
            table_html = table_region['res']
            
            # Aqui você implementaria a extração de dados da tabela HTML
            # Por simplicidade, vou retornar uma estrutura básica
            return {
                'type': 'table',
                'bbox': table_region.get('bbox', []),
                'confidence': table_region.get('confidence', 0.8),
                'html': table_html,
                'rows': [],  # Seria extraído do HTML
                'headers': []  # Seria extraído do HTML
            }
            
        except Exception as e:
            logger.warning("Erro na extração de tabela", error=str(e))
            return None
    
    def _table_to_text(self, table_data: Dict) -> str:
        """Converte dados de tabela para texto"""
        try:
            # Implementação simplificada
            return f"[Tabela detectada - {table_data.get('confidence', 0):.2f} confiança]"
        except:
            return "[Tabela detectada]"
    
    def _mock_ocr_result(self, image: np.ndarray, **kwargs) -> Dict[str, Any]:
        """Resultado mock quando PaddleOCR não está disponível"""
        logger.warning("Usando resultado mock - PaddleOCR não disponível")
        
        # Simular processamento baseado no tamanho da imagem
        height, width = image.shape[:2]
        mock_confidence = 0.75 + (min(width, height) / 2000) * 0.2  # Confiança baseada na resolução
        
        mock_text = """LABORATÓRIO EXEMPLO
        
HEMOGRAMA COMPLETO

Paciente: João Silva
Idade: 45 anos
Data: 15/06/2024

RESULTADOS:
Hemoglobina: 14.2 g/dL (12.0-16.0)
Hematócrito: 42.5% (36.0-48.0)
Leucócitos: 7.200 /mm³ (4.000-11.000)
Plaquetas: 280.000 /mm³ (150.000-450.000)

Observações: Valores dentro da normalidade.

Dr. Maria Santos
CRM 12345"""
        
        return {
            'text': mock_text,
            'confidence': min(mock_confidence, 0.95),
            'words': [
                {'text': word, 'confidence': mock_confidence, 'bbox': [0, 0, 100, 20]}
                for word in mock_text.split()
            ],
            'method': 'mock',
            'mock': True
        }
    
    def get_supported_formats(self) -> List[str]:
        """Retorna formatos suportados"""
        return self.config.ALLOWED_EXTENSIONS
    
    def get_engine_info(self) -> Dict[str, Any]:
        """Retorna informações sobre os engines"""
        return {
            'paddleocr_available': PADDLEOCR_AVAILABLE,
            'ocr_engine_initialized': self.ocr_engine is not None,
            'structure_engine_initialized': self.structure_engine is not None,
            'gpu_enabled': self.config.ENABLE_GPU,
            'language': self.config.PADDLE_OCR_LANG,
            'supported_formats': self.get_supported_formats()
        }
