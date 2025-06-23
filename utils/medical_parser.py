"""
Parser inteligente para extração de parâmetros médicos
Busca valores próximos aos nomes de parâmetros conhecidos
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
    status: str
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
    """Parser inteligente que busca valores próximos aos nomes"""
    
    def __init__(self):
        self.config = config_module.config
        self._load_medical_knowledge()

    def _load_medical_knowledge(self):
        """Carrega base de conhecimento médico abrangente"""
        
        # Base de conhecimento expandida com TODOS os exames da lista fornecida
        self.medical_parameters = {
            # HEMOGRAMA COMPLETO - SÉRIE VERMELHA
            'hemacias': {'canonical': 'Hemácias', 'unit': 'milhões/mm³', 'category': 'hematologia', 'ref': {'min': 4.5, 'max': 5.9}},
            'hemácias': {'canonical': 'Hemácias', 'unit': 'milhões/mm³', 'category': 'hematologia', 'ref': {'min': 4.5, 'max': 5.9}},
            'eritrocitos': {'canonical': 'Hemácias', 'unit': 'milhões/mm³', 'category': 'hematologia', 'ref': {'min': 4.5, 'max': 5.9}},
            'globulos vermelhos': {'canonical': 'Hemácias', 'unit': 'milhões/mm³', 'category': 'hematologia', 'ref': {'min': 4.5, 'max': 5.9}},
            
            'hemoglobina': {'canonical': 'Hemoglobina', 'unit': 'g/dL', 'category': 'hematologia', 'ref': {'min': 13.5, 'max': 17.5}},
            'hb': {'canonical': 'Hemoglobina', 'unit': 'g/dL', 'category': 'hematologia', 'ref': {'min': 13.5, 'max': 17.5}},
            
            'hematocrito': {'canonical': 'Hematócrito', 'unit': '%', 'category': 'hematologia', 'ref': {'min': 38.8, 'max': 50.0}},
            'hematócrito': {'canonical': 'Hematócrito', 'unit': '%', 'category': 'hematologia', 'ref': {'min': 38.8, 'max': 50.0}},
            'ht': {'canonical': 'Hematócrito', 'unit': '%', 'category': 'hematologia', 'ref': {'min': 38.8, 'max': 50.0}},
            'hct': {'canonical': 'Hematócrito', 'unit': '%', 'category': 'hematologia', 'ref': {'min': 38.8, 'max': 50.0}},
            
            'vcm': {'canonical': 'VCM', 'unit': 'fL', 'category': 'hematologia', 'ref': {'min': 81.2, 'max': 95.1}},
            'vol corp medio': {'canonical': 'VCM', 'unit': 'fL', 'category': 'hematologia', 'ref': {'min': 81.2, 'max': 95.1}},
            'vol. corp. medio': {'canonical': 'VCM', 'unit': 'fL', 'category': 'hematologia', 'ref': {'min': 81.2, 'max': 95.1}},
            'volume corpuscular medio': {'canonical': 'VCM', 'unit': 'fL', 'category': 'hematologia', 'ref': {'min': 81.2, 'max': 95.1}},
            
            'hcm': {'canonical': 'HCM', 'unit': 'pg', 'category': 'hematologia', 'ref': {'min': 27.0, 'max': 32.0}},
            'hem corp media': {'canonical': 'HCM', 'unit': 'pg', 'category': 'hematologia', 'ref': {'min': 27.0, 'max': 32.0}},
            'hem.corp. media': {'canonical': 'HCM', 'unit': 'pg', 'category': 'hematologia', 'ref': {'min': 27.0, 'max': 32.0}},
            'hemoglobina corpuscular media': {'canonical': 'HCM', 'unit': 'pg', 'category': 'hematologia', 'ref': {'min': 27.0, 'max': 32.0}},
            
            'chcm': {'canonical': 'CHCM', 'unit': '%', 'category': 'hematologia', 'ref': {'min': 32.0, 'max': 36.0}},
            'concentracao hemoglobina corpuscular media': {'canonical': 'CHCM', 'unit': '%', 'category': 'hematologia', 'ref': {'min': 32.0, 'max': 36.0}},
            
            'rdw': {'canonical': 'RDW', 'unit': '%', 'category': 'hematologia', 'ref': {'min': 11.5, 'max': 14.5}},
            'red cell distribution width': {'canonical': 'RDW', 'unit': '%', 'category': 'hematologia', 'ref': {'min': 11.5, 'max': 14.5}},
            
            'morfologia das hemacias': {'canonical': 'Morfologia das Hemácias', 'unit': '', 'category': 'hematologia', 'ref': {}},
            'morfologia hemacias': {'canonical': 'Morfologia das Hemácias', 'unit': '', 'category': 'hematologia', 'ref': {}},
            
            # HEMOGRAMA COMPLETO - SÉRIE BRANCA
            'leucocitos': {'canonical': 'Leucócitos', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 4000, 'max': 11000}},
            'leucocitos totais': {'canonical': 'Leucócitos', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 4000, 'max': 11000}},
            'globulos brancos': {'canonical': 'Leucócitos', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 4000, 'max': 11000}},
            'wbc': {'canonical': 'Leucócitos', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 4000, 'max': 11000}},
            
            'neutrofilos': {'canonical': 'Neutrófilos', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 1700, 'max': 8000}},
            'neutrofilos totais': {'canonical': 'Neutrófilos', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 1700, 'max': 8000}},
            'neutrofilos segmentados': {'canonical': 'Neutrófilos Segmentados', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 1700, 'max': 8000}},
            'segmentados': {'canonical': 'Neutrófilos Segmentados', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 1700, 'max': 8000}},
            'neutrofilos bastonetes': {'canonical': 'Neutrófilos Bastonetes', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 0, 'max': 700}},
            'bastonetes': {'canonical': 'Neutrófilos Bastonetes', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 0, 'max': 700}},
            
            'promielocitos': {'canonical': 'Promielócitos', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 0, 'max': 0}},
            'mielocitos': {'canonical': 'Mielócitos', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 0, 'max': 0}},
            'metamielocitos': {'canonical': 'Metamielócitos', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 0, 'max': 0}},
            
            'eosinofilos': {'canonical': 'Eosinófilos', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 50, 'max': 500}},
            'basofilos': {'canonical': 'Basófilos', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 0, 'max': 100}},
            
            'linfocitos': {'canonical': 'Linfócitos', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 900, 'max': 2900}},
            'linfocitos tipicos': {'canonical': 'Linfócitos Típicos', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 900, 'max': 2900}},
            'linfocitos atipicos': {'canonical': 'Linfócitos Atípicos', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 0, 'max': 100}},
            
            'celulas atipicas': {'canonical': 'Células Atípicas', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 0, 'max': 0}},
            'monocitos': {'canonical': 'Monócitos', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 300, 'max': 900}},
            'blastos': {'canonical': 'Blastos', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 0, 'max': 0}},
            
            'morfologia dos leucocitos': {'canonical': 'Morfologia dos Leucócitos', 'unit': '', 'category': 'hematologia', 'ref': {}},
            'morfologia leucocitos': {'canonical': 'Morfologia dos Leucócitos', 'unit': '', 'category': 'hematologia', 'ref': {}},
            
            # HEMOGRAMA COMPLETO - SÉRIE PLAQUETÁRIA
            'plaquetas': {'canonical': 'Plaquetas', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 150000, 'max': 450000}},
            'plt': {'canonical': 'Plaquetas', 'unit': '/mm³', 'category': 'hematologia', 'ref': {'min': 150000, 'max': 450000}},
            
            'vpm': {'canonical': 'VPM', 'unit': 'fL', 'category': 'hematologia', 'ref': {'min': 9.2, 'max': 12.6}},
            'volume plaquetario medio': {'canonical': 'VPM', 'unit': 'fL', 'category': 'hematologia', 'ref': {'min': 9.2, 'max': 12.6}},
            
            'morfologia das plaquetas': {'canonical': 'Morfologia das Plaquetas', 'unit': '', 'category': 'hematologia', 'ref': {}},
            'morfologia plaquetas': {'canonical': 'Morfologia das Plaquetas', 'unit': '', 'category': 'hematologia', 'ref': {}},
            
            # FERRO E FERRITINA
            'ferro': {'canonical': 'Ferro Sérico', 'unit': 'mcg/dL', 'category': 'eletrolitos', 'ref': {'min': 33, 'max': 193}},
            'ferro serico': {'canonical': 'Ferro Sérico', 'unit': 'mcg/dL', 'category': 'eletrolitos', 'ref': {'min': 33, 'max': 193}},
            'fe': {'canonical': 'Ferro Sérico', 'unit': 'mcg/dL', 'category': 'eletrolitos', 'ref': {'min': 33, 'max': 193}},
            
            'ferritina': {'canonical': 'Ferritina', 'unit': 'ng/mL', 'category': 'eletrolitos', 'ref': {'min': 30, 'max': 400}},
            
            # GLICEMIA E DIABETES
            'glicose': {'canonical': 'Glicose', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 70, 'max': 99}},
            'glicemia': {'canonical': 'Glicose', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 70, 'max': 99}},
            'glucose': {'canonical': 'Glicose', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 70, 'max': 99}},
            
            'hemoglobina glicada': {'canonical': 'Hemoglobina Glicada', 'unit': '%', 'category': 'bioquimica', 'ref': {'min': 0, 'max': 5.6}},
            'hba1c': {'canonical': 'Hemoglobina Glicada', 'unit': '%', 'category': 'bioquimica', 'ref': {'min': 0, 'max': 5.6}},
            'a1c': {'canonical': 'Hemoglobina Glicada', 'unit': '%', 'category': 'bioquimica', 'ref': {'min': 0, 'max': 5.6}},
            
            'glicemia media estimada': {'canonical': 'Glicemia Média Estimada', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 126, 'max': 154}},
            
            # PERFIL LIPÍDICO
            'colesterol total': {'canonical': 'Colesterol Total', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 0, 'max': 190}},
            'colesterol': {'canonical': 'Colesterol Total', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 0, 'max': 190}},
            
            'hdl': {'canonical': 'HDL', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 40, 'max': 999}},
            'colesterol hdl': {'canonical': 'HDL', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 40, 'max': 999}},
            'hdl colesterol': {'canonical': 'HDL', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 40, 'max': 999}},
            
            'ldl': {'canonical': 'LDL', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 0, 'max': 130}},
            'colesterol ldl': {'canonical': 'LDL', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 0, 'max': 130}},
            'ldl colesterol': {'canonical': 'LDL', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 0, 'max': 130}},
            
            'vldl': {'canonical': 'VLDL', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 0, 'max': 30}},
            'colesterol vldl': {'canonical': 'VLDL', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 0, 'max': 30}},
            
            'colesterol nao hdl': {'canonical': 'Colesterol Não-HDL', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 0, 'max': 160}},
            'colesterol não hdl': {'canonical': 'Colesterol Não-HDL', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 0, 'max': 160}},
            
            'triglicerides': {'canonical': 'Triglicerídeos', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 0, 'max': 150}},
            'triglicerideos': {'canonical': 'Triglicerídeos', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 0, 'max': 150}},
            'tg': {'canonical': 'Triglicerídeos', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 0, 'max': 150}},
            
            'lipideos totais': {'canonical': 'Lipídeos Totais', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 400, 'max': 800}},
            
            # OUTROS BIOQUÍMICOS
            'acido urico': {'canonical': 'Ácido Úrico', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 3.4, 'max': 7.0}},
            'ácido úrico': {'canonical': 'Ácido Úrico', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 3.4, 'max': 7.0}},
            'uric acid': {'canonical': 'Ácido Úrico', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 3.4, 'max': 7.0}},
            
            'pcr': {'canonical': 'PCR', 'unit': 'mg/L', 'category': 'inflamatorios', 'ref': {'min': 0, 'max': 5}},
            'proteina c reativa': {'canonical': 'PCR', 'unit': 'mg/L', 'category': 'inflamatorios', 'ref': {'min': 0, 'max': 5}},
            'c reactive protein': {'canonical': 'PCR', 'unit': 'mg/L', 'category': 'inflamatorios', 'ref': {'min': 0, 'max': 5}},
            
            # ELETRÓLITOS
            'potassio': {'canonical': 'Potássio', 'unit': 'mEq/L', 'category': 'eletrolitos', 'ref': {'min': 3.5, 'max': 5.5}},
            'potássio': {'canonical': 'Potássio', 'unit': 'mEq/L', 'category': 'eletrolitos', 'ref': {'min': 3.5, 'max': 5.5}},
            'k': {'canonical': 'Potássio', 'unit': 'mEq/L', 'category': 'eletrolitos', 'ref': {'min': 3.5, 'max': 5.5}},
            
            'sodio': {'canonical': 'Sódio', 'unit': 'mEq/L', 'category': 'eletrolitos', 'ref': {'min': 135, 'max': 145}},
            'sódio': {'canonical': 'Sódio', 'unit': 'mEq/L', 'category': 'eletrolitos', 'ref': {'min': 135, 'max': 145}},
            'na': {'canonical': 'Sódio', 'unit': 'mEq/L', 'category': 'eletrolitos', 'ref': {'min': 135, 'max': 145}},
            
            'magnesio': {'canonical': 'Magnésio', 'unit': 'mg/dL', 'category': 'eletrolitos', 'ref': {'min': 1.6, 'max': 2.6}},
            'magnésio': {'canonical': 'Magnésio', 'unit': 'mg/dL', 'category': 'eletrolitos', 'ref': {'min': 1.6, 'max': 2.6}},
            'mg': {'canonical': 'Magnésio', 'unit': 'mg/dL', 'category': 'eletrolitos', 'ref': {'min': 1.6, 'max': 2.6}},
            
            # FUNÇÃO RENAL
            'creatinina': {'canonical': 'Creatinina', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 0.6, 'max': 1.2}},
            'creat': {'canonical': 'Creatinina', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 0.6, 'max': 1.2}},
            
            'filtracao glomerular': {'canonical': 'Filtração Glomerular', 'unit': 'mL/min/1.73m²', 'category': 'bioquimica', 'ref': {'min': 90, 'max': 999}},
            'filtração glomerular': {'canonical': 'Filtração Glomerular', 'unit': 'mL/min/1.73m²', 'category': 'bioquimica', 'ref': {'min': 90, 'max': 999}},
            'tfg': {'canonical': 'Filtração Glomerular', 'unit': 'mL/min/1.73m²', 'category': 'bioquimica', 'ref': {'min': 90, 'max': 999}},
            
            'ureia': {'canonical': 'Ureia', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 15, 'max': 45}},
            'uréia': {'canonical': 'Ureia', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 15, 'max': 45}},
            'bun': {'canonical': 'Ureia', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 15, 'max': 45}},
            
            # ENZIMAS HEPÁTICAS
            'tgo': {'canonical': 'TGO', 'unit': 'U/L', 'category': 'enzimas', 'ref': {'min': 0, 'max': 40}},
            'ast': {'canonical': 'TGO', 'unit': 'U/L', 'category': 'enzimas', 'ref': {'min': 0, 'max': 40}},
            'transaminase oxalacetica': {'canonical': 'TGO', 'unit': 'U/L', 'category': 'enzimas', 'ref': {'min': 0, 'max': 40}},
            
            'tgp': {'canonical': 'TGP', 'unit': 'U/L', 'category': 'enzimas', 'ref': {'min': 0, 'max': 41}},
            'alt': {'canonical': 'TGP', 'unit': 'U/L', 'category': 'enzimas', 'ref': {'min': 0, 'max': 41}},
            'transaminase piruvica': {'canonical': 'TGP', 'unit': 'U/L', 'category': 'enzimas', 'ref': {'min': 0, 'max': 41}},
            
            'ggt': {'canonical': 'GGT', 'unit': 'U/L', 'category': 'enzimas', 'ref': {'min': 8, 'max': 61}},
            'gama gt': {'canonical': 'GGT', 'unit': 'U/L', 'category': 'enzimas', 'ref': {'min': 8, 'max': 61}},
            'gamma gt': {'canonical': 'GGT', 'unit': 'U/L', 'category': 'enzimas', 'ref': {'min': 8, 'max': 61}},
            
            # BILIRRUBINAS
            'bilirrubina total': {'canonical': 'Bilirrubina Total', 'unit': 'mg/dL', 'category': 'enzimas', 'ref': {'min': 0, 'max': 1.2}},
            'bilirrubina direta': {'canonical': 'Bilirrubina Direta', 'unit': 'mg/dL', 'category': 'enzimas', 'ref': {'min': 0, 'max': 0.2}},
            'bilirrubina indireta': {'canonical': 'Bilirrubina Indireta', 'unit': 'mg/dL', 'category': 'enzimas', 'ref': {'min': 0, 'max': 0.8}},
            
            # HORMÔNIOS
            't4 livre': {'canonical': 'T4 Livre', 'unit': 'ng/dL', 'category': 'hormonal', 'ref': {'min': 0.85, 'max': 1.87}},
            't4l': {'canonical': 'T4 Livre', 'unit': 'ng/dL', 'category': 'hormonal', 'ref': {'min': 0.85, 'max': 1.87}},
            'tiroxina livre': {'canonical': 'T4 Livre', 'unit': 'ng/dL', 'category': 'hormonal', 'ref': {'min': 0.85, 'max': 1.87}},
            
            'tsh': {'canonical': 'TSH', 'unit': 'mUI/L', 'category': 'hormonal', 'ref': {'min': 0.4, 'max': 4.0}},
            'hormonio tireoestimulante': {'canonical': 'TSH', 'unit': 'mUI/L', 'category': 'hormonal', 'ref': {'min': 0.4, 'max': 4.0}},
            'tireoestimulante': {'canonical': 'TSH', 'unit': 'mUI/L', 'category': 'hormonal', 'ref': {'min': 0.4, 'max': 4.0}},
            
            'psa total': {'canonical': 'PSA Total', 'unit': 'ng/mL', 'category': 'hormonal', 'ref': {'min': 0, 'max': 4.0}},
            'psa': {'canonical': 'PSA Total', 'unit': 'ng/mL', 'category': 'hormonal', 'ref': {'min': 0, 'max': 4.0}},
            'psa livre': {'canonical': 'PSA Livre', 'unit': 'ng/mL', 'category': 'hormonal', 'ref': {'min': 0, 'max': 1.0}},
            
            'testosterona total': {'canonical': 'Testosterona Total', 'unit': 'ng/dL', 'category': 'hormonal', 'ref': {'min': 249, 'max': 836}},
            'testosterona': {'canonical': 'Testosterona Total', 'unit': 'ng/dL', 'category': 'hormonal', 'ref': {'min': 249, 'max': 836}},
            'testosterona livre': {'canonical': 'Testosterona Livre', 'unit': 'ng/dL', 'category': 'hormonal', 'ref': {'min': 8.7, 'max': 25.1}},
            
            # VITAMINAS E MINERAIS
            'vitamina d': {'canonical': 'Vitamina D', 'unit': 'ng/mL', 'category': 'vitaminas', 'ref': {'min': 20, 'max': 60}},
            '25-oh vitamina d': {'canonical': 'Vitamina D', 'unit': 'ng/mL', 'category': 'vitaminas', 'ref': {'min': 20, 'max': 60}},
            '25 hidroxivitamina d': {'canonical': 'Vitamina D', 'unit': 'ng/mL', 'category': 'vitaminas', 'ref': {'min': 20, 'max': 60}},
            
            'acido folico': {'canonical': 'Ácido Fólico', 'unit': 'ng/mL', 'category': 'vitaminas', 'ref': {'min': 3.89, 'max': 26.8}},
            'ácido fólico': {'canonical': 'Ácido Fólico', 'unit': 'ng/mL', 'category': 'vitaminas', 'ref': {'min': 3.89, 'max': 26.8}},
            'folato': {'canonical': 'Ácido Fólico', 'unit': 'ng/mL', 'category': 'vitaminas', 'ref': {'min': 3.89, 'max': 26.8}},
            
            'zinco': {'canonical': 'Zinco', 'unit': 'mcg/dL', 'category': 'eletrolitos', 'ref': {'min': 60, 'max': 120}},
            'zn': {'canonical': 'Zinco', 'unit': 'mcg/dL', 'category': 'eletrolitos', 'ref': {'min': 60, 'max': 120}},
            
            'paratormonio': {'canonical': 'Paratormônio', 'unit': 'pg/mL', 'category': 'hormonal', 'ref': {'min': 15, 'max': 65}},
            'paratormonio intacto': {'canonical': 'Paratormônio', 'unit': 'pg/mL', 'category': 'hormonal', 'ref': {'min': 15, 'max': 65}},
            'pth': {'canonical': 'Paratormônio', 'unit': 'pg/mL', 'category': 'hormonal', 'ref': {'min': 15, 'max': 65}},
            
            # VITAMINAS ADICIONAIS
            'vitamina b12': {'canonical': 'Vitamina B12', 'unit': 'pg/mL', 'category': 'vitaminas', 'ref': {'min': 197, 'max': 771}},
            'b12': {'canonical': 'Vitamina B12', 'unit': 'pg/mL', 'category': 'vitaminas', 'ref': {'min': 197, 'max': 771}},
            'cobalamina': {'canonical': 'Vitamina B12', 'unit': 'pg/mL', 'category': 'vitaminas', 'ref': {'min': 197, 'max': 771}},
            
            # MINERAIS ADICIONAIS
            'selenio': {'canonical': 'Selênio', 'unit': 'mcg/L', 'category': 'eletrolitos', 'ref': {'min': 70, 'max': 150}},
            'selênio': {'canonical': 'Selênio', 'unit': 'mcg/L', 'category': 'eletrolitos', 'ref': {'min': 70, 'max': 150}},
            'se': {'canonical': 'Selênio', 'unit': 'mcg/L', 'category': 'eletrolitos', 'ref': {'min': 70, 'max': 150}},
            
            # HORMÔNIOS TIREOIDIANOS ADICIONAIS
            'tireoglobulina': {'canonical': 'Tireoglobulina', 'unit': 'ng/mL', 'category': 'hormonal', 'ref': {'min': 1.4, 'max': 78.0}},
            'tg': {'canonical': 'Tireoglobulina', 'unit': 'ng/mL', 'category': 'hormonal', 'ref': {'min': 1.4, 'max': 78.0}},
            
            'anti tpo': {'canonical': 'Anti-TPO', 'unit': 'UI/mL', 'category': 'hormonal', 'ref': {'min': 0, 'max': 34}},
            'anti-tpo': {'canonical': 'Anti-TPO', 'unit': 'UI/mL', 'category': 'hormonal', 'ref': {'min': 0, 'max': 34}},
            'tpo': {'canonical': 'Anti-TPO', 'unit': 'UI/mL', 'category': 'hormonal', 'ref': {'min': 0, 'max': 34}},
            'peroxidase tireoidiana': {'canonical': 'Anti-TPO', 'unit': 'UI/mL', 'category': 'hormonal', 'ref': {'min': 0, 'max': 34}},
            
            'rt3': {'canonical': 'rT3', 'unit': 'ng/dL', 'category': 'hormonal', 'ref': {'min': 9.2, 'max': 24.1}},
            'reverse t3': {'canonical': 'rT3', 'unit': 'ng/dL', 'category': 'hormonal', 'ref': {'min': 9.2, 'max': 24.1}},
            't3 reverso': {'canonical': 'rT3', 'unit': 'ng/dL', 'category': 'hormonal', 'ref': {'min': 9.2, 'max': 24.1}},
            
            't3': {'canonical': 'T3', 'unit': 'ng/dL', 'category': 'hormonal', 'ref': {'min': 80, 'max': 200}},
            't3 total': {'canonical': 'T3', 'unit': 'ng/dL', 'category': 'hormonal', 'ref': {'min': 80, 'max': 200}},
            'triiodotironina': {'canonical': 'T3', 'unit': 'ng/dL', 'category': 'hormonal', 'ref': {'min': 80, 'max': 200}},
            
            't4': {'canonical': 'T4', 'unit': 'mcg/dL', 'category': 'hormonal', 'ref': {'min': 4.5, 'max': 12.0}},
            't4 total': {'canonical': 'T4', 'unit': 'mcg/dL', 'category': 'hormonal', 'ref': {'min': 4.5, 'max': 12.0}},
            'tiroxina': {'canonical': 'T4', 'unit': 'mcg/dL', 'category': 'hormonal', 'ref': {'min': 4.5, 'max': 12.0}},
            
            # INFLAMATÓRIOS ADICIONAIS
            'vhs': {'canonical': 'VHS', 'unit': 'mm/h', 'category': 'inflamatorios', 'ref': {'min': 0, 'max': 20}},
            'velocidade hemossedimentacao': {'canonical': 'VHS', 'unit': 'mm/h', 'category': 'inflamatorios', 'ref': {'min': 0, 'max': 20}},
            'velocidade de hemossedimentacao': {'canonical': 'VHS', 'unit': 'mm/h', 'category': 'inflamatorios', 'ref': {'min': 0, 'max': 20}},
            'esr': {'canonical': 'VHS', 'unit': 'mm/h', 'category': 'inflamatorios', 'ref': {'min': 0, 'max': 20}},
            
            # HORMÔNIOS METABÓLICOS ADICIONAIS
            'insulina': {'canonical': 'Insulina', 'unit': 'mUI/L', 'category': 'hormonal', 'ref': {'min': 2.6, 'max': 24.9}},
            'insulina basal': {'canonical': 'Insulina', 'unit': 'mUI/L', 'category': 'hormonal', 'ref': {'min': 2.6, 'max': 24.9}},
            
            # FATORES DE CRESCIMENTO (da imagem)
            'igf1': {'canonical': 'IGF-1', 'unit': 'ng/mL', 'category': 'hormonal', 'ref': {'min': 109, 'max': 284}},
            'igf-1': {'canonical': 'IGF-1', 'unit': 'ng/mL', 'category': 'hormonal', 'ref': {'min': 109, 'max': 284}},
            'fator crescimento insulina': {'canonical': 'IGF-1', 'unit': 'ng/mL', 'category': 'hormonal', 'ref': {'min': 109, 'max': 284}},
            
            'igf bp3': {'canonical': 'IGF-BP3', 'unit': 'mcg/mL', 'category': 'hormonal', 'ref': {'min': 3.3, 'max': 6.7}},
            'igf-bp3': {'canonical': 'IGF-BP3', 'unit': 'mcg/mL', 'category': 'hormonal', 'ref': {'min': 3.3, 'max': 6.7}},
            'proteina ligadora igf': {'canonical': 'IGF-BP3', 'unit': 'mcg/mL', 'category': 'hormonal', 'ref': {'min': 3.3, 'max': 6.7}},
            
            # AMINOÁCIDOS (da imagem)
            'homocisteina': {'canonical': 'Homocisteína', 'unit': 'mcmol/L', 'category': 'bioquimica', 'ref': {'min': 0, 'max': 15}},
            'homocisteína': {'canonical': 'Homocisteína', 'unit': 'mcmol/L', 'category': 'bioquimica', 'ref': {'min': 0, 'max': 15}},
            
            # VITAMINA D ESPECÍFICA (da imagem)
            '25 oh': {'canonical': '25(OH) Vitamina D', 'unit': 'ng/mL', 'category': 'vitaminas', 'ref': {'min': 20, 'max': 60}},
            '25(oh)': {'canonical': '25(OH) Vitamina D', 'unit': 'ng/mL', 'category': 'vitaminas', 'ref': {'min': 20, 'max': 60}},
            '25-oh': {'canonical': '25(OH) Vitamina D', 'unit': 'ng/mL', 'category': 'vitaminas', 'ref': {'min': 20, 'max': 60}},
            
            # ELETRÓLITOS ESPECÍFICOS (da imagem)
            'na': {'canonical': 'Sódio (Na)', 'unit': 'mEq/L', 'category': 'eletrolitos', 'ref': {'min': 135, 'max': 145}},
            'k': {'canonical': 'Potássio (K)', 'unit': 'mEq/L', 'category': 'eletrolitos', 'ref': {'min': 3.5, 'max': 5.5}},
            
            # TRIGLICERÍDEOS ESPECÍFICOS (da imagem)
            'tgs': {'canonical': 'Triglicerídeos (TGs)', 'unit': 'mg/dL', 'category': 'bioquimica', 'ref': {'min': 0, 'max': 150}},
            
            # TESTE DE IODO (da imagem)
            'iodine loading test': {'canonical': 'Iodine Loading Test', 'unit': '%', 'category': 'urina', 'ref': {'min': 90, 'max': 100}},
            'teste carga iodo': {'canonical': 'Iodine Loading Test', 'unit': '%', 'category': 'urina', 'ref': {'min': 90, 'max': 100}},
            'iodo urina': {'canonical': 'Iodine Loading Test', 'unit': '%', 'category': 'urina', 'ref': {'min': 90, 'max': 100}},
            
            # URINA TIPO 1 (EAS) - Parâmetros qualitativos
            'aspecto': {'canonical': 'Aspecto', 'unit': '', 'category': 'urina', 'ref': {}},
            'cor': {'canonical': 'Cor', 'unit': '', 'category': 'urina', 'ref': {}},
            'ph': {'canonical': 'pH', 'unit': '', 'category': 'urina', 'ref': {'min': 4.6, 'max': 8.0}},
            'densidade': {'canonical': 'Densidade', 'unit': '', 'category': 'urina', 'ref': {'min': 1.003, 'max': 1.030}},
            'hemoglobina urina': {'canonical': 'Hemoglobina (Urina)', 'unit': '', 'category': 'urina', 'ref': {}},
            'esterase leucocitaria': {'canonical': 'Esterase Leucocitária', 'unit': '', 'category': 'urina', 'ref': {}},
            'glicose urina': {'canonical': 'Glicose (Urina)', 'unit': '', 'category': 'urina', 'ref': {}},
            'proteinas urina': {'canonical': 'Proteínas (Urina)', 'unit': '', 'category': 'urina', 'ref': {}},
            'bilirrubinas urina': {'canonical': 'Bilirrubinas (Urina)', 'unit': '', 'category': 'urina', 'ref': {}},
            'urobilinogenio': {'canonical': 'Urobilinogênio', 'unit': '', 'category': 'urina', 'ref': {}},
            'corpos cetonicos': {'canonical': 'Corpos Cetônicos', 'unit': '', 'category': 'urina', 'ref': {}},
            'nitrito': {'canonical': 'Nitrito', 'unit': '', 'category': 'urina', 'ref': {}},
            'leucocitos sedimento': {'canonical': 'Leucócitos (Sedimento)', 'unit': '/campo', 'category': 'urina', 'ref': {'min': 0, 'max': 5}},
            'hemacias sedimento': {'canonical': 'Hemácias (Sedimento)', 'unit': '/campo', 'category': 'urina', 'ref': {'min': 0, 'max': 3}},
            'flora bacteriana': {'canonical': 'Flora Bacteriana', 'unit': '', 'category': 'urina', 'ref': {}},
            
            # CULTURA DE URINA
            'cultura urina': {'canonical': 'Cultura de Urina', 'unit': '', 'category': 'microbiologia', 'ref': {}},
        }

    def parse_medical_text(self, text: str, confidence_threshold: float = 0.3) -> Dict[str, Any]:
        """
        Analisa texto médico com busca inteligente por valores próximos aos nomes
        """
        try:
            logger.info(f"Iniciando parse inteligente do texto...")
            
            # Normalizar texto
            text = self._normalize_text(text)
            
            # ESTRATÉGIA PRINCIPAL: Busca inteligente por parâmetros
            parameters = self._intelligent_parameter_search(text, confidence_threshold)
            
            # Calcular estatísticas
            stats = self._calculate_statistics(parameters)
            categorized = self._categorize_parameters(parameters)
            
            logger.info(f"Total de parâmetros extraídos: {len(parameters)}")
            
            return {
                'patient': None,
                'laboratory': None,
                'parameters': [p.__dict__ for p in parameters],
                'categories': categorized,
                'statistics': stats,
                'total_parameters': len(parameters),
                'confidence_avg': sum(p.confidence for p in parameters) / len(parameters) if parameters else 0.0
            }
            
        except Exception as e:
            logger.error(f"Erro no parsing: {e}", exc_info=True)
            return {'error': str(e)}

    def _normalize_text(self, text: str) -> str:
        """Normalização básica do texto"""
        # Converter vírgulas decimais para pontos
        text = re.sub(r'(\d+),(\d+)', r'\1.\2', text)
        # Normalizar espaços
        text = re.sub(r'\s+', ' ', text)
        return text

    def _intelligent_parameter_search(self, text: str, confidence_threshold: float) -> List[MedicalParameter]:
        """
        ESTRATÉGIA INTELIGENTE: Busca por nomes de parâmetros conhecidos
        e procura valores numéricos próximos (mesma linha ou linhas adjacentes)
        """
        parameters = []
        lines = text.split('\n')
        
        # Para cada parâmetro conhecido, buscar no texto
        for param_key, param_info in self.medical_parameters.items():
            found_params = self._search_parameter_in_text(param_key, param_info, lines)
            parameters.extend(found_params)
        
        # Remover duplicatas
        parameters = self._remove_duplicates(parameters)
        
        # Filtrar por confiança
        parameters = [p for p in parameters if p.confidence >= confidence_threshold]
        
        return parameters

    def _search_parameter_in_text(self, param_key: str, param_info: Dict, lines: List[str]) -> List[MedicalParameter]:
        """Busca um parâmetro específico no texto"""
        found_parameters = []
        
        for i, line in enumerate(lines):
            line_lower = unidecode(line.lower())
            
            # Verificar se o nome do parâmetro está na linha
            if param_key in line_lower:
                logger.debug(f"Encontrado parâmetro '{param_key}' na linha {i}: {line}")
                
                # Buscar valor numérico na mesma linha
                value = self._extract_value_from_line(line)
                if value is not None:
                    param = self._create_parameter(param_info, value, line, 0.8)
                    if param:
                        found_parameters.append(param)
                    continue
                
                # Buscar valor nas próximas 3 linhas
                for j in range(i + 1, min(i + 4, len(lines))):
                    next_line = lines[j].strip()
                    if next_line:
                        value = self._extract_value_from_line(next_line)
                        if value is not None:
                            # Verificar se o valor faz sentido para este parâmetro
                            if self._value_makes_sense(param_info, value):
                                param = self._create_parameter(param_info, value, f"{line} -> {next_line}", 0.7)
                                if param:
                                    found_parameters.append(param)
                                break
                
                # Buscar "Resultado:" nas próximas linhas
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_line = lines[j].strip()
                    if 'resultado' in next_line.lower():
                        value = self._extract_value_from_line(next_line)
                        if value is not None and self._value_makes_sense(param_info, value):
                            param = self._create_parameter(param_info, value, f"{line} -> {next_line}", 0.9)
                            if param:
                                found_parameters.append(param)
                            break
        
        return found_parameters

    def _extract_value_from_line(self, line: str) -> Optional[float]:
        """Extrai valor numérico de uma linha"""
        # Buscar números decimais
        number_patterns = [
            r'(\d+[,.]?\d*)',  # Qualquer número
            r'resultado\s*:?\s*(\d+[,.]?\d*)',  # Após "resultado:"
            r'(\d+[,.]?\d*)\s*(?:mg/dL|g/dL|%|/mm³|fL|pg|U/L|mEq/L)',  # Com unidade
        ]
        
        for pattern in number_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                try:
                    value_str = match.group(1).replace(',', '.')
                    value = float(value_str)
                    if 0 <= value <= 999999:  # Validação básica
                        return value
                except ValueError:
                    continue
        
        return None

    def _value_makes_sense(self, param_info: Dict, value: float) -> bool:
        """Verifica se o valor faz sentido para o parâmetro"""
        ref = param_info.get('ref', {})
        min_val = ref.get('min', 0)
        max_val = ref.get('max', 999999)
        
        # Permitir valores até 50% fora da faixa de referência
        extended_min = min_val * 0.5 if min_val > 0 else 0
        extended_max = max_val * 1.5
        
        return extended_min <= value <= extended_max

    def _create_parameter(self, param_info: Dict, value: float, original_text: str, base_confidence: float) -> Optional[MedicalParameter]:
        """Cria um parâmetro médico"""
        try:
            canonical_name = param_info['canonical']
            unit = param_info['unit']
            category = param_info['category']
            ref_range = param_info.get('ref')
            
            # Determinar status
            status = self._determine_status(value, ref_range)
            
            # Ajustar confiança baseada no valor
            confidence = base_confidence
            if self._value_makes_sense(param_info, value):
                confidence += 0.1
            
            return MedicalParameter(
                name=canonical_name,
                value=value,
                unit=unit,
                reference_range=ref_range,
                status=status,
                category=category,
                confidence=min(confidence, 0.95),
                original_text=original_text
            )
            
        except Exception as e:
            logger.debug(f"Erro ao criar parâmetro: {e}")
            return None

    def _determine_status(self, value: float, ref_range: Optional[Dict]) -> str:
        """Determina status do parâmetro"""
        if not ref_range:
            return 'indeterminado'
        
        min_val = ref_range.get('min', 0)
        max_val = ref_range.get('max', float('inf'))
        
        if value < min_val:
            return 'baixo'
        elif value > max_val:
            return 'alto'
        else:
            return 'normal'

    def _remove_duplicates(self, parameters: List[MedicalParameter]) -> List[MedicalParameter]:
        """Remove duplicatas mantendo a de maior confiança"""
        unique = {}
        
        for param in parameters:
            key = (param.name.lower(), round(param.value, 1))
            if key not in unique or param.confidence > unique[key].confidence:
                unique[key] = param
        
        return list(unique.values())

    def _categorize_parameters(self, parameters: List[MedicalParameter]) -> Dict[str, List[Dict]]:
        """Categoriza parâmetros"""
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
        """Calcula estatísticas"""
        if not parameters:
            return {
                'total_parameters': 0,
                'by_status': {},
                'normal_percentage': 0,
                'altered_percentage': 0
            }
        
        total = len(parameters)
        by_status = {}
        
        for param in parameters:
            status = param.status
            by_status[status] = by_status.get(status, 0) + 1
        
        normal_count = by_status.get('normal', 0)
        altered_count = by_status.get('alto', 0) + by_status.get('baixo', 0)
        
        return {
            'total_parameters': total,
            'by_status': by_status,
            'normal_percentage': (normal_count / total) * 100 if total > 0 else 0,
            'altered_percentage': (altered_count / total) * 100 if total > 0 else 0
        }

    def get_medical_insights(self, parameters: List[MedicalParameter]) -> List[str]:
        """Gera insights médicos"""
        insights = []
        
        if not parameters:
            insights.append("Nenhum parâmetro médico foi extraído.")
            return insights
        
        total = len(parameters)
        altered = [p for p in parameters if p.status in ['alto', 'baixo']]
        
        insights.append(f"✓ {total} parâmetro(s) médico(s) extraído(s) com sucesso.")
        
        if altered:
            insights.append(f"⚠️ {len(altered)} parâmetro(s) fora da faixa de referência:")
            for param in altered[:5]:
                status_symbol = "↑" if param.status == 'alto' else "↓"
                insights.append(f"   {status_symbol} {param.name}: {param.value} {param.unit}")
        else:
            insights.append("✓ Todos os parâmetros estão dentro da faixa de referência.")
        
        return insights
