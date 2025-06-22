"""
Parser especializado para extração de parâmetros médicos
Versão melhorada com maior inteligência e precisão
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple, Set
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
    """Parser avançado para parâmetros médicos"""
    
    def __init__(self):
        self.config = config_module.get_config()
        self._compile_patterns()
        self._load_medical_knowledge()
        self._define_garbage_keywords()
        self._initialize_extraction_context()

    def _initialize_extraction_context(self):
        """Inicializa contexto para evitar duplicações"""
        self.extracted_parameters = {}  # Chave: (nome_normalizado, valor) -> parâmetro
        self.processed_positions = set()  # Posições já processadas no texto

    def _define_garbage_keywords(self):
        """Define palavras-chave para identificar e ignorar lixo na extração"""
        # Lista expandida de palavras que NÃO são parâmetros médicos
        self.GARBAGE_KEYWORDS_PARAM_NAME = [
            # Informações administrativas
            'data', 'pagina', 'codigo', 'cpf', 'crm', 'medico', 'convenio', 'unidade',
            'responsavel', 'assinatura', 'exame', 'referencia', 'laudo', 'conferido',
            'material', 'metodo', 'idade', 'sexo', 'nome', 'horario', 'liberacao',
            'coleta', 'nro.exame', 'masculino', 'feminino', 'dr', 'dra', 'laboratorio',
            'rua', 'cep', 'telefone', 'cnpj', 'cnes', 'convênio', 'paciente', 'nascimento',
            'd/n', 'vr:', 'ate:', 'de:', 'para:', 'dias', 'anos', 'meses', 'horas',
            
            # Nomes próprios e lugares
            'jose', 'espedito', 'silva', 'rodrigues', 'paula', 'augusta', 'renato', 
            'miranda', 'marcus', 'henrique', 'soares', 'ana', 'pitarelo', 'uberlandia',
            'checkupmedicina', 'com', 'br', 'unimed', 'jardim', 'patricia', 'centro',
            'duque', 'caxias', 'fogaca', 'aguiar', 'borges', 'stra', 'siva',
            
            # Termos técnicos não relacionados a resultados
            'serie vermelha', 'serie branca', 'serie plaquetaria', 'morfologia',
            'observacoes', 'obs:', 'nota:', 'valores encontrados', 'valores de referencia',
            'adultos', 'criancas', 'homens', 'mulheres', 'recem-nascidos',
            'assinatura digital', 'resultado de exames on-line', 'check-up',
            
            # Métodos e materiais
            'soro', 'edta', 'sangue total', 'urina', 'plasma', 'colorimetrico',
            'enzimatico', 'eletroquimioluminescencia', 'citometria de fluxo',
            'automatizada', 'contagem', 'imunoturbidimetria', 'eletrodo seletivo',
            
            # Lixo específico do OCR
            'rasponsavel', 'tecnica', 'medcns', 'sarurej', 'fream', 'merreu', 'bcrs',
            'paus', 'audpk', 'cf4', 'mo', 'mircis', 'life', 'caug', 'magoglino', 'cdf',
            'dho', 'peds', 'egasna', 'mstico', 'rasponeaoaly', 'faaerisy', 'fveems',
            'perrige', 'brgnt', 'ao', 'she', 'cpm', 'mg', 's',
            
            # Textos de rodapé e avisos
            'os valores dos testes', 'somente seu medico', 'tem condicoes',
            'interpretar corretamente', 'estes resultados', 'bibliografia', 'fontes'
        ]
        
        self.GARBAGE_KEYWORDS_LOWER_UNIDECODED = {
            unidecode(k.lower()) for k in self.GARBAGE_KEYWORDS_PARAM_NAME if len(k) > 2
        }

        # Padrões para limpar nomes de parâmetros
        self.NAME_CLEANING_PATTERNS = [
            re.compile(r'^(Material|Método|Metodo|Colorim[ée]trico|Enzim[áa]tico|Soro|EDTA|Sangue Total|Plasma|Urina|Automatzada)\s*[:\-]?\s*', re.IGNORECASE | re.UNICODE),
            re.compile(r'\s*\((SORO|EDTA|URINA|SANGUE(\sTOTAL)?|PLASMA)\)$', re.IGNORECASE | re.UNICODE),
            re.compile(r'Valores?\s+de\s+Refer[êe]ncia\s*[:\-]?\s*', re.IGNORECASE | re.UNICODE),
            re.compile(r'Vlr?\.\s*Ref\.\s*[:\-]?\s*', re.IGNORECASE | re.UNICODE),
            re.compile(r'Limites\s*[:\-]?\s*', re.IGNORECASE | re.UNICODE),
            re.compile(r'(Adultos|Homens|Mulheres|Crian[çc]as)(\s*[:\-]\s*)?', re.IGNORECASE | re.UNICODE),
            re.compile(r'Observa[çc](ão|ões)\s*[:\-]?\s*', re.IGNORECASE | re.UNICODE),
            re.compile(r'Resultado\s*[:\-]?\s*', re.IGNORECASE | re.UNICODE),
            re.compile(r'\d{1,2}/\d{1,2}/\d{2,4}(\s+\d{1,2}:\d{1,2}(:\d{1,2})?)?', re.UNICODE),
            re.compile(r'P[áa]gina\(s\)?\s*\d+(\s*/\s*\d+)?', re.IGNORECASE | re.UNICODE)
        ]

    def _compile_patterns(self):
        """Compila padrões regex otimizados para extração"""
        self.compiled_patterns = {}
        
        # Compilar padrões específicos de parâmetros
        for param_name, patterns in self.config.PARAMETER_PATTERNS.items():
            self.compiled_patterns[param_name] = [
                re.compile(pattern, re.IGNORECASE | re.UNICODE)
                for pattern in patterns
            ]
        
        # Padrões mais inteligentes e específicos
        self.general_patterns = [
            # Padrão 1: Nome do parâmetro seguido de valor e unidade (mais comum)
            re.compile(
                r'^([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\.\(\)\-]{2,50}?)\s*:?\s+'
                r'(\d+[,.]?\d*)\s*'
                r'(mg/dL|g/dL|%|/mm³|/mm3|fL|pg|U/L|mEq/L|ng/mL|pg/mL|mcg/dL|mUI/L|microUI/mL|ng/dL)?'
                r'(?:\s+(?:Vr:|VR:)?\s*(.+?))?$',
                re.IGNORECASE | re.UNICODE | re.MULTILINE
            ),
            
            # Padrão 2: Para tabelas com valores alinhados
            re.compile(
                r'^([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\.\(\)\-]{2,50}?)\s+'
                r'(\d+[,.]?\d*)\s*'
                r'(mg/dL|g/dL|%|/mm³|/mm3|fL|pg|U/L|mEq/L|ng/mL|pg/mL|mcg/dL|mUI/L|microUI/mL|ng/dL)\s+'
                r'([\d\s,.\-aAatéTO<>]{3,})',
                re.IGNORECASE | re.UNICODE | re.MULTILINE
            ),
            
            # Padrão 3: Para resultados com "Resultado:" explícito
            re.compile(
                r'Resultado:\s*(\d+[,.]?\d*)\s*'
                r'(mg/dL|g/dL|%|/mm³|/mm3|fL|pg|U/L|mEq/L|ng/mL|pg/mL|mcg/dL|mUI/L|microUI/mL|ng/dL)',
                re.IGNORECASE | re.UNICODE
            )
        ]
        
        # Padrões melhorados para informações do paciente
        self.patient_patterns = {
            'name': [
                re.compile(r'Nome\.+:\s*([A-Za-zÀ-ÿ\s]+?)(?:\s+D/N:|$)', re.IGNORECASE | re.MULTILINE),
                re.compile(r'(?:paciente|nome)\s*:?\s*([A-Za-zÀ-ÿ\s]+?)(?:\s+\d|$)', re.IGNORECASE)
            ],
            'age': [
                re.compile(r'(?:idade|anos?)\s*:?\s*(\d{1,3})', re.IGNORECASE),
                re.compile(r'(\d{1,3})\s*anos?', re.IGNORECASE)
            ],
            'gender': [
                re.compile(r'Sexo:\s*(Masculino|Feminino|M|F)', re.IGNORECASE)
            ],
            'id': [
                re.compile(r'CPF:\s*([\d.\-]+)', re.IGNORECASE),
                re.compile(r'(?:rg|id|registro|código)\s*:?\s*([\w.\-/]+)', re.IGNORECASE)
            ]
        }

    def _load_medical_knowledge(self):
        """Carrega base de conhecimento médico expandida"""
        # Mapeamento canônico de nomes de parâmetros
        self.canonical_names = {
            'hemacias': 'Hemácias',
            'hemaciag': 'Hemácias',
            'hemoglobina': 'Hemoglobina',
            'hematocrito': 'Hematócrito',
            'hematócrito': 'Hematócrito',
            'leucocitos': 'Leucócitos',
            'leucocitos totais': 'Leucócitos',
            'plaquetas': 'Plaquetas',
            'glicemia': 'Glicose',
            'glicose': 'Glicose',
            'colesterol total': 'Colesterol Total',
            'colesterol hdl': 'HDL',
            'hdl': 'HDL',
            'colesterol ldl': 'LDL',
            'ldl': 'LDL',
            'colesterol vldl': 'VLDL',
            'vldl': 'VLDL',
            'triglicerides': 'Triglicerídeos',
            'triglicerideos': 'Triglicerídeos',
            'creatinina': 'Creatinina',
            'ureia': 'Ureia',
            'acido urico': 'Ácido Úrico',
            'tgo': 'TGO',
            'tgp': 'TGP',
            'ggt': 'GGT',
            'bilirrubina total': 'Bilirrubina Total',
            'bilirrubina direta': 'Bilirrubina Direta',
            'bilirrubina indireta': 'Bilirrubina Indireta',
            'sodio': 'Sódio',
            'potassio': 'Potássio',
            'magnesio': 'Magnésio',
            'ferro': 'Ferro',
            'ferritina': 'Ferritina',
            'vitamina d': '25-Hidroxivitamina D',
            '25-hidroxivitamina d': '25-Hidroxivitamina D',
            'vitamina b12': 'Vitamina B12',
            'acido folico': 'Ácido Fólico',
            'zinco': 'Zinco',
            'tsh': 'TSH',
            'tireoestimulante': 'TSH',
            't4 livre': 'T4 Livre',
            'psa': 'PSA',
            'psa livre': 'PSA Livre',
            'testosterona': 'Testosterona',
            'testosterona total': 'Testosterona Total',
            'testosterona livre': 'Testosterona Livre',
            'paratormonio': 'Paratormônio',
            'paratormonio intacto': 'Paratormônio',
            'pcr': 'PCR',
            'proteina c reativa': 'PCR',
            'hemoglobina glicada': 'Hemoglobina Glicada',
            'a1c': 'Hemoglobina Glicada',
            'glicemia media estimada': 'Glicemia Média Estimada',
            'vcm': 'VCM',
            'vo1. corp. medio': 'VCM',
            'hcm': 'HCM',
            'hem.corp. media': 'HCM',
            'chcm': 'CHCM',
            'c.h. corp. media': 'CHCM',
            'rdw': 'RDW',
            'r. d. w': 'RDW',
            'vpm': 'VPM',
            'volume plaquetario medio': 'VPM',
            'neutrofilos': 'Neutrófilos',
            'segmentados': 'Segmentados',
            'eosinofilos': 'Eosinófilos',
            'basofilos': 'Basófilos',
            'linfocitos': 'Linfócitos',
            'linfocitos tipicos': 'Linfócitos',
            'monocitos': 'Monócitos',
            'monoci tos': 'Monócitos',
            'fosfatase alcalina': 'Fosfatase Alcalina',
            'colesterol nao hdl': 'Colesterol Não-HDL',
            'filtracao glomerular': 'Filtração Glomerular',
            'filtracão glomerular calculada': 'Filtração Glomerular'
        }
        
        # Categorias expandidas
        self.expanded_categories = {}
        for category, parameters in self.config.MEDICAL_CATEGORIES.items():
            expanded_params = set()
            for param in parameters:
                param_lower = param.lower()
                expanded_params.add(param_lower)
                # Adicionar variações do canonical_names
                for key, value in self.canonical_names.items():
                    if value.lower() == param_lower:
                        expanded_params.add(key)
            self.expanded_categories[category] = list(expanded_params)

    def parse_medical_text(self, text: str, confidence_threshold: float = 0.7) -> Dict[str, Any]:
        """Analisa texto médico e extrai parâmetros estruturados com inteligência aprimorada"""
        try:
            # Reinicializar contexto para nova análise
            self._initialize_extraction_context()
            
            # Dividir texto em seções para análise mais precisa
            sections = self._split_into_sections(text)
            
            # Extrair informações estruturadas
            patient_info = self._extract_patient_info(text)
            lab_info = self._extract_laboratory_info(text)
            
            # Extrair parâmetros de cada seção
            all_parameters = []
            for section in sections:
                if self._is_medical_results_section(section):
                    parameters = self._extract_parameters_from_section(section, confidence_threshold)
                    all_parameters.extend(parameters)
            
            # Remover duplicatas finais
            unique_parameters = self._remove_duplicates(all_parameters)
            
            # Categorizar e calcular estatísticas
            categorized_params = self._categorize_parameters(unique_parameters)
            stats = self._calculate_statistics(unique_parameters)
            
            return {
                'patient': patient_info.__dict__ if patient_info else None,
                'laboratory': lab_info.__dict__ if lab_info else None,
                'parameters': [p.__dict__ for p in unique_parameters],
                'categories': categorized_params,
                'statistics': stats,
                'total_parameters': len(unique_parameters),
                'confidence_avg': sum(p.confidence for p in unique_parameters) / len(unique_parameters) if unique_parameters else 0.0
            }
            
        except Exception as e:
            logger.error("Erro no parsing médico", error=str(e), exc_info=True)
            return {'error': str(e)}

    def _split_into_sections(self, text: str) -> List[str]:
        """Divide o texto em seções lógicas baseadas em marcadores"""
        sections = []
        current_section = []
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            
            # Detectar início de nova seção
            if any(marker in line.upper() for marker in [
                'HEMOGRAMA', 'BIOQUIMICA', 'PERFIL LIPIDICO', 'HORMÔNIOS',
                'URINA', 'IMUNOLOGIA', 'HEMATOLOGIA', 'SERIE VERMELHA',
                'SERIE BRANCA', 'SERIE PLAQUETARIA'
            ]):
                if current_section:
                    sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)
        
        if current_section:
            sections.append('\n'.join(current_section))
        
        return sections

    def _is_medical_results_section(self, section: str) -> bool:
        """Verifica se a seção contém resultados médicos"""
        # Indicadores de seção médica
        medical_indicators = [
            r'\d+[,.]?\d*\s*(mg/dL|g/dL|%|/mm³|U/L|mEq/L)',
            r'(Vr:|VR:|Valor de referência|Valores de referência)',
            r'(Material|Método|Resultado)',
            r'(HEMOGRAMA|BIOQUIMICA|LIPIDOGRAMA|HORMÔNIOS)'
        ]
        
        for indicator in medical_indicators:
            if re.search(indicator, section, re.IGNORECASE):
                return True
        return False

    def _extract_parameters_from_section(self, section: str, confidence_threshold: float) -> List[MedicalParameter]:
        """Extrai parâmetros de uma seção específica com maior precisão"""
        parameters = []
        lines = section.split('\n')
        
        # Primeiro, tentar extrair de linhas individuais
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # Verificar se a linha não é lixo
            if self._is_garbage_line(line):
                continue
            
            # Tentar extrair parâmetro da linha
            param = self._extract_parameter_from_line(line, i)
            if param and param.confidence >= confidence_threshold:
                # Verificar se não é duplicata
                key = (self._normalize_param_name(param.name), param.value)
                if key not in self.extracted_parameters:
                    self.extracted_parameters[key] = param
                    parameters.append(param)
        
        return parameters

    def _is_garbage_line(self, line: str) -> bool:
        """Verifica se a linha inteira é lixo"""
        line_lower = unidecode(line.lower())
        
        # Linhas muito curtas ou só números
        if len(line) < 5 or line.isdigit():
            return True
        
        # Linhas que são puramente administrativas
        garbage_line_patterns = [
            r'^(página|pag\.?|pagina)\s*\d+',
            r'^data.*coleta',
            r'^data.*liberac[aã]o',
            r'^assinatura\s*digital',
            r'^check-?up\s*laborat[oó]rio',
            r'^m[eé]dico.*respons[aá]vel',
            r'^conv[eê]nio',
            r'^unidade',
            r'^cnes\s*\d+',
            r'^cpf.*\d{3}',
            r'^c[oó]digo.*\d+',
            r'resultado\s*de\s*exames\s*on-?line',
            r'rua\s+duque\s+de\s+caxias'
        ]
        
        for pattern in garbage_line_patterns:
            if re.match(pattern, line_lower):
                return True
        
        # Contar palavras válidas vs lixo
        words = line_lower.split()
        garbage_count = sum(1 for word in words if word in self.GARBAGE_KEYWORDS_LOWER_UNIDECODED)
        if len(words) > 2 and garbage_count > len(words) * 0.6:
            return True
        
        return False

    def _extract_parameter_from_line(self, line: str, line_number: int) -> Optional[MedicalParameter]:
        """Extrai parâmetro de uma linha específica"""
        # Normalizar linha
        line = re.sub(r'\s+', ' ', line).strip()
        
        # Primeiro, verificar se é um parâmetro conhecido
        line_lower = unidecode(line.lower())
        
        # Procurar por padrões específicos conhecidos
        for param_key, canonical_name in self.canonical_names.items():
            if param_key in line_lower:
                # Procurar valor numérico após o nome do parâmetro
                value_pattern = re.compile(
                    rf'{re.escape(param_key)}\s*:?\s*(\d+[,.]?\d*)\s*'
                    r'(mg/dL|g/dL|%|/mm³|/mm3|fL|pg|U/L|mEq/L|ng/mL|pg/mL|mcg/dL|mUI/L|microUI/mL|ng/dL)?',
                    re.IGNORECASE
                )
                match = value_pattern.search(line)
                if match:
                    try:
                        value = float(match.group(1).replace(',', '.'))
                        unit = match.group(2) or self._get_default_unit(canonical_name)
                        
                        # Buscar referência na mesma linha ou próximas
                        ref_range = self._extract_reference_from_context(line, line_number)
                        if not ref_range:
                            ref_range = self._get_reference_range(canonical_name)
                        
                        status = self._determine_status(canonical_name, value, ref_range)
                        category = self._get_parameter_category(canonical_name)
                        
                        return MedicalParameter(
                            name=canonical_name,
                            value=value,
                            unit=unit,
                            reference_range=ref_range,
                            status=status,
                            category=category,
                            confidence=0.95,  # Alta confiança para parâmetros conhecidos
                            original_text=line,
                            position=(line_number, line_number)
                        )
                    except (ValueError, AttributeError):
                        pass
        
        # Se não encontrou parâmetro conhecido, tentar padrões gerais
        for pattern in self.general_patterns:
            match = pattern.search(line)
            if match:
                param = self._create_parameter_from_general_match(match, line, line_number)
                if param and self._validate_parameter(param):
                    return param
        
        return None

    def _extract_reference_from_context(self, line: str, line_number: int) -> Optional[Dict[str, float]]:
        """Extrai faixa de referência do contexto da linha"""
        # Procurar por padrões de referência na mesma linha
        ref_patterns = [
            r'(?:Vr:|VR:|Valor de refer[êe]ncia:?)\s*([\d,.\s\-aAatéTO<>]+)',
            r'(\d+[,.]?\d*)\s*(?:-|–|a|até)\s*(\d+[,.]?\d*)',
            r'(?:inferior a|menor que|até)\s*(\d+[,.]?\d*)',
            r'(?:superior a|maior que|acima de)\s*(\d+[,.]?\d*)'
        ]
        
        for pattern in ref_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return self._parse_reference_range(match.group(0))
        
        return None

    def _normalize_param_name(self, name: str) -> str:
        """Normaliza nome do parâmetro para comparação"""
        name_lower = unidecode(name.lower())
        
        # Verificar se existe nome canônico
        for key, canonical in self.canonical_names.items():
            if key in name_lower or name_lower in key:
                return canonical
        
        return name

    def _create_parameter_from_general_match(self, match: re.Match, line: str, line_number: int) -> Optional[MedicalParameter]:
        """Cria parâmetro a partir de match de padrão geral com validação rigorosa"""
        try:
            groups = match.groups()
            
            # Para padrão de "Resultado:"
            if 'Resultado:' in line:
                # Encontrar o nome do parâmetro olhando linhas anteriores
                name = self._find_parameter_name_from_context(line_number)
                if not name:
                    return None
                value_str = groups[0]
                unit = groups[1] if len(groups) > 1 else ''
            else:
                raw_name = groups[0].strip()
                value_str = groups[1]
                unit = groups[2] if len(groups) > 2 else ''
                
                # Limpar e validar nome
                name = self._clean_parameter_name(raw_name)
                if not name or self._is_garbage_name(name):
                    return None
                
                # Normalizar nome
                name = self._normalize_param_name(name)
            
            # Converter valor
            value = float(value_str.replace(',', '.'))
            
            # Obter unidade padrão se não encontrada
            if not unit:
                unit = self._get_default_unit(name)
            
            # Extrair referência
            reference_range = None
            if len(groups) > 3 and groups[3]:
                reference_range = self._parse_reference_range(groups[3])
            if not reference_range:
                reference_range = self._get_reference_range(name)
            
            # Determinar categoria e status
            category = self._get_parameter_category(name)
            status = self._determine_status(name, value, reference_range)
            
            # Calcular confiança
            confidence = 0.7
            if name in self.canonical_names.values():
                confidence += 0.2
            if unit:
                confidence += 0.05
            if reference_range:
                confidence += 0.05
            
            return MedicalParameter(
                name=name,
                value=value,
                unit=unit,
                reference_range=reference_range,
                status=status,
                category=category,
                confidence=min(confidence, 0.99),
                original_text=line,
                position=(line_number, line_number)
            )
            
        except (ValueError, IndexError, AttributeError) as e:
            logger.debug(f"Erro ao criar parâmetro de match geral: {e}")
            return None

    def _find_parameter_name_from_context(self, line_number: int) -> Optional[str]:
        """Encontra nome do parâmetro baseado no contexto (linhas anteriores)"""
        # Esta função precisaria acesso ao texto completo dividido em linhas
        # Por ora, retornar None
        return None

    def _clean_parameter_name(self, raw_name: str) -> str:
        """Limpa e padroniza nome do parâmetro"""
        name = raw_name.strip()
        
        # Aplicar padrões de limpeza
        for pattern in self.NAME_CLEANING_PATTERNS:
            name = pattern.sub('', name).strip()
        
        # Remover pontuação final desnecessária
        name = re.sub(r'[:\-\.]', '', name).strip()
        
        # Normalizar espaços
        name = re.sub(r'\s+', ' ', name)
        
        return name

    def _is_garbage_name(self, name: str) -> bool:
        """Verifica se o nome é lixo com critérios rigorosos"""
        if not name or len(name) < 2:
            return True
        
        name_lower = unidecode(name.lower())
        
        # Verificar se é apenas números ou caracteres especiais
        if re.match(r'^[\d\W]+$', name):
            return True
        
        # Verificar se é uma palavra-chave de lixo completa
        if name_lower in self.GARBAGE_KEYWORDS_LOWER_UNIDECODED:
            return True
        
        # Verificar se contém muitas palavras de lixo
        words = name_lower.split()
        if len(words) > 1:
            garbage_words = sum(1 for word in words if word in self.GARBAGE_KEYWORDS_LOWER_UNIDECODED)
            if garbage_words >= len(words) * 0.7:
                return True
        
        # Verificar padrões específicos de lixo
        garbage_patterns = [
            r'^\d{2}/\d{2}/\d{4}',  # Datas
            r'^\d{3}\.\d{3}\.\d{3}-\d{2}',  # CPF
            r'^página\s*\d+',  # Páginas
            r'^check.?up',  # Check-up
            r'^dr\.?\s+\w+',  # Nome de médico
            r'^\w+\s+(CRM|CRF|CRBM)',  # Registros profissionais
        ]
        
        for pattern in garbage_patterns:
            if re.match(pattern, name_lower):
                return True
        
        return False

    def _get_default_unit(self, param_name: str) -> str:
        """Retorna unidade padrão para parâmetro baseado no nome canônico"""
        unit_map = {
            'Hemácias': '/mm³',
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
            'Hemoglobina Glicada': '%',
            'Glicemia Média Estimada': 'mg/dL',
            'Colesterol Total': 'mg/dL',
            'HDL': 'mg/dL',
            'LDL': 'mg/dL',
            'VLDL': 'mg/dL',
            'Colesterol Não-HDL': 'mg/dL',
            'Triglicerídeos': 'mg/dL',
            'Creatinina': 'mg/dL',
            'Filtração Glomerular': 'mL/min/1.73m²',
            'Ureia': 'mg/dL',
            'Ácido Úrico': 'mg/dL',
            'TGO': 'U/L',
            'TGP': 'U/L',
            'GGT': 'U/L',
            'Fosfatase Alcalina': 'U/L',
            'Bilirrubina Total': 'mg/dL',
            'Bilirrubina Direta': 'mg/dL',
            'Bilirrubina Indireta': 'mg/dL',
            'Proteínas Totais': 'g/dL',
            'Albumina': 'g/dL',
            'Globulina': 'g/dL',
            'Sódio': 'mEq/L',
            'Potássio': 'mEq/L',
            'Cálcio': 'mg/dL',
            'Magnésio': 'mg/dL',
            'Ferro': 'mcg/dL',
            'Ferritina': 'ng/mL',
            'TSH': 'mUI/L',
            'T4 Livre': 'ng/dL',
            'T3': 'ng/dL',
            'PSA': 'ng/mL',
            'PSA Livre': 'ng/mL',
            'Testosterona Total': 'ng/dL',
            'Testosterona Livre': 'ng/dL',
            'Vitamina B12': 'pg/mL',
            'Ácido Fólico': 'ng/mL',
            '25-Hidroxivitamina D': 'ng/mL',
            'Zinco': 'mcg/dL',
            'PCR': 'mg/L',
            'Paratormônio': 'pg/mL'
        }
        
        return unit_map.get(param_name, '')

    def _get_reference_range(self, param_name: str) -> Optional[Dict[str, float]]:
        """Retorna faixa de referência padrão para parâmetro"""
        # Usar o nome canônico para buscar referências
        reference_ranges = {
            'Hemácias': {'min': 4.35, 'max': 5.65},  # Homens adultos
            'Hemoglobina': {'min': 12.5, 'max': 17.5},  # Homens adultos
            'Hematócrito': {'min': 38.8, 'max': 50.0},  # Homens adultos
            'VCM': {'min': 81.2, 'max': 95.1},
            'HCM': {'min': 26.0, 'max': 34.0},
            'CHCM': {'min': 31.0, 'max': 36.0},
            'RDW': {'min': 11.8, 'max': 15.6},
            'Leucócitos': {'min': 3500, 'max': 10500},
            'Neutrófilos': {'min': 1700, 'max': 8000},
            'Linfócitos': {'min': 900, 'max': 2900},
            'Monócitos': {'min': 300, 'max': 900},
            'Eosinófilos': {'min': 50, 'max': 500},
            'Basófilos': {'min': 0, 'max': 100},
            'Plaquetas': {'min': 150000, 'max': 450000},
            'VPM': {'min': 9.2, 'max': 12.6},
            'Glicose': {'min': 70, 'max': 99},
            'Hemoglobina Glicada': {'min': 0, 'max': 5.6},
            'Colesterol Total': {'min': 0, 'max': 190},
            'HDL': {'min': 40, 'max': float('inf')},  # Homens
            'LDL': {'min': 0, 'max': 130},
            'Triglicerídeos': {'min': 0, 'max': 150},
            'Creatinina': {'min': 0.7, 'max': 1.2},  # Homens
            'Ureia': {'min': 16.6, 'max': 48.5},
            'Ácido Úrico': {'min': 3.4, 'max': 7.0},  # Homens
            'TGO': {'min': 0, 'max': 40},  # Homens
            'TGP': {'min': 0, 'max': 41},  # Homens
            'GGT': {'min': 8, 'max': 61},  # Homens
            'Fosfatase Alcalina': {'min': 40, 'max': 129},  # Homens adultos
            'Bilirrubina Total': {'min': 0, 'max': 1.2},
            'Bilirrubina Direta': {'min': 0, 'max': 0.2},
            'Bilirrubina Indireta': {'min': 0, 'max': 0.8},
            'Sódio': {'min': 135, 'max': 145},
            'Potássio': {'min': 3.5, 'max': 5.5},
            'Magnésio': {'min': 1.6, 'max': 2.6},
            'Ferro': {'min': 33, 'max': 193},
            'Ferritina': {'min': 30, 'max': 400},  # Homens
            'TSH': {'min': 0.13, 'max': 6.33},
            'T4 Livre': {'min': 0.85, 'max': 1.87},
            'PSA': {'min': 0, 'max': 4.0},
            'Testosterona Total': {'min': 249, 'max': 836},  # Homens 20-49 anos
            'Vitamina B12': {'min': 197, 'max': 771},
            'Ácido Fólico': {'min': 3.89, 'max': 26.8},
            '25-Hidroxivitamina D': {'min': 20, 'max': 60},
            'Zinco': {'min': 60, 'max': 120},
            'PCR': {'min': 0, 'max': 5},
            'Paratormônio': {'min': 15, 'max': 65}
        }
        
        return reference_ranges.get(param_name)

    def _parse_reference_range(self, ref_text: str) -> Optional[Dict[str, float]]:
        """Analisa texto de referência para extrair valores min/max"""
        if not ref_text:
            return None
        
        ref_text = ref_text.replace(',', '.')
        
        try:
            # Padrão: X a Y, X - Y, X até Y
            match = re.search(r'(\d+\.?\d*)\s*(?:-|–|a|até)\s*(\d+\.?\d*)', ref_text, re.IGNORECASE)
            if match:
                return {
                    'min': float(match.group(1)),
                    'max': float(match.group(2))
                }
            
            # Padrão: até X, menor que X
            match = re.search(r'(?:até|menor que|inferior a|<)\s*(\d+\.?\d*)', ref_text, re.IGNORECASE)
            if match:
                return {
                    'min': 0,
                    'max': float(match.group(1))
                }
            
            # Padrão: maior que X, acima de X
            match = re.search(r'(?:maior que|superior a|acima de|>)\s*(\d+\.?\d*)', ref_text, re.IGNORECASE)
            if match:
                return {
                    'min': float(match.group(1)),
                    'max': float('inf')
                }
            
        except (ValueError, AttributeError):
            logger.debug(f"Erro ao parsear faixa de referência: '{ref_text}'")
        
        return None

    def _get_parameter_category(self, param_name: str) -> str:
        """Retorna categoria do parâmetro baseado no nome canônico"""
        categories = {
            'hematologia': [
                'Hemácias', 'Hemoglobina', 'Hematócrito', 'VCM', 'HCM', 'CHCM', 'RDW',
                'Leucócitos', 'Neutrófilos', 'Segmentados', 'Eosinófilos', 'Basófilos',
                'Linfócitos', 'Monócitos', 'Plaquetas', 'VPM'
            ],
            'bioquimica': [
                'Glicose', 'Hemoglobina Glicada', 'Glicemia Média Estimada',
                'Creatinina', 'Filtração Glomerular', 'Ureia', 'Ácido Úrico',
                'Proteínas Totais', 'Albumina', 'Globulina',
                'Colesterol Total', 'HDL', 'LDL', 'VLDL', 'Colesterol Não-HDL',
                'Triglicerídeos', 'PCR'
            ],
            'enzimas': [
                'TGO', 'TGP', 'GGT', 'Fosfatase Alcalina',
                'Bilirrubina Total', 'Bilirrubina Direta', 'Bilirrubina Indireta'
            ],
            'eletrólitos': [
                'Sódio', 'Potássio', 'Cálcio', 'Magnésio', 'Cloro', 'Fósforo'
            ],
            'metais': [
                'Ferro', 'Ferritina', 'Zinco', 'Cobre', 'Selênio'
            ],
            'hormônios': [
                'TSH', 'T4 Livre', 'T3', 'PSA', 'PSA Livre',
                'Testosterona Total', 'Testosterona Livre', 'Paratormônio',
                'Cortisol', 'Insulina', 'Estradiol', 'Progesterona'
            ],
            'vitaminas': [
                'Vitamina B12', 'Ácido Fólico', '25-Hidroxivitamina D',
                'Vitamina A', 'Vitamina E', 'Vitamina K'
            ]
        }
        
        for category, params in categories.items():
            if param_name in params:
                return category
        
        return 'outros'

    def _determine_status(self, param_name: str, value: float, reference_range: Optional[Dict[str, float]]) -> str:
        """Determina status do parâmetro com lógica inteligente"""
        if not reference_range:
            return 'indeterminado'
        
        min_val = reference_range.get('min', 0)
        max_val = reference_range.get('max', float('inf'))
        
        # Lógica específica para alguns parâmetros
        critical_params = {
            'Glicose': {'critical_low': 40, 'critical_high': 400},
            'Potássio': {'critical_low': 2.5, 'critical_high': 6.5},
            'Sódio': {'critical_low': 120, 'critical_high': 160},
            'Hemoglobina': {'critical_low': 7.0, 'critical_high': 20.0},
            'Plaquetas': {'critical_low': 50000, 'critical_high': 800000},
            'Leucócitos': {'critical_low': 1000, 'critical_high': 30000}
        }
        
        # Verificar se é crítico
        if param_name in critical_params:
            critical = critical_params[param_name]
            if value < critical['critical_low'] or value > critical['critical_high']:
                return 'crítico'
        
        # Determinar status normal
        if value < min_val:
            # Calcular porcentagem abaixo do mínimo
            if min_val > 0:
                percent_below = ((min_val - value) / min_val) * 100
                if percent_below > 50:
                    return 'crítico'
            return 'baixo'
        elif value > max_val and max_val < float('inf'):
            # Calcular porcentagem acima do máximo
            percent_above = ((value - max_val) / max_val) * 100
            if percent_above > 50:
                return 'crítico'
            return 'alto'
        else:
            return 'normal'

    def _remove_duplicates(self, parameters: List[MedicalParameter]) -> List[MedicalParameter]:
        """Remove duplicatas mantendo o parâmetro com maior confiança"""
        unique_params = {}
        
        for param in parameters:
            # Chave normalizada para comparação
            key = (self._normalize_param_name(param.name), round(param.value, 2))
            
            if key not in unique_params or param.confidence > unique_params[key].confidence:
                unique_params[key] = param
        
        return list(unique_params.values())

    def _validate_parameter(self, param: MedicalParameter) -> bool:
        """Valida se um parâmetro é válido com critérios rigorosos"""
        # Validar nome
        if not param.name or len(param.name) < 2:
            return False
        
        if self._is_garbage_name(param.name):
            return False
        
        # Validar valor
        if param.value < 0:
            return False
        
        # Validações específicas por tipo de parâmetro
        param_validations = {
            'Hemoglobina': (1, 30),
            'Hematócrito': (5, 80),
            'Glicose': (10, 1000),
            'Creatinina': (0.1, 20),
            'Leucócitos': (100, 100000),
            'Plaquetas': (1000, 2000000),
            'Colesterol Total': (50, 1000),
            'Triglicerídeos': (10, 5000),
            'TSH': (0.01, 100),
            'PSA': (0, 1000),
            'PCR': (0, 500)
        }
        
        if param.name in param_validations:
            min_val, max_val = param_validations[param.name]
            if param.value < min_val or param.value > max_val:
                return False
        
        # Validar confiança mínima
        if param.confidence < 0.5:
            return False
        
        return True

    def _categorize_parameters(self, parameters: List[MedicalParameter]) -> Dict[str, List[Dict]]:
        """Agrupa parâmetros por categoria"""
        categorized = {}
        
        for param in parameters:
            if param.category not in categorized:
                categorized[param.category] = []
            
            categorized[param.category].append({
                'name': param.name,
                'value': param.value,
                'unit': param.unit,
                'status': param.status,
                'confidence': param.confidence
            })
        
        # Ordenar parâmetros dentro de cada categoria
        for category in categorized:
            categorized[category].sort(key=lambda x: x['name'])
        
        return categorized

    def _calculate_statistics(self, parameters: List[MedicalParameter]) -> Dict[str, Any]:
        """Calcula estatísticas dos parâmetros extraídos"""
        if not parameters:
            return {
                'total_parameters': 0,
                'by_status': {},
                'by_category': {},
                'normal_percentage': 0,
                'altered_percentage': 0,
                'critical_percentage': 0
            }
        
        total = len(parameters)
        by_status = {}
        by_category = {}
        
        for param in parameters:
            # Contagem por status
            status = param.status
            by_status[status] = by_status.get(status, 0) + 1
            
            # Contagem por categoria
            category = param.category
            by_category[category] = by_category.get(category, 0) + 1
        
        # Calcular porcentagens
        normal_count = by_status.get('normal', 0)
        altered_count = by_status.get('alto', 0) + by_status.get('baixo', 0)
        critical_count = by_status.get('crítico', 0)
        
        return {
            'total_parameters': total,
            'by_status': by_status,
            'by_category': by_category,
            'normal_percentage': (normal_count / total) * 100 if total > 0 else 0,
            'altered_percentage': (altered_count / total) * 100 if total > 0 else 0,
            'critical_percentage': (critical_count / total) * 100 if total > 0 else 0
        }

    def get_medical_insights(self, parameters: List[MedicalParameter]) -> List[str]:
        """Gera insights médicos baseados nos parâmetros"""
        insights = []
        
        # Parâmetros alterados
        altered_params = [p for p in parameters if p.status in ['alto', 'baixo', 'crítico']]
        critical_params = [p for p in altered_params if p.status == 'crítico']
        
        if not altered_params:
            insights.append("✓ Todos os parâmetros analisados estão dentro dos valores de referência.")
            return insights
        
        # Alertas críticos
        if critical_params:
            insights.append(f"⚠️ ATENÇÃO: {len(critical_params)} parâmetro(s) em nível crítico:")
            for param in critical_params:
                insights.append(f"   • {param.name}: {param.value} {param.unit}")
        
        # Parâmetros alterados não críticos
        non_critical = [p for p in altered_params if p.status != 'crítico']
        if non_critical:
            insights.append(f"\n📊 {len(non_critical)} parâmetro(s) fora da faixa de referência:")
            for param in non_critical:
                status_symbol = "↑" if param.status == 'alto' else "↓"
                insights.append(f"   {status_symbol} {param.name}: {param.value} {param.unit}")
        
        # Insights por categoria
        categories_affected = {}
        for param in altered_params:
            if param.category not in categories_affected:
                categories_affected[param.category] = []
            categories_affected[param.category].append(param)
        
        if len(categories_affected) > 1:
            insights.append("\n📋 Categorias com alterações:")
            for category, params in categories_affected.items():
                insights.append(f"   • {category.title()}: {len(params)} alterações")
        
        return insights
