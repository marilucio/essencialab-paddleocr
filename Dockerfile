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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar pip mais recente
RUN pip install --upgrade pip

# Copiar requirements e instalar dependências Python
COPY requirements.txt .

# Instalar dependências com logs detalhados
RUN echo "=== INSTALANDO DEPENDÊNCIAS PYTHON ===" && \
    pip install --no-cache-dir --verbose -r requirements.txt && \
    echo "=== INSTALAÇÃO CONCLUÍDA ==="

# Comandos de diagnóstico APÓS pip install
RUN echo "--- INÍCIO DIAGNÓSTICO PADDLEOCR ---" && \
    echo "1. Verificando instalação do paddleocr com pip show:" && \
    pip show paddleocr || echo "pip show paddleocr FALHOU" && \
    echo "2. Verificando instalação do paddlepaddle com pip show:" && \
    pip show paddlepaddle || echo "pip show paddlepaddle FALHOU" && \
    echo "3. Listando pacotes instalados relacionados ao paddle:" && \
    pip list | grep -i paddle || echo "Nenhum pacote paddle encontrado" && \
    echo "4. Tentando importar paddleocr em Python:" && \
    python -c "import paddleocr; print('SUCESSO: PaddleOCR importado via python -c')" || echo "FALHA: Não foi possível importar paddleocr via python -c" && \
    echo "5. Tentando importar paddleocr.PaddleOCR:" && \
    python -c "from paddleocr import PaddleOCR; print('SUCESSO: PaddleOCR.PaddleOCR importado via python -c')" || echo "FALHA: Não foi possível importar PaddleOCR.PaddleOCR via python -c" && \
    echo "6. Verificando versão do Python:" && \
    python --version && \
    echo "7. Verificando site-packages:" && \
    python -c "import site; print('Site-packages:', site.getsitepackages())" && \
    echo "8. Listando conteúdo de site-packages para paddleocr (se existir):" && \
    (ls -la $(python -c 'import site; print(site.getsitepackages()[0])')/paddleocr* 2>/dev/null || echo "AVISO: Não foi possível listar arquivos do paddleocr em site-packages") && \
    echo "--- FIM DIAGNÓSTICO PADDLEOCR ---"

# Copiar código da aplicação
COPY . .

# Criar diretórios necessários
RUN mkdir -p /tmp/uploads /tmp/temp /tmp/logs

# Expor porta
EXPOSE 5000

# Comando para iniciar com logs detalhados
CMD echo "=== INICIANDO APLICAÇÃO ===" && \
    echo "Verificando se PaddleOCR está disponível..." && \
    python -c "import paddleocr; print('PaddleOCR disponível!')" || echo "PaddleOCR NÃO DISPONÍVEL!" && \
    echo "Iniciando servidor..." && \
    gunicorn --bind 0.0.0.0:5000 --workers 1 --timeout 300 --log-level info api_server:app
