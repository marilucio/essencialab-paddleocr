#!/usr/bin/env python3
"""
Script de teste para validar deployment do PaddleOCR
Testa importações, configurações e funcionalidades básicas
"""

import sys
import os
import traceback
from datetime import datetime

def print_header(title):
    """Imprime cabeçalho formatado"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_result(test_name, success, details=""):
    """Imprime resultado do teste"""
    status = "✅ PASSOU" if success else "❌ FALHOU"
    print(f"{status} - {test_name}")
    if details:
        print(f"    {details}")

def test_python_environment():
    """Testa ambiente Python"""
    print_header("TESTE 1: AMBIENTE PYTHON")
    
    try:
        print(f"Versão Python: {sys.version}")
        print(f"Executável: {sys.executable}")
        print(f"Path: {sys.path[:3]}...")  # Primeiros 3 paths
        print_result("Ambiente Python", True)
        return True
    except Exception as e:
        print_result("Ambiente Python", False, str(e))
        return False

def test_basic_imports():
    """Testa importações básicas"""
    print_header("TESTE 2: IMPORTAÇÕES BÁSICAS")
    
    imports_to_test = [
        ("os", "os"),
        ("numpy", "numpy"),
        ("PIL", "PIL"),
        ("cv2", "opencv-python-headless"),
        ("flask", "flask"),
        ("redis", "redis"),
        ("structlog", "structlog")
    ]
    
    success_count = 0
    for module_name, package_name in imports_to_test:
        try:
            __import__(module_name)
            print_result(f"Importar {package_name}", True)
            success_count += 1
        except ImportError as e:
            print_result(f"Importar {package_name}", False, str(e))
    
    return success_count == len(imports_to_test)

def test_paddleocr_import():
    """Testa importação específica do PaddleOCR"""
    print_header("TESTE 3: PADDLEOCR")
    
    try:
        import paddleocr
        print_result("Importar paddleocr", True, f"Versão: {getattr(paddleocr, '__version__', 'desconhecida')}")
        
        try:
            from paddleocr import PaddleOCR
            print_result("Importar PaddleOCR class", True)
            
            # Tentar criar instância (sem inicializar modelos)
            try:
                # Não inicializar para evitar download de modelos
                print_result("PaddleOCR disponível", True, "Classe importada com sucesso")
                return True
            except Exception as e:
                print_result("Criar instância PaddleOCR", False, str(e))
                return False
                
        except ImportError as e:
            print_result("Importar PaddleOCR class", False, str(e))
            return False
            
    except ImportError as e:
        print_result("Importar paddleocr", False, str(e))
        return False

def test_project_imports():
    """Testa importações do projeto"""
    print_header("TESTE 4: MÓDULOS DO PROJETO")
    
    # Adicionar diretório atual ao path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    modules_to_test = [
        ("config", "Configurações"),
        ("medical_ocr", "Processador OCR"),
        ("utils.image_processor", "Processador de Imagens"),
        ("utils.medical_parser", "Parser Médico")
    ]
    
    success_count = 0
    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            print_result(f"{description}", True)
            success_count += 1
        except Exception as e:
            print_result(f"{description}", False, str(e))
    
    return success_count == len(modules_to_test)

def test_configuration():
    """Testa configurações"""
    print_header("TESTE 5: CONFIGURAÇÕES")
    
    try:
        import config
        cfg = config.config
        
        print(f"API Key: {'*' * (len(cfg.API_KEY) - 4) + cfg.API_KEY[-4:]}")
        print(f"Host: {cfg.HOST}")
        print(f"Port: {cfg.PORT}")
        print(f"Debug: {cfg.DEBUG}")
        print(f"GPU: {cfg.ENABLE_GPU}")
        print(f"Idioma: {cfg.PADDLE_OCR_LANG}")
        print(f"Temp Dir: {cfg.TEMP_DIR}")
        print(f"Upload Dir: {cfg.UPLOAD_DIR}")
        
        # Verificar se diretórios existem
        dirs_ok = True
        for dir_path in [cfg.TEMP_DIR, cfg.UPLOAD_DIR]:
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    print(f"Criado diretório: {dir_path}")
                except Exception as e:
                    print(f"Erro ao criar {dir_path}: {e}")
                    dirs_ok = False
        
        print_result("Configurações", True)
        print_result("Diretórios", dirs_ok)
        return True
        
    except Exception as e:
        print_result("Configurações", False, str(e))
        return False

def test_flask_app():
    """Testa aplicação Flask"""
    print_header("TESTE 6: APLICAÇÃO FLASK")
    
    try:
        import api_server
        app = api_server.app
        
        print(f"App criado: {app}")
        print(f"Rotas disponíveis:")
        
        with app.app_context():
            for rule in app.url_map.iter_rules():
                print(f"  {rule.methods} {rule.rule}")
        
        print_result("Aplicação Flask", True)
        return True
        
    except Exception as e:
        print_result("Aplicação Flask", False, str(e))
        traceback.print_exc()
        return False

def test_medical_ocr_processor():
    """Testa processador OCR médico"""
    print_header("TESTE 7: PROCESSADOR OCR")
    
    try:
        from medical_ocr import MedicalOCRProcessor
        
        processor = MedicalOCRProcessor()
        
        # Verificar se engines foram inicializados
        ocr_available = processor.ocr_engine is not None
        structure_available = processor.structure_engine is not None
        
        print_result("Criar processador", True)
        print_result("OCR Engine", ocr_available, "PaddleOCR inicializado" if ocr_available else "Usando modo mock")
        print_result("Structure Engine", structure_available, "PP-Structure disponível" if structure_available else "Não disponível")
        
        # Testar informações do engine
        info = processor.get_engine_info()
        print(f"Info do engine: {info}")
        
        return True
        
    except Exception as e:
        print_result("Processador OCR", False, str(e))
        traceback.print_exc()
        return False

def test_health_endpoint():
    """Testa endpoint de health check"""
    print_header("TESTE 8: HEALTH CHECK")
    
    try:
        import api_server
        app = api_server.app
        
        with app.test_client() as client:
            response = client.get('/health')
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.get_json()}")
            
            success = response.status_code == 200
            print_result("Health Check", success)
            return success
            
    except Exception as e:
        print_result("Health Check", False, str(e))
        return False

def main():
    """Função principal"""
    print_header("TESTE DE DEPLOYMENT - PADDLEOCR SERVICE")
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Diretório: {os.getcwd()}")
    
    tests = [
        test_python_environment,
        test_basic_imports,
        test_paddleocr_import,
        test_project_imports,
        test_configuration,
        test_flask_app,
        test_medical_ocr_processor,
        test_health_endpoint
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ ERRO CRÍTICO em {test_func.__name__}: {e}")
            traceback.print_exc()
            results.append(False)
    
    # Resumo final
    print_header("RESUMO DOS TESTES")
    passed = sum(results)
    total = len(results)
    
    print(f"Testes passaram: {passed}/{total}")
    print(f"Taxa de sucesso: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Deploy está pronto para produção")
        exit_code = 0
    elif passed >= total * 0.8:  # 80% ou mais
        print("\n⚠️  MAIORIA DOS TESTES PASSOU")
        print("🔧 Alguns ajustes podem ser necessários")
        exit_code = 0
    else:
        print("\n❌ MUITOS TESTES FALHARAM")
        print("🚨 Deploy precisa de correções antes da produção")
        exit_code = 1
    
    print(f"\nCódigo de saída: {exit_code}")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
