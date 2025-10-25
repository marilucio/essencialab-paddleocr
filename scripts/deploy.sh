#!/bin/bash
# Script de build customizado para Coolify / Docker

echo "🚀 Iniciando build customizado para Coolify..."

# Variáveis e diretórios temporários
export PADDLEOCR_HOME=/tmp/.paddleocr
export HOME=/tmp
mkdir -p /tmp/.paddleocr /tmp/uploads /tmp/temp /tmp/logs

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

# Tornar scripts executáveis
chmod +x start.sh

echo "✅ Build concluído!"