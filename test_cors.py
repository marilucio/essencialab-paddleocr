#!/usr/bin/env python3
"""
Script de teste para verificar se o servidor PaddleOCR está funcionando corretamente
e se o CORS está configurado adequadamente.
"""

import requests
import json
import sys
import os

def test_health_endpoint():
    """Testa o endpoint de health check"""
    try:
        url = "https://essencialab-paddleocr-production.up.railway.app/health"
        print(f"Testando endpoint de health: {url}")
        
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"Erro: {response.text}")
            return False
            
    except Exception as e:
        print(f"Erro ao testar health endpoint: {e}")
        return False

def test_cors_preflight():
    """Testa requisição OPTIONS (preflight CORS)"""
    try:
        url = "https://essencialab-paddleocr-production.up.railway.app/ocr"
        print(f"\nTestando CORS preflight: {url}")
        
        headers = {
            'Origin': 'https://essencialab.app',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type,Authorization,X-Requested-With'
        }
        
        response = requests.options(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        # Verificar headers CORS necessários
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
        }
        
        print(f"CORS Headers: {json.dumps(cors_headers, indent=2)}")
        
        if response.status_code == 200 and cors_headers['Access-Control-Allow-Origin'] == '*':
            print("✅ CORS preflight OK")
            return True
        else:
            print("❌ CORS preflight falhou")
            return False
            
    except Exception as e:
        print(f"Erro ao testar CORS preflight: {e}")
        return False

def test_info_endpoint():
    """Testa o endpoint de informações da API"""
    try:
        url = "https://essencialab-paddleocr-production.up.railway.app/info"
        print(f"\nTestando endpoint de info: {url}")
        
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"API Info: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"Erro: {response.text}")
            return False
            
    except Exception as e:
        print(f"Erro ao testar info endpoint: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("🧪 Iniciando testes do servidor PaddleOCR...")
    print("=" * 60)
    
    tests = [
        ("Health Check", test_health_endpoint),
        ("CORS Preflight", test_cors_preflight),
        ("API Info", test_info_endpoint),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Executando: {test_name}")
        print("-" * 40)
        result = test_func()
        results.append((test_name, result))
        
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES:")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("🎉 TODOS OS TESTES PASSARAM! O servidor está funcionando corretamente.")
        sys.exit(0)
    else:
        print("⚠️  ALGUNS TESTES FALHARAM. Verifique os logs acima.")
        sys.exit(1)

if __name__ == "__main__":
    main()
