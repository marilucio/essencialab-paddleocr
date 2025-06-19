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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar pip mais recente
RUN pip install --upgrade pip

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
# Adicionar um ARG para invalidar o cache desta camada se necessário
ARG CACHE_BUSTER=1
RUN echo "Forçando a não utilização de cache para pip install com CACHE_BUSTER=${CACHE_BUSTER}" && \
    pip install --no-cache-dir --force-reinstall -r requirements.txt

# Copiar código da aplicação
COPY . .

# Expor porta
EXPOSE 5000

# Comando para iniciar
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "api_server:app"]
