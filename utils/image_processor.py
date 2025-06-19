"""
Processador de imagens para melhorar qualidade do OCR
Pré-processamento especializado para exames médicos
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import io
from typing import Tuple, Optional
import structlog

logger = structlog.get_logger()

class ImageProcessor:
    """Processador de imagens para otimizar OCR de exames médicos"""
    
    def __init__(self):
        self.default_dpi = 300
        self.min_resolution = (800, 600)
        self.max_resolution = (4000, 3000)
    
    def preprocess_image(self, image_data: bytes) -> bytes:
        """
        Pré-processa imagem para melhorar qualidade do OCR
        
        Args:
            image_data: Dados da imagem em bytes
            
        Returns:
            Dados da imagem processada em bytes
        """
        try:
            # Converter bytes para PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Converter para RGB se necessário
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Aplicar pipeline de processamento
            processed_image = self._apply_processing_pipeline(image)
            
            # Converter de volta para bytes
            output_buffer = io.BytesIO()
            processed_image.save(output_buffer, format='PNG', quality=95)
            
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.error("Erro no pré-processamento de imagem", error=str(e))
            return image_data  # Retornar imagem original em caso de erro
    
    def _apply_processing_pipeline(self, image: Image.Image) -> Image.Image:
        """Aplica pipeline completo de processamento"""
        
        # 1. Redimensionar se necessário
        image = self._resize_if_needed(image)
        
        # 2. Corrigir orientação
        image = self._correct_orientation(image)
        
        # 3. Melhorar contraste
        image = self._enhance_contrast(image)
        
        # 4. Reduzir ruído
        image = self._reduce_noise(image)
        
        # 5. Binarização inteligente
        image = self._smart_binarization(image)
        
        # 6. Correção de perspectiva (se necessário)
        image = self._correct_perspective(image)
        
        return image
    
    def _resize_if_needed(self, image: Image.Image) -> Image.Image:
        """Redimensiona imagem se necessário para otimizar OCR"""
        width, height = image.size
        
        # Se muito pequena, aumentar
        if width < self.min_resolution[0] or height < self.min_resolution[1]:
            scale_factor = max(
                self.min_resolution[0] / width,
                self.min_resolution[1] / height
            )
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"Imagem redimensionada para {new_width}x{new_height}")
        
        # Se muito grande, reduzir
        elif width > self.max_resolution[0] or height > self.max_resolution[1]:
            scale_factor = min(
                self.max_resolution[0] / width,
                self.max_resolution[1] / height
            )
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"Imagem redimensionada para {new_width}x{new_height}")
        
        return image
    
    def _correct_orientation(self, image: Image.Image) -> Image.Image:
        """Corrige orientação da imagem baseada em EXIF"""
        try:
            # Verificar dados EXIF para orientação
            exif = image._getexif()
            if exif is not None:
                orientation = exif.get(274)  # Tag de orientação
                
                if orientation == 3:
                    image = image.rotate(180, expand=True)
                elif orientation == 6:
                    image = image.rotate(270, expand=True)
                elif orientation == 8:
                    image = image.rotate(90, expand=True)
                    
                logger.info(f"Orientação corrigida: {orientation}")
        except:
            pass  # Ignorar erros de EXIF
        
        return image
    
    def _enhance_contrast(self, image: Image.Image) -> Image.Image:
        """Melhora contraste da imagem"""
        try:
            # Converter para numpy para análise
            img_array = np.array(image)
            
            # Calcular histograma para determinar se precisa de melhoria
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            
            # Se histograma muito concentrado, melhorar contraste
            hist_std = np.std(hist)
            if hist_std < 1000:  # Threshold empírico
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.3)  # Aumentar contraste em 30%
                
                logger.info("Contraste melhorado")
        except Exception as e:
            logger.warning("Erro na melhoria de contraste", error=str(e))
        
        return image
    
    def _reduce_noise(self, image: Image.Image) -> Image.Image:
        """Reduz ruído da imagem"""
        try:
            # Aplicar filtro de mediana para reduzir ruído
            img_array = np.array(image)
            
            # Converter para OpenCV
            img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # Aplicar filtro bilateral para preservar bordas
            denoised = cv2.bilateralFilter(img_cv, 9, 75, 75)
            
            # Converter de volta para PIL
            denoised_rgb = cv2.cvtColor(denoised, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(denoised_rgb)
            
            logger.info("Ruído reduzido")
        except Exception as e:
            logger.warning("Erro na redução de ruído", error=str(e))
        
        return image
    
    def _smart_binarization(self, image: Image.Image) -> Image.Image:
        """Aplica binarização inteligente para melhorar legibilidade do texto"""
        try:
            # Converter para escala de cinza
            gray_image = image.convert('L')
            img_array = np.array(gray_image)
            
            # Aplicar threshold adaptativo
            binary = cv2.adaptiveThreshold(
                img_array,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,  # Tamanho do bloco
                2    # Constante subtraída da média
            )
            
            # Aplicar operações morfológicas para limpar
            kernel = np.ones((2, 2), np.uint8)
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
            
            # Converter de volta para PIL
            image = Image.fromarray(binary).convert('RGB')
            
            logger.info("Binarização aplicada")
        except Exception as e:
            logger.warning("Erro na binarização", error=str(e))
        
        return image
    
    def _correct_perspective(self, image: Image.Image) -> Image.Image:
        """Corrige perspectiva da imagem se necessário"""
        try:
            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Detectar bordas
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # Detectar linhas
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is not None and len(lines) > 4:
                # Analisar ângulos das linhas principais
                angles = []
                for line in lines[:10]:  # Analisar apenas as 10 primeiras
                    rho, theta = line[0]
                    angle = theta * 180 / np.pi
                    angles.append(angle)
                
                # Calcular ângulo médio de rotação necessário
                median_angle = np.median(angles)
                
                # Se há inclinação significativa, corrigir
                if abs(median_angle - 90) > 2:  # Threshold de 2 graus
                    rotation_angle = 90 - median_angle
                    image = image.rotate(rotation_angle, expand=True, fillcolor='white')
                    logger.info(f"Perspectiva corrigida: {rotation_angle:.2f} graus")
        
        except Exception as e:
            logger.warning("Erro na correção de perspectiva", error=str(e))
        
        return image
    
    def analyze_image_quality(self, image_data: bytes) -> dict:
        """Analisa qualidade da imagem para OCR"""
        try:
            image = Image.open(io.BytesIO(image_data))
            img_array = np.array(image)
            
            # Converter para escala de cinza
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Métricas de qualidade
            quality_metrics = {
                'resolution': image.size,
                'aspect_ratio': image.size[0] / image.size[1],
                'brightness': np.mean(gray),
                'contrast': np.std(gray),
                'sharpness': self._calculate_sharpness(gray),
                'noise_level': self._estimate_noise(gray)
            }
            
            # Calcular score geral de qualidade
            quality_score = self._calculate_quality_score(quality_metrics)
            quality_metrics['overall_score'] = quality_score
            
            return quality_metrics
            
        except Exception as e:
            logger.error("Erro na análise de qualidade", error=str(e))
            return {'error': str(e)}
    
    def _calculate_sharpness(self, gray_image: np.ndarray) -> float:
        """Calcula nitidez da imagem usando variância do Laplaciano"""
        try:
            laplacian = cv2.Laplacian(gray_image, cv2.CV_64F)
            return laplacian.var()
        except:
            return 0.0
    
    def _estimate_noise(self, gray_image: np.ndarray) -> float:
        """Estima nível de ruído na imagem"""
        try:
            # Usar filtro Gaussian para estimar ruído
            blurred = cv2.GaussianBlur(gray_image, (5, 5), 0)
            noise = gray_image.astype(float) - blurred.astype(float)
            return np.std(noise)
        except:
            return 0.0
    
    def _calculate_quality_score(self, metrics: dict) -> float:
        """Calcula score geral de qualidade (0-100)"""
        try:
            score = 50  # Score base
            
            # Penalizar resolução muito baixa
            width, height = metrics['resolution']
            if width < 800 or height < 600:
                score -= 20
            elif width > 1200 and height > 900:
                score += 10
            
            # Penalizar contraste muito baixo
            if metrics['contrast'] < 30:
                score -= 15
            elif metrics['contrast'] > 50:
                score += 10
            
            # Penalizar nitidez muito baixa
            if metrics['sharpness'] < 100:
                score -= 15
            elif metrics['sharpness'] > 500:
                score += 10
            
            # Penalizar muito ruído
            if metrics['noise_level'] > 20:
                score -= 10
            
            # Penalizar brilho extremo
            brightness = metrics['brightness']
            if brightness < 50 or brightness > 200:
                score -= 10
            
            return max(0, min(100, score))
            
        except:
            return 50  # Score neutro em caso de erro
    
    def create_thumbnail(self, image_data: bytes, size: Tuple[int, int] = (200, 200)) -> bytes:
        """Cria thumbnail da imagem"""
        try:
            image = Image.open(io.BytesIO(image_data))
            image.thumbnail(size, Image.Resampling.LANCZOS)
            
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='JPEG', quality=85)
            
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.error("Erro ao criar thumbnail", error=str(e))
            return image_data
    
    def extract_text_regions(self, image_data: bytes) -> list:
        """Detecta regiões de texto na imagem"""
        try:
            image = Image.open(io.BytesIO(image_data))
            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Usar MSER (Maximally Stable Extremal Regions) para detectar texto
            mser = cv2.MSER_create()
            regions, _ = mser.detectRegions(gray)
            
            # Converter regiões para bounding boxes
            text_regions = []
            for region in regions:
                x, y, w, h = cv2.boundingRect(region.reshape(-1, 1, 2))
                
                # Filtrar regiões muito pequenas ou muito grandes
                if 10 < w < 500 and 5 < h < 100:
                    text_regions.append({
                        'x': int(x),
                        'y': int(y),
                        'width': int(w),
                        'height': int(h),
                        'area': int(w * h)
                    })
            
            # Ordenar por posição (top-left primeiro)
            text_regions.sort(key=lambda r: (r['y'], r['x']))
            
            return text_regions
            
        except Exception as e:
            logger.error("Erro na detecção de regiões de texto", error=str(e))
            return []
