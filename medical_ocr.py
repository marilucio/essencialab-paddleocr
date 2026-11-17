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
            
            # PP-Structure não é carregado: em páginas de laudo ele classificava o
            # conteúdo como "figura" e devolvia a página sem texto. PDFs sem camada
            # de texto usam o mesmo OCR das fotos (ver _process_image_array).
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
            direct_text_length = len(direct_text.strip()) if direct_text else 0
            
            logger.info(f"Extração direta de texto: {direct_text_length} caracteres")
            
            if direct_text and direct_text_length > 50:  # Reduzido de 100 para 50
                logger.info("PDF com texto pesquisável detectado", text_length=direct_text_length)
                return {
                    'text': direct_text,
                    'confidence': 0.95,
                    'method': 'direct_text_extraction',
                    'processing_time': time.time() - start_time,
                    'pages_processed': 1
                }
            
            # Se não há texto suficiente, tentar usar PyMuPDF para converter páginas
            logger.info("Texto insuficiente, tentando OCR com PyMuPDF")
            try:
                images = self._pdf_to_images_with_fitz(file_data)
                logger.info(f"Convertido para {len(images)} imagens usando PyMuPDF")
            except Exception as fitz_error:
                logger.warning(f"PyMuPDF falhou: {fitz_error}, tentando pdf2image")
                # Fallback para pdf2image (que precisa do Poppler)
                images = self._pdf_to_images(file_data)
                logger.info(f"Convertido para {len(images)} imagens usando pdf2image")
            
            all_results = []
            combined_text = ""
            total_confidence = 0
            
            for i, image in enumerate(images):
                logger.info(f"Processando página {i+1}/{len(images)}")

                page_result = self._process_image_array(image, _from_pdf=True, **kwargs)
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
    
    def _pdf_to_images_with_fitz(self, file_data: bytes) -> List[np.ndarray]:
        """Converte PDF para lista de imagens usando PyMuPDF (não precisa do Poppler)"""
        try:
            doc = fitz.open(stream=file_data, filetype="pdf")
            images = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Converter página para imagem com alta resolução
                mat = fitz.Matrix(3.0, 3.0)  # 3x zoom = ~300 DPI
                pix = page.get_pixmap(matrix=mat)
                
                # Converter para numpy array
                img_data = pix.tobytes("ppm")
                img = Image.open(io.BytesIO(img_data))
                np_img = np.array(img)
                images.append(np_img)
                
                pix = None  # Liberar memória
            
            doc.close()
            return images
            
        except Exception as e:
            logger.error("Erro na conversão PDF para imagens com PyMuPDF", error=str(e))
            raise

    def _pdf_to_images(self, file_data: bytes) -> List[np.ndarray]:
        """Converte PDF para lista de imagens usando pdf2image (precisa do Poppler)"""
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
            logger.error("Erro na conversão PDF para imagens com pdf2image", error=str(e))
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
            raise RuntimeError("Motor OCR não inicializado. Verifique os logs para erros de inicialização do PaddleOCR.")

        try:
            confidence_threshold = kwargs.get('confidence_threshold', self.config.CONFIDENCE_THRESHOLD)
            # Página de PDF é uma tabela de laudo: cada linha visual (nome, resultado,
            # referência) precisa sair junta, senão o valor pode se afastar do nome.
            from_pdf = kwargs.get('_from_pdf', False)

            result = {
                'text': '',
                'confidence': 0.0,
                'words': [],
                'lines': [],
                'processing_time': 0
            }

            basic_result = self._process_with_basic_ocr(image, confidence_threshold, group_rows=from_pdf)
            result.update(basic_result)

            result['processing_time'] = time.time() - start_time
            return result
            
        except Exception as e:
            logger.error("Erro no processamento da imagem", error=str(e))
            raise
    
    def _process_with_basic_ocr(self, image: np.ndarray, confidence_threshold: float, group_rows: bool = False) -> Dict[str, Any]:
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
            kept_boxes = []
            
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
                            kept_boxes.append((bbox, text))
                            
                            # Adicionar palavras individuais
                            words = text.split()
                            for word in words:
                                all_words.append({
                                    'text': word,
                                    'confidence': confidence,
                                    'bbox': bbox
                                })
            
            if group_rows:
                text_parts = self._boxes_to_row_lines(kept_boxes)

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
    
    @staticmethod
    def _boxes_to_row_lines(boxes: List[Any]) -> List[str]:
        """
        Junta as caixas de texto que estão na mesma linha visual, da esquerda
        para a direita, e devolve uma string por linha.

        O PaddleOCR devolve uma caixa por célula; em tabelas a ordem entre caixas
        vizinhas pode se inverter (o resultado sai antes do nome do exame).
        Duas caixas são da mesma linha quando o centro vertical de uma está a
        menos de meia altura (da menor das duas) do centro da linha.
        """
        entries = []
        for bbox, text in boxes:
            try:
                xs = [float(point[0]) for point in bbox]
                ys = [float(point[1]) for point in bbox]
            except (TypeError, ValueError, IndexError):
                continue
            if not xs or not ys:
                continue
            entries.append({
                'x': min(xs),
                'y': sum(ys) / len(ys),
                'h': max(max(ys) - min(ys), 1.0),
                'text': text,
            })

        entries.sort(key=lambda entry: entry['y'])

        rows: List[Dict[str, Any]] = []
        for entry in entries:
            row = rows[-1] if rows else None
            if row is not None and abs(entry['y'] - row['y']) <= 0.5 * min(entry['h'], row['h']):
                row['items'].append(entry)
                count = len(row['items'])
                row['y'] += (entry['y'] - row['y']) / count
                row['h'] += (entry['h'] - row['h']) / count
            else:
                rows.append({'y': entry['y'], 'h': entry['h'], 'items': [entry]})

        return [
            '  '.join(item['text'] for item in sorted(row['items'], key=lambda item: item['x']))
            for row in rows
        ]
    
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
