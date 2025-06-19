"""
Parser especializado para extração de parâmetros médicos
Identifica automaticamente qualquer tipo de exame médico
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import structlog
from unidecode import unidecode

import config as config_module # Alterado para importar o módulo inteiro

logger = structlog.get_logger()
# config = get_config() # Esta linha não é mais necessária

@dataclass
class MedicalParameter:
    """Representa um parâmetro médico extraído"""
    name: str
    value: float
    unit: str
    reference_range: Optional[Dict[str, float]]
    status: str  # 'normal', 'high', 'low', 'critical'
    category: str
    confidence: float
    original_text: str
    position: Optional[Tuple[int, int]] = None

@dataclass
class PatientInfo:
    """Informações do paciente"""
    name: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    id: Optional[str] = None
    birth_date: Optional[str] = None

@dataclass
class LaboratoryInfo:
    """Informações do laboratório"""
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    responsible: Optional[str] = None
    date: Optional[str] = None

class MedicalParameterParser:
    """Parser avançado para parâmetros médicos"""
    
    def __init__(self):
        self.config = config_module.config # Usar a instância importada
        self._compile_patterns()
        self._load_medical_knowledge()
    
    def _compile_patterns(self):
        """Compila padrões regex para melhor performance"""
        self.compiled_patterns = {}
        
        # Compilar padrões de parâmetros
        for param_name, patterns in self.config.PARAMETER_PATTERNS.items():
            self.compiled_patterns[param_name] = [
                re.compile(pattern, re.IGNORECASE | re.UNICODE)
                for pattern in patterns
            ]
        
        # Padrões gerais para qualquer parâmetro
        self.general_patterns = [
            # Formato: Nome: Valor Unidade (Referência)
            re.compile(r'([A-Za-zÀ-ÿ\s]+):\s*(\d+[,.]?\d*)\s*([A-Za-z\/μ³%]+)?\s*\(([^)]+)\)', re.IGNORECASE),
            # Formato: Nome Valor Unidade Referência
            re.compile(r'([A-Za-zÀ-ÿ\s]+)\s+(\d+[,.]?\d*)\s+([A-Za-z\/μ³%]+)\s+([0-9,.\-\s]+)', re.IGNORECASE),
            # Formato simples: Nome: Valor Unidade
            re.compile(r'([A-Za-zÀ-ÿ\s]+):\s*(\d+[,.]?\d*)\s*([A-Za-z\/μ³%]+)?', re.IGNORECASE),
            # Formato tabular: Nome | Valor | Unidade | Referência
            re.compile(r'([A-Za-zÀ-ÿ\s]+)\s*\|\s*(\d+[,.]?\d*)\s*\|\s*([A-Za-z\/μ³%]+)?\s*\|\s*([^|]+)', re.IGNORECASE)
        ]
        
        # Padrões para informações do paciente
        self.patient_patterns = {
            'name': [
                re.compile(r'(?:paciente|nome)\s*:?\s*([A-Za-zÀ-ÿ\s]+)', re.IGNORECASE),
                re.compile(r'^([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+)+)$', re.MULTILINE)
            ],
            'age': [
                re.compile(r'(?:idade|anos?)\s*:?\s*(\d{1,3})', re.IGNORECASE),
                re.compile(r'(\d{1,3})\s*anos?', re.IGNORECASE)
            ],
            'gender': [
                re.compile(r'(?:sexo|gênero)\s*:?\s*(masculino|feminino|m|f)', re.IGNORECASE)
            ],
            'id': [
                re.compile(r'(?:rg|cpf|id|registro)\s*:?\s*([0-9.\-/]+)', re.IGNORECASE)
            ]
        }
        
        # Padrões para laboratório
        self.lab_patterns = {
            'name': [
                re.compile(r'(?:laborat[óo]rio|lab\.?)\s*:?\s*([A-Za-zÀ-ÿ\s&]+)', re.IGNORECASE)
            ],
            'responsible': [
                re.compile(r'(?:m[ée]dico|dr\.?|dra\.?|respons[áa]vel)\s*:?\s*([A-Za-zÀ-ÿ\s\.]+)', re.IGNORECASE)
            ],
            'date': [
                re.compile(r'(?:data|realizado em|coletado em)\s*:?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})', re.IGNORECASE)
            ]
        }
    
    def _load_medical_knowledge(self):
        """Carrega base de conhecimento médico expandida"""
        # Expandir categorias com sinônimos e variações
        self.expanded_categories = {}
        
        for category, parameters in self.config.MEDICAL_CATEGORIES.items():
            expanded_params = set(parameters)
            
            # Adicionar variações e sinônimos
            for param in parameters:
                expanded_params.update(self._get_parameter_variations(param))
            
            self.expanded_categories[category] = list(expanded_params)
        
        # Criar mapeamento reverso: parâmetro -> categoria
        self.param_to_category = {}
        for category, parameters in self.expanded_categories.items():
            for param in parameters:
                self.param_to_category[param.lower()] = category
    
    def _get_parameter_variations(self, param: str) -> List[str]:
        """Gera variações e sinônimos de um parâmetro"""
        variations = [param]
        
        # Variações comuns
        param_lower = param.lower()
        
        # Hemoglobina
        if 'hemoglobina' in param_lower:
            variations.extend(['hb', 'hemoglobina', 'hemoglobin'])
        
        # Hematócrito
        elif 'hematócrito' in param_lower:
            variations.extend(['ht', 'hct', 'hematocrito'])
        
        # Leucócitos
        elif 'leucócitos' in param_lower:
            variations.extend(['leucocitos', 'glóbulos brancos', 'globulos brancos', 'wbc'])
        
        # Plaquetas
        elif 'plaquetas' in param_lower:
            variations.extend(['plt', 'platelets'])
        
        # Glicose
        elif 'glicose' in param_lower:
            variations.extend(['glicemia', 'glucose', 'açúcar'])
        
        # Colesterol
        elif 'colesterol' in param_lower:
            variations.extend(['col', 'cholesterol'])
        
        # Triglicerídeos
        elif 'triglicerídeos' in param_lower:
            variations.extend(['triglicerides', 'tg', 'triglycerides'])
        
        # Creatinina
        elif 'creatinina' in param_lower:
            variations.extend(['creat', 'creatinine'])
        
        # Ureia
        elif 'ureia' in param_lower:
            variations.extend(['uréia', 'bun', 'urea'])
        
        # TSH
        elif 'tsh' in param_lower:
            variations.extend(['hormônio estimulante da tireoide'])
        
        # Adicionar versões sem acentos
        variations.extend([unidecode(v) for v in variations])
        
        return list(set(variations))
    
    def parse_medical_text(self, text: str, confidence_threshold: float = 0.7) -> Dict[str, Any]:
        """
        Analisa texto médico e extrai parâmetros estruturados
        
        Args:
            text: Texto do exame médico
            confidence_threshold: Threshold mínimo de confiança
            
        Returns:
            Dados estruturados do exame
        """
        try:
            # Normalizar texto
            normalized_text = self._normalize_text(text)
            
            # Extrair informações básicas
            patient_info = self._extract_patient_info(normalized_text)
            lab_info = self._extract_laboratory_info(normalized_text)
            exam_type = self._identify_exam_type(normalized_text)
            
            # Extrair parâmetros
            parameters = self._extract_all_parameters(normalized_text, confidence_threshold)
            
            # Classificar parâmetros por categoria
            categorized_params = self._categorize_parameters(parameters)
            
            # Calcular estatísticas
            stats = self._calculate_statistics(parameters)
            
            return {
                'patient': patient_info.__dict__ if patient_info else None,
                'laboratory': lab_info.__dict__ if lab_info else None,
                'exam_type': exam_type,
                'parameters': [p.__dict__ for p in parameters],
                'categories': categorized_params,
                'statistics': stats,
                'total_parameters': len(parameters),
                'confidence_avg': sum(p.confidence for p in parameters) / len(parameters) if parameters else 0
            }
            
        except Exception as e:
            logger.error("Erro no parsing médico", error=str(e))
            return {'error': str(e)}
    
    def _normalize_text(self, text: str) -> str:
        """Normaliza texto para melhor processamento"""
        # Remover caracteres especiais desnecessários
        text = re.sub(r'[^\w\s:.,()/-]', ' ', text)
        
        # Normalizar espaços
        text = re.sub(r'\s+', ' ', text)
        
        # Normalizar pontuação
        text = text.replace(',', '.')  # Vírgulas decimais para pontos
        
        return text.strip()
    
    def _extract_patient_info(self, text: str) -> Optional[PatientInfo]:
        """Extrai informações do paciente"""
        patient = PatientInfo()
        
        for field, patterns in self.patient_patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    value = match.group(1).strip()
                    
                    # Validações específicas
                    if field == 'name' and len(value) > 5 and len(value.split()) >= 2:
                        patient.name = value.title()
                    elif field == 'age' and value.isdigit() and 0 < int(value) < 120:
                        patient.age = value
                    elif field == 'gender':
                        gender_map = {'m': 'masculino', 'f': 'feminino'}
                        patient.gender = gender_map.get(value.lower(), value.lower())
                    elif field == 'id':
                        patient.id = value
                    
                    break
        
        # Retornar apenas se pelo menos um campo foi encontrado
        if any([patient.name, patient.age, patient.gender, patient.id]):
            return patient
        
        return None
    
    def _extract_laboratory_info(self, text: str) -> Optional[LaboratoryInfo]:
        """Extrai informações do laboratório"""
        lab = LaboratoryInfo()
        
        for field, patterns in self.lab_patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    value = match.group(1).strip()
                    
                    if field == 'name' and len(value) > 3:
                        lab.name = value.title()
                    elif field == 'responsible' and len(value) > 5:
                        lab.responsible = value.title()
                    elif field == 'date':
                        lab.date = value
                    
                    break
        
        if any([lab.name, lab.responsible, lab.date]):
            return lab
        
        return None
    
    def _identify_exam_type(self, text: str) -> str:
        """Identifica tipo de exame baseado no conteúdo"""
        text_lower = text.lower()
        
        # Padrões para tipos de exame
        exam_patterns = {
            'hemograma': ['hemograma', 'sangue completo', 'hematologia'],
            'bioquímica': ['bioquímica', 'bioquimico', 'glicose', 'colesterol'],
            'hormonal': ['hormonal', 'tsh', 't3', 't4', 'cortisol'],
            'urina': ['urina', 'eas', 'urinálise'],
            'lipidograma': ['lipidograma', 'perfil lipídico', 'colesterol'],
            'função_renal': ['função renal', 'creatinina', 'ureia'],
            'função_hepática': ['função hepática', 'alt', 'ast', 'bilirrubina'],
            'eletrólitos': ['eletrólitos', 'sódio', 'potássio'],
            'vitaminas': ['vitamina', 'b12', 'ácido fólico']
        }
        
        for exam_type, keywords in exam_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                return exam_type
        
        return 'geral'
    
    def _extract_all_parameters(self, text: str, confidence_threshold: float) -> List[MedicalParameter]:
        """Extrai todos os parâmetros médicos do texto"""
        parameters = []
        
        # Primeiro, tentar padrões específicos conhecidos
        for param_name, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.finditer(text)
                for match in matches:
                    param = self._create_parameter_from_match(param_name, match, confidence_threshold + 0.1)
                    if param and param.confidence >= confidence_threshold:
                        parameters.append(param)
        
        # Depois, usar padrões gerais para capturar outros parâmetros
        for pattern in self.general_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                param = self._create_parameter_from_general_match(match, confidence_threshold)
                if param and param.confidence >= confidence_threshold:
                    # Verificar se já não foi capturado
                    if not any(p.name.lower() == param.name.lower() for p in parameters):
                        parameters.append(param)
        
        return parameters
    
    def _create_parameter_from_match(self, param_name: str, match: re.Match, base_confidence: float) -> Optional[MedicalParameter]:
        """Cria parâmetro a partir de match de padrão específico"""
        try:
            value_str = match.group(1).replace(',', '.')
            value = float(value_str)
            
            # Obter unidade e referência se disponível
            unit = self._get_default_unit(param_name)
            reference_range = self._get_reference_range(param_name)
            category = self._get_parameter_category(param_name)
            
            # Determinar status
            status = self._determine_status(param_name, value, reference_range)
            
            return MedicalParameter(
                name=param_name.replace('_', ' ').title(),
                value=value,
                unit=unit,
                reference_range=reference_range,
                status=status,
                category=category,
                confidence=base_confidence,
                original_text=match.group(0),
                position=(match.start(), match.end())
            )
            
        except (ValueError, IndexError):
            return None
    
    def _create_parameter_from_general_match(self, match: re.Match, base_confidence: float) -> Optional[MedicalParameter]:
        """Cria parâmetro a partir de match de padrão geral"""
        try:
            groups = match.groups()
            
            if len(groups) < 2:
                return None
            
            name = groups[0].strip()
            value_str = groups[1].replace(',', '.')
            value = float(value_str)
            
            # Filtrar nomes muito curtos ou inválidos
            if len(name) < 3 or not re.match(r'^[A-Za-zÀ-ÿ\s]+$', name):
                return None
            
            # Obter unidade
            unit = groups[2].strip() if len(groups) > 2 and groups[2] else ''
            
            # Tentar extrair referência
            reference_range = None
            if len(groups) > 3 and groups[3]:
                reference_range = self._parse_reference_range(groups[3])
            
            # Determinar categoria
            category = self._get_parameter_category(name)
            
            # Determinar status
            status = self._determine_status(name, value, reference_range)
            
            # Ajustar confiança baseada na qualidade da extração
            confidence = base_confidence
            if unit:
                confidence += 0.1
            if reference_range:
                confidence += 0.1
            if category != 'outros':
                confidence += 0.1
            
            return MedicalParameter(
                name=name.title(),
                value=value,
                unit=unit,
                reference_range=reference_range,
                status=status,
                category=category,
                confidence=min(confidence, 0.95),
                original_text=match.group(0),
                position=(match.start(), match.end())
            )
            
        except (ValueError, IndexError):
            return None
    
    def _get_default_unit(self, param_name: str) -> str:
        """Retorna unidade padrão para parâmetro conhecido"""
        unit_map = {
            'hemoglobina': 'g/dL',
            'hematócrito': '%',
            'leucócitos': '/mm³',
            'plaquetas': '/mm³',
            'glicose': 'mg/dL',
            'colesterol_total': 'mg/dL',
            'hdl': 'mg/dL',
            'ldl': 'mg/dL',
            'triglicerídeos': 'mg/dL',
            'creatinina': 'mg/dL',
            'ureia': 'mg/dL',
            'tsh': 'mUI/L'
        }
        return unit_map.get(param_name, '')
    
    def _get_reference_range(self, param_name: str) -> Optional[Dict[str, float]]:
        """Retorna faixa de referência para parâmetro conhecido"""
        ranges = self.config.REFERENCE_RANGES.get(param_name)
        if ranges:
            return {
                'min': ranges['min'],
                'max': ranges['max']
            }
        return None
    
    def _parse_reference_range(self, ref_text: str) -> Optional[Dict[str, float]]:
        """Analisa texto de referência para extrair valores min/max"""
        try:
            # Padrões para faixas de referência
            patterns = [
                r'(\d+[,.]?\d*)\s*[-–]\s*(\d+[,.]?\d*)',  # min-max
                r'(\d+[,.]?\d*)\s*a\s*(\d+[,.]?\d*)',     # min a max
                r'até\s*(\d+[,.]?\d*)',                    # até max
                r'acima\s*de\s*(\d+[,.]?\d*)',            # acima de min
            ]
            
            for pattern in patterns:
                match = re.search(pattern, ref_text)
                if match:
                    if len(match.groups()) == 2:
                        min_val = float(match.group(1).replace(',', '.'))
                        max_val = float(match.group(2).replace(',', '.'))
                        return {'min': min_val, 'max': max_val}
                    elif 'até' in pattern:
                        max_val = float(match.group(1).replace(',', '.'))
                        return {'min': 0, 'max': max_val}
                    elif 'acima' in pattern:
                        min_val = float(match.group(1).replace(',', '.'))
                        return {'min': min_val, 'max': 999999}
            
        except (ValueError, AttributeError):
            pass
        
        return None
    
    def _get_parameter_category(self, param_name: str) -> str:
        """Determina categoria do parâmetro"""
        param_lower = param_name.lower()
        
        # Buscar em categorias expandidas
        for category, parameters in self.expanded_categories.items():
            if any(p.lower() in param_lower or param_lower in p.lower() for p in parameters):
                return category
        
        return 'outros'
    
    def _determine_status(self, param_name: str, value: float, reference_range: Optional[Dict[str, float]]) -> str:
        """Determina status do parâmetro (normal, alto, baixo, crítico)"""
        if not reference_range:
            return 'indeterminado'
        
        min_val = reference_range.get('min', 0)
        max_val = reference_range.get('max', float('inf'))
        
        if value < min_val:
            # Verificar se é criticamente baixo
            if min_val > 0 and value < min_val * 0.7:
                return 'crítico'
            return 'baixo'
        elif value > max_val:
            # Verificar se é criticamente alto
            if value > max_val * 1.3:
                return 'crítico'
            return 'alto'
        else:
            return 'normal'
    
    def _categorize_parameters(self, parameters: List[MedicalParameter]) -> Dict[str, List[Dict]]:
        """Agrupa parâmetros por categoria"""
        categorized = {}
        
        for param in parameters:
            category = param.category
            if category not in categorized:
                categorized[category] = []
            
            categorized[category].append({
                'name': param.name,
                'value': param.value,
                'unit': param.unit,
                'status': param.status,
                'confidence': param.confidence
            })
        
        return categorized
    
    def _calculate_statistics(self, parameters: List[MedicalParameter]) -> Dict[str, Any]:
        """Calcula estatísticas dos parâmetros extraídos"""
        if not parameters:
            return {}
        
        total = len(parameters)
        by_status = {}
        by_category = {}
        
        for param in parameters:
            # Contar por status
            status = param.status
            by_status[status] = by_status.get(status, 0) + 1
            
            # Contar por categoria
            category = param.category
            by_category[category] = by_category.get(category, 0) + 1
        
        return {
            'total_parameters': total,
            'by_status': by_status,
            'by_category': by_category,
            'normal_percentage': (by_status.get('normal', 0) / total) * 100,
            'altered_percentage': ((by_status.get('alto', 0) + by_status.get('baixo', 0)) / total) * 100,
            'critical_percentage': (by_status.get('crítico', 0) / total) * 100
        }
    
    def validate_parameter(self, param: MedicalParameter) -> bool:
        """Valida se um parâmetro extraído é válido"""
        # Verificações básicas
        if not param.name or len(param.name) < 3:
            return False
        
        if param.value < 0:
            return False
        
        if param.confidence < 0.5:
            return False
        
        # Verificações específicas por categoria
        if param.category == 'hematologia':
            # Valores muito extremos são suspeitos
            if param.name.lower() == 'hemoglobina' and (param.value < 1 or param.value > 25):
                return False
        
        return True
    
    def get_medical_insights(self, parameters: List[MedicalParameter]) -> List[str]:
        """Gera insights médicos baseados nos parâmetros"""
        insights = []
        
        # Analisar parâmetros alterados
        altered_params = [p for p in parameters if p.status in ['alto', 'baixo', 'crítico']]
        
        if not altered_params:
            insights.append("Todos os parâmetros analisados estão dentro da normalidade.")
            return insights
        
        # Insights por categoria
        categories_with_issues = {}
        for param in altered_params:
            category = param.category
            if category not in categories_with_issues:
                categories_with_issues[category] = []
            categories_with_issues[category].append(param)
        
        for category, params in categories_with_issues.items():
            if category == 'hematologia':
                insights.append(f"Alterações hematológicas detectadas em {len(params)} parâmetro(s).")
            elif category == 'bioquímica':
                insights.append(f"Alterações bioquímicas detectadas em {len(params)} parâmetro(s).")
            elif category == 'hormonal':
                insights.append(f"Alterações hormonais detectadas em {len(params)} parâmetro(s).")
        
        # Parâmetros críticos
        critical_params = [p for p in parameters if p.status == 'crítico']
        if critical_params:
            insights.append(f"ATENÇÃO: {len(critical_params)} parâmetro(s) em nível crítico.")
        
        return insights
