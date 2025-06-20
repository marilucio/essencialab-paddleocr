FROM python:3.9-slim

# Instalar dependências do sistema necessárias para OpenCV e PaddleOCR
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-0 \
    libgstreamer1.0-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    pkg-config \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar pip mais recente
RUN pip install --upgrade pip

# Copiar requirements primeiro para aproveitar cache
COPY requirements.txt .

# Instalar dependências com logs detalhados
RUN echo "=== INSTALANDO DEPENDÊNCIAS PYTHON ===" && \
    pip install --no-cache-dir --verbose -r requirements.txt && \
    echo "=== INSTALAÇÃO CONCLUÍDA ==="

# Pré-baixar modelos do PaddleOCR durante o build
RUN echo "=== PRÉ-BAIXANDO MODELOS PADDLEOCR ===" && \
    python -c "from paddleocr import PaddleOCR; ocr = PaddleOCR(use_angle_cls=True, lang='pt', use_gpu=False, show_log=True); print('Modelos baixados com sucesso!')" || echo "AVISO: Falha ao pré-baixar modelos"

# Copiar código da aplicação
COPY . .

# Criar diretórios necessários
RUN mkdir -p /tmp/uploads /tmp/temp /tmp/logs /tmp/.paddleocr

# Configurar variáveis de ambiente para PaddleOCR
ENV PADDLEOCR_HOME=/tmp/.paddleocr
ENV HOME=/tmp

# Script de inicialização com timeout maior
RUN echo '#!/bin/bash\n\
echo "=== INICIANDO APLICAÇÃO ==="\n\
echo "Verificando PaddleOCR..."\n\
python -c "import paddleocr; print(\"PaddleOCR disponível!\")" || echo "AVISO: PaddleOCR com problemas"\n\
echo "Iniciando Gunicorn com timeout estendido..."\n\
exec gunicorn --bind 0.0.0.0:${PORT:-5000} \
    --workers 1 \
    --timeout 300 \
    --graceful-timeout 120 \
    --keep-alive 5 \
    --log-level info \
    --preload \
    --worker-tmp-dir /dev/shm \
    api_server:app' > /app/start.sh && chmod +x /app/start.sh

# Expor porta
EXPOSE 5000

# Health check mais tolerante
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=5 \
    CMD curl -f http://localhost:${PORT:-5000}/health || exit 1

# Comando para iniciar
CMD ["/app/start.sh"]