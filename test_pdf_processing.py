#!/usr/bin/env python3
"""
Script de teste para verificar se o processamento de PDF está funcionando
"""

import requests
import sys
import os

def test_pdf_processing():
    """Testa o processamento de PDF no servidor"""
    
    # URL do servidor (ajuste conforme necessário)
    base_url = "https://essencialab-paddleocr-production.up.railway.app"
    api_key = "paddleocr-key-2024"
    
    print("🔍 Testando servidor PaddleOCR...")
    
    # 1. Teste de health check
    try:
        print("1. Testando health check...")
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
