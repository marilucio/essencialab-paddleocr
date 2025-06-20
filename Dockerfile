FROM python:3.9-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar e instalar dependências
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Criar diretórios necessários
RUN mkdir -p /tmp/uploads /tmp/temp /tmp/logs

# Pré-baixar modelos do PaddleOCR para otimizar o boot
RUN python -c "import os; os.environ['PADDLEOCR_HOME'] = '/tmp/.paddleocr'; from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='pt', use_gpu=False, show_log=True)"

# Porta (será definida pela variável de ambiente PORT)
EXPOSE 5000

# Comando de inicialização otimizado para Railway, executado como módulo
CMD ["python", "-m", "utils.start_railway"]
