#!/bin/bash

# Script de deploy otimizado para Railway
# Este script prepara o ambiente para deploy no Railway

echo "🚀 Preparando deploy para Railway..."

# Verificar se estamos no diretório correto
if [ ! -f "requirements.txt" ]; then
    echo "❌ Erro: Execute este script no diretório essencialab-paddleocr"
    exit 1
fi

# Limpar cache e arquivos temporários
echo "🧹 Limpando cache..."
rm -rf __pycache__/
rm -rf .pytest_cache/
rm -rf *.pyc
rm -rf temp/*
rm -rf uploads/*
rm -rf logs/*

# Verificar dependências críticas
echo "📦 Verificando requirements.txt..."
if ! grep -q "paddleocr" requirements.txt; then
    echo "❌ Erro: PaddleOCR não encontrado em requirements.txt"
    exit 1
fi

# Criar diretórios necessários
echo "📁 Criando diretórios..."
mkdir -p temp uploads logs utils

# Verificar arquivos essenciais
echo "🔍 Verificando arquivos essenciais..."
required_files=("api_server.py" "medical_ocr.py" "config.py" "Dockerfile" "railway.toml")

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Erro: Arquivo $file não encontrado"
        exit 1
    fi
done

# Verificar configuração do Railway
echo "⚙️ Verificando configuração do Railway..."
if [ ! -f "railway.toml" ]; then
    echo "❌ Erro: railway.toml não encontrado"
    exit 1
fi

# Verificar variáveis de ambiente
echo "🔧 Verificando .env..."
if [ ! -f ".env" ]; then
    echo "⚠️ Aviso: .env não encontrado, usando valores padrão"
fi

# Testar sintaxe Python
echo "🐍 Testando sintaxe Python..."
python3 -m py_compile api_server.py
if [ $? -ne 0 ]; then
    echo "❌ Erro: Sintaxe inválida em api_server.py"
    exit 1
fi

python3 -m py_compile medical_ocr.py
if [ $? -ne 0 ]; then
    echo "❌ Erro: Sintaxe inválida em medical_ocr.py"
    exit 1
fi

python3 -m py_compile config.py
if [ $? -ne 0 ]; then
    echo "❌ Erro: Sintaxe inválida em config.py"
    exit 1
fi

# Verificar se utils/image_processor.py existe
if [ ! -f "utils/image_processor.py" ]; then
    echo "❌ Erro: utils/image_processor.py não encontrado"
    exit 1
fi

python3 -m py_compile utils/image_processor.py
if [ $? -ne 0 ]; then
    echo "❌ Erro: Sintaxe inválida em utils/image_processor.py"
    exit 1
fi

echo "✅ Verificações concluídas com sucesso!"
echo ""
echo "📋 Resumo da configuração:"
echo "   - Inicialização lazy: ✅ Ativada"
echo "   - Health check timeout: 600s"
echo "   - Workers: 1"
echo "   - Timeout: 600s"
echo "   - Max file size: 10MB"
echo "   - GPU: Desabilitado"
echo "   - Redis: Desabilitado (evita erros de conexão)"
echo ""
echo "🚀 Pronto para deploy no Railway!"
echo ""
echo "Próximos passos:"
echo "1. Commit e push das alterações"
echo "2. Deploy automático será iniciado no Railway"
echo "3. Monitorar logs para verificar inicialização"
echo ""
echo "URLs importantes:"
echo "   - Health check: https://seu-app.railway.app/health"
echo "   - Info da API: https://seu-app.railway.app/info"
echo "   - Teste: https://seu-app.railway.app/test"
