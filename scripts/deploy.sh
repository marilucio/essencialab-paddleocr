#!/bin/bash
# Script de build customizado para Railway

echo "🚀 Iniciando build customizado para Railway..."

# Configurar variáveis de ambiente
export PADDLEOCR_HOME=/tmp/.paddleocr
export HOME=/tmp

# Criar diretórios necessários
mkdir -p /tmp/.paddleocr
mkdir -p /tmp/uploads
mkdir -p /tmp/temp
mkdir -p /tmp/logs

# Instalar dependências
echo "📦 Instalando dependências..."
pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt

# Pré-baixar modelos do PaddleOCR
echo "🔄 Pré-baixando modelos PaddleOCR..."
python -c "
import os
os.environ['PADDLEOCR_HOME'] = '/tmp/.paddleocr'
try:
    from paddleocr import PaddleOCR
    print('Inicializando PaddleOCR...')
    ocr = PaddleOCR(use_angle_cls=True, lang='pt', use_gpu=False, show_log=True)
    print('✅ Modelos baixados com sucesso!')
except Exception as e:
    print(f'⚠️ Aviso ao baixar modelos: {e}')
    print('Os modelos serão baixados na primeira execução.')
"

# Copiar arquivo .env se existir
if [ -f ".env.railway" ]; then
    cp .env.railway .env
    echo "✅ Arquivo .env configurado"
fi

# Tornar scripts executáveis
chmod +x start.sh
chmod +x start_railway.py

echo "✅ Build concluído!"