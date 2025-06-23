"""
Parser especializado para extração de parâmetros médicos
Versão otimizada para máxima eficiência de extração
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import structlog
from unidecode import unidecode

import config as config_module

logger = structlog.get_logger()

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
    """Parser otimizado para parâmetros médicos"""
    
    def __init__(self):
        self.config = config_module.config
        self._compile_patterns()
        self._load_medical_knowledge()

    def _compile_patterns(self):
        """Compila padrões regex otimizados para extração máxima"""
        
        # Padrões MUITO mais agressivos para capturar qualquer parâmetro
        self.general_patterns = [
            # Padrão 1: Nome: Valor Unidade (mais comum em exames)
            re.compile(
                r'([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\.\(\)\-]{2,40}?)\s*:?\s*'
                r'(\d+[,.]?\d*)\s*'
                r'(g/dL|mg/dL|%|/mm³|/mm3|fL|pg|U/L|mEq/L|ng/mL|pg/mL|mcg/dL|mUI/L|microUI/mL|ng/dL|mil/mm³|k/uL)?',
                re.IGNORECASE | re.UNICODE
            ),
            
            # Padrão 2: Linha com nome e valor separados por espaços
            re.compile(
                r'^([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\.\(\)\-]{2,40}?)\s+'
                r'(\d+[,.]?\d*)\s*'
                r'(g/dL|mg/dL|%|/mm³|/mm3|fL|pg|U/L|mEq/L|ng/mL|pg/mL|mcg/dL|mUI/L|microUI/mL|ng/dL|mil/mm³|k/uL)?',
                re.IGNORECASE | re.UNICODE | re.MULTILINE
            ),
            
            # Padrão 3: Capturar valores em formato tabular
            re.compile(
                r'([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\.\(\)\-]{2,40}?)\s*'
                r'(\d+[,.]?\d*)\s*'
                r'(g/dL|mg/dL|%|/mm³|/mm3|fL|pg|U/L|mEq/L|ng/mL|pg/mL|mcg/dL|mUI/L|microUI/mL|ng/dL|mil/mm³|k/uL)?\s*'
                r'([\d\s,.\-aAatéTO<>]{3,})?',
                re.IGNORECASE | re.UNICODE
            ),
            
            # Padrão 4: Para hemácias em formato específico (como "5,55")
            re.compile(
                r'(Hem[aá]cias?|Hemaciag|Eritr[óo]citos?)\s*:?\s*'
                r'(\d+[,.]?\d*)\s*'
                r'(milhões/mm³|mil/mm³|/mm³|x10\^6/uL)?',
                re.IGNORECASE | re.UNICODE
            ),
            
            # Padrão 5: Capturar qualquer linha com número e possível unidade
            re.compile(
                r'([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]{2,30}?)\s+'
                r'(\d+[,.]?\d*)\s*'
                r'([a-zA-Z/%³³]{1,15})?',
                re.IGNORECASE | re.UNICODE
            )
        ]
        
        # Padrões para informações do paciente (simplificados)
        self.patient_patterns = {
            'name': [
                re.compile(r'Nome[:\s]*([A-Za-zÀ-ÿ\s]{5,50})', re.IGNORECASE),
                re.compile(r'Paciente[:\s]*([A-Za-zÀ-ÿ\s]{5,50})', re.IGNORECASE)
            ],
            'age': [
                re.compile(r'Idade[:\s]*(\d{1,3})', re.IGNORECASE),
                re.compile(r'(\d{1,3})\s*anos?', re.IGNORECASE)
            ],
            'gender': [
                re.compile(r'Sexo[:\s]*(Masculino|Feminino|M|F)', re.IGNORECASE)
            ]
        }

    def _load_medical_knowledge(self):
        """Carrega mapeamento de parâmetros conhecidos"""
        
        # Mapeamento mais abrangente de nomes para parâmetros canônicos
        self.parameter_mapping = {
            # Hemograma
            'hemacias': 'Hemácias',
            'hemaciag': 'Hemácias',
            'eritrocitos': 'Hemácias',
            'hemoglobina': 'Hemoglobina',
            'hb': 'Hemoglobina',
            'hematocrito': 'Hematócrito',
            'ht': 'Hematócrito',
            'hct': 'Hematócrito',
            'vcm': 'VCM',
            'vol corp medio': 'VCM',
            'hcm': 'HCM',
            'hem corp media': 'HCM',
            'chcm': 'CHCM',
            'c h corp media': 'CHCM',
            'rdw': 'RDW',
            'r d w': 'RDW',
            'leucocitos': 'Leucócitos',
            'globulos brancos': 'Leucócitos',
            'neutrofilos': 'Neutrófilos',
            'segmentados': 'Segmentados',
            'eosinofilos': 'Eosinófilos',
            'basofilos': 'Basófilos',
            'linfocitos': 'Linfócitos',
            'linfocitos tipicos': 'Linfócitos',
            'monocitos': 'Monócitos',
            'monoci tos': 'Monócitos',
            'plaquetas': 'Plaquetas',
            'vpm': 'VPM',
            'volume plaquetario medio': 'VPM',
            
            # Bioquímica
            'glicose': 'Glicose',
            'glicemia': 'Glicose',
            'colesterol total': 'Colesterol Total',
            'hdl': 'HDL',
            'ldl': 'LDL',
            'vldl': 'VLDL',
            'triglicerides': 'Triglicerídeos',
            'triglicerideos': 'Triglicerídeos',
            'creatinina': 'Creatinina',
            'ureia': 'Ureia',
            'acido urico': 'Ácido Úrico',
            
            # Enzimas
            'tgo': 'TGO',
            'ast': 'TGO',
            'tgp': 'TGP',
            'alt': 'TGP',
            'ggt': 'GGT',
            'fosfatase alcalina': 'Fosfatase Alcalina',
            
            # Hormônios
            'tsh': 'TSH',
            't4 livre': 'T4 Livre',
            't3': 'T3',
            
            # Eletrólitos
            'sodio': 'Sódio',
            'potassio': 'Potássio',
            'magnesio': 'Magnésio',
            'ferro': 'Ferro',
            'ferritina': 'Ferritina'
        }
        
        # Unidades padrão por parâmetro
        self.default_units = {
            'Hemácias': 'milhões/mm³',
            'Hemoglobina': 'g/dL',
            'Hematócrito': '%',
            'VCM': 'fL',
            'HCM': 'pg',
            'CHCM': '%',
            'RDW': '%',
            'Leucócitos': '/mm³',
            'Neutrófilos': '/mm³',
            'Segmentados': '/mm³',
            'Eosinófilos': '/mm³',
            'Basófilos': '/mm³',
            'Linfócitos': '/mm³',
            'Monócitos': '/mm³',
            'Plaquetas': '/mm³',
            'VPM': 'fL',
            'Glicose': 'mg/dL',
            'Colesterol Total': 'mg/dL',
            'HDL': 'mg/dL',
            'LDL': 'mg/dL',
            'VLDL': 'mg/dL',
            'Triglicerídeos': 'mg/dL',
            'Creatinina': 'mg/dL',
            'Ureia': 'mg/dL',
            'Ácido Úrico': 'mg/dL',
            'TGO': 'U/L',
            'TGP': 'U/L',
            'GGT': 'U/L',
            'Fosfatase Alcalina': 'U/L',
            'TSH': 'mUI/L',
            'T4 Livre': 'ng/dL',
            'T3': 'ng/dL',
            'Sódio': 'mEq/L',
            'Potássio': 'mEq/L',
            'Magnésio': 'mg/dL',
            'Ferro': 'mcg/dL',
            'Ferritina': 'ng/mL'
        }
        
        # Categorias
        self.categories = {
            'Hemácias': 'hematologia',
            'Hemoglobina': 'hematologia',
            'Hematócrito': 'hematologia',
            'VCM': 'hematologia',
            'HCM': 'hematologia',
            'CHCM': 'hematologia',
            'RDW': 'hematologia',
            'Leucócitos': 'hematologia',
            'Neutrófilos': 'hematologia',
            'Segmentados': 'hematologia',
            'Eosinófilos': 'hematologia',
            'Basófilos': 'hematologia',
            'Linfócitos': 'hematologia',
            'Monócitos': 'hematologia',
            'Plaquetas': 'hematologia',
            'VPM': 'hematologia',
            'Glicose': 'bioquimica',
            'Colesterol Total': 'bioquimica',
            'HDL': 'bioquimica',
            'LDL': 'bioquimica',
            'VLDL': 'bioquimica',
            'Triglicerídeos': 'bioquimica',
            'Creatinina': 'bioquimica',
            'Ureia': 'bioquimica',
            'Ácido Úrico': 'bioquimica',
            'TGO': 'enzimas',
            'TGP': 'enzimas',
            'GGT': 'enzimas',
            'Fosfatase Alcalina': 'enzimas',
            'TSH': 'hormonal',
            'T4 Livre': 'hormonal',
            'T3': 'hormonal',
            'Sódio': 'eletrolitos',
            'Potássio': 'eletrolitos',
            'Magnésio': 'eletrolitos',
            'Ferro': 'eletrolitos',
            'Ferritina': 'eletrolitos'
        }

    def parse_medical_text(self, text: str, confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """Analisa texto médico com foco em máxima extração"""
        try:
            # Normalizar texto básico
            text = self._basic_normalize(text)
            
            # Extrair informações básicas
            patient_info = self._extract_patient_info(text)
            lab_info = self._extract_laboratory_info(text)
            
            # Extrair TODOS os parâmetros possíveis
            parameters = self._extract_all_parameters(text, confidence_threshold)
            
            # Remover duplicatas óbvias
            parameters = self._remove_obvious_duplicates(parameters)
            
            # Categorizar
            categorized_params = self._categorize_parameters(parameters)
            stats = self._calculate_statistics(parameters)
            
            return {
                'patient': patient_info.__dict__ if patient_info else None,
                'laboratory': lab_info.__dict__ if lab_info else None,
                'parameters': [p.__dict__ for p in parameters],
                'categories': categorized_params,
                'statistics': stats,
                'total_parameters': len(parameters),
                'confidence_avg': sum(p.confidence for p in parameters) / len(parameters) if parameters else 0.0
            }
            
        except Exception as e:
            logger.error("Erro no parsing médico", error=str(e), exc_info=True)
            return {'error': str(e)}

    def _basic_normalize(self, text: str) -> str:
        """Normalização básica do texto"""
        # Substituir vírgulas por pontos em números
        text = re.sub(r'(\d+),(\d+)', r'\1.\2', text)
        
        # Normalizar espaços
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def _extract_all_parameters(self, text: str, confidence_threshold: float) -> List[MedicalParameter]:
        """Extrai TODOS os parâmetros possíveis do texto"""
        parameters = []
        processed_positions = set()
        
        # Dividir texto em linhas para análise linha por linha
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if len(line) < 3:
                continue
            
            # Tentar cada padrão na linha
            for pattern_num, pattern in enumerate(self.general_patterns):
                matches = list(pattern.finditer(line))
                
                for match in matches:
                    # Verificar se já processamos esta posição
                    pos_key = (line_num, match.start(), match.end())
                    if pos_key in processed_positions:
                        continue
                    
                    param = self._create_parameter_from_match(match, line, line_num, pattern_num)
                    if param and param.confidence >= confidence_threshold:
                        # Validação mínima
                        if self._basic_validate_parameter(param):
                            parameters.append(param)
                            processed_positions.add(pos_key)
        
        return parameters

    def _create_parameter_from_match(self, match: re.Match, line: str, line_num: int, pattern_num: int) -> Optional[MedicalParameter]:
        """Cria parâmetro a partir de match com validação mínima"""
        try:
            groups = match.groups()
            
            if len(groups) < 2:
                return None
            
            raw_name = groups[0].strip()
            value_str = groups[1].strip()
            unit = groups[2].strip() if len(groups) > 2 and groups[2] else ''
            
            # Limpar nome básico
            name = self._clean_parameter_name(raw_name)
            if not name or len(name) < 2:
                return None
            
            # Converter valor
            try:
                value = float(value_str.replace(',', '.'))
            except ValueError:
                return None
            
            # Validação de valor básica
            if value < 0 or value > 999999:
                return None
            
            # Normalizar nome para canônico
            canonical_name = self._get_canonical_name(name)
            
            # Obter unidade padrão se não encontrada
            if not unit:
                unit = self.default_units.get(canonical_name, '')
            
            # Obter categoria
            category = self.categories.get(canonical_name, 'outros')
            
            # Obter referência
            reference_range = self._get_reference_range(canonical_name)
            
            # Determinar status
            status = self._determine_status(canonical_name, value, reference_range)
            
            # Calcular confiança baseada em vários fatores
            confidence = self._calculate_confidence(canonical_name, name, unit, pattern_num, value)
            
            return MedicalParameter(
                name=canonical_name,
                value=value,
                unit=unit,
                reference_range=reference_range,
                status=status,
                category=category,
                confidence=confidence,
                original_text=match.group(0),
                position=(match.start(), match.end())
            )
            
        except Exception as e:
            logger.debug(f"Erro ao criar parâmetro: {e}")
            return None

    def _clean_parameter_name(self, raw_name: str) -> str:
        """Limpeza básica do nome do parâmetro"""
        # Remover pontuação desnecessária
        name = re.sub(r'[:\-\.]$', '', raw_name).strip()
        
        # Remover prefixos comuns
        name = re.sub(r'^(Material|Método|Resultado)\s*:?\s*', '', name, flags=re.IGNORECASE)
        
        # Normalizar espaços
        name = re.sub(r'\s+', ' ', name)
        
        return name.strip()

    def _get_canonical_name(self, name: str) -> str:
        """Converte nome para forma canônica"""
        name_lower = unidecode(name.lower())
        
        # Buscar mapeamento direto
        for key, canonical in self.parameter_mapping.items():
            if key in name_lower or name_lower in key:
                return canonical
        
        # Se não encontrou, retornar nome limpo capitalizado
        return name.title()

    def _calculate_confidence(self, canonical_name: str, original_name: str, unit: str, pattern_num: int, value: float) -> float:
        """Calcula confiança do parâmetro extraído"""
        confidence = 0.6  # Base
        
        # Boost se é parâmetro conhecido
        if canonical_name in self.parameter_mapping.values():
            confidence += 0.2
        
        # Boost se tem unidade
        if unit:
            confidence += 0.1
        
        # Boost baseado no padrão usado (padrões mais específicos = maior confiança)
        if pattern_num <= 1:  # Padrões mais específicos
            confidence += 0.1
        
        # Boost se o valor está em faixa razoável para parâmetros conhecidos
        if self._value_in_reasonable_range(canonical_name, value):
            confidence += 0.1
        
        return min(confidence, 0.95)

    def _value_in_reasonable_range(self, param_name: str, value: float) -> bool:
        """Verifica se valor está em faixa razoável para o parâmetro"""
        reasonable_ranges = {
            'Hemácias': (3.0, 7.0),
            'Hemoglobina': (8.0, 20.0),
            'Hematócrito': (20.0, 60.0),
            'Leucócitos': (1000, 50000),
            'Plaquetas': (50000, 800000),
            'Glicose': (50, 500),
            'Colesterol Total': (100, 400),
            'Creatinina': (0.3, 5.0),
            'TSH': (0.1, 20.0)
        }
        
        if param_name in reasonable_ranges:
            min_val, max_val = reasonable_ranges[param_name]
            return min_val <= value <= max_val
        
        return True  # Se não conhecemos, assumimos que está ok

    def _basic_validate_parameter(self, param: MedicalParameter) -> bool:
        """Validação básica do parâmetro"""
        # Nome muito curto
        if len(param.name) < 2:
            return False
        
        # Valor negativo
        if param.value < 0:
            return False
        
        # Nome que é claramente lixo
        garbage_names = ['data', 'pagina', 'codigo', 'cpf', 'dr', 'dra', 'telefone', 'endereco']
        if any(garbage in param.name.lower() for garbage in garbage_names):
            return False
        
        return True

    def _remove_obvious_duplicates(self, parameters: List[MedicalParameter]) -> List[MedicalParameter]:
        """Remove duplicatas óbvias mantendo a de maior confiança"""
        unique_params = {}
        
        for param in parameters:
            # Chave baseada em nome e valor (arredondado)
            key = (param.name.lower(), round(param.value, 2))
            
            if key not in unique_params or param.confidence > unique_params[key].confidence:
                unique_params[key] = param
        
        return list(unique_params.values())

    def _extract_patient_info(self, text: str) -> Optional[PatientInfo]:
        """Extrai informações básicas do paciente"""
        patient = PatientInfo()
        
        for field, patterns in self.patient_patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    value = match.group(1).strip()
                    
                    if field == 'name' and len(value) > 3:
                        patient.name = value.title()
                    elif field == 'age' and value.isdigit():
                        patient.age = value
                    elif field == 'gender':
                        patient.gender = value.lower()
                    
                    break
        
        if any([patient.name, patient.age, patient.gender]):
            return patient
        
        return None

    def _extract_laboratory_info(self, text: str) -> Optional[LaboratoryInfo]:
        """Extrai informações básicas do laboratório"""
        lab = LaboratoryInfo()
        
        # Buscar data
        date_pattern = re.compile(r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})', re.IGNORECASE)
        date_match = date_pattern.search(text)
        if date_match:
            lab.date = date_match.group(1)
        
        # Buscar nome do laboratório
        lab_pattern = re.compile(r'(laborat[óo]rio\s+[A-Za-zÀ-ÿ\s&]{3,30})', re.IGNORECASE)
        lab_match = lab_pattern.search(text)
        if lab_match:
            lab.name = lab_match.group(1).title()
        
        if any([lab.name, lab.date]):
            return lab
        
        return None

    def _get_reference_range(self, param_name: str) -> Optional[Dict[str, float]]:
        """Retorna faixa de referência para parâmetro"""
        ranges = self.config.REFERENCE_RANGES.get(param_name.lower())
        if ranges:
            return {
                'min': ranges['min'],
                'max': ranges['max']
            }
        return None

    def _determine_status(self, param_name: str, value: float, reference_range: Optional[Dict[str, float]]) -> str:
        """Determina status do parâmetro"""
        if not reference_range:
            return 'indeterminado'
        
        min_val = reference_range.get('min', 0)
        max_val = reference_range.get('max', float('inf'))
        
        if value < min_val:
            return 'baixo'
        elif value > max_val:
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
        """Calcula estatísticas dos parâmetros"""
        if not parameters:
            return {
                'total_parameters': 0,
                'by_status': {},
                'by_category': {},
                'normal_percentage': 0,
                'altered_percentage': 0
            }
        
        total = len(parameters)
        by_status = {}
        by_category = {}
        
        for param in parameters:
            # Por status
            status = param.status
            by_status[status] = by_status.get(status, 0) + 1
            
            # Por categoria
            category = param.category
            by_category[category] = by_category.get(category, 0) + 1
        
        normal_count = by_status.get('normal', 0)
        altered_count = by_status.get('alto', 0) + by_status.get('baixo', 0)
        
        return {
            'total_parameters': total,
            'by_status': by_status,
            'by_category': by_category,
            'normal_percentage': (normal_count / total) * 100 if total > 0 else 0,
            'altered_percentage': (altered_count / total) * 100 if total > 0 else 0
        }

    def get_medical_insights(self, parameters: List[MedicalParameter]) -> List[str]:
        """Gera insights médicos básicos"""
        insights = []
        
        if not parameters:
            insights.append("Nenhum parâmetro médico foi extraído do texto.")
            return insights
        
        total = len(parameters)
        altered = [p for p in parameters if p.status in ['alto', 'baixo']]
        
        insights.append(f"✓ {total} parâmetro(s) médico(s) extraído(s) com sucesso.")
        
        if altered:
            insights.append(f"⚠️ {len(altered)} parâmetro(s) fora da faixa de referência:")
            for param in altered[:5]:  # Mostrar apenas os primeiros 5
                status_symbol = "↑" if param.status == 'alto' else "↓"
                insights.append(f"   {status_symbol} {param.name}: {param.value} {param.unit}")
        else:
            insights.append("✓ Todos os parâmetros estão dentro da faixa de referência.")
        
        return insights
