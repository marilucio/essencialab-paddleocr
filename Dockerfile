FROM python:3.9-slim

# Instalar dependências do sistema incluindo Poppler para PDF
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    libgl1-mesa-glx \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar e instalar dependências
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Definir variável de ambiente para o PaddleOCR
ENV PADDLEOCR_HOME=/tmp/.paddleocr

# Criar diretórios necessários
RUN mkdir -p $PADDLEOCR_HOME /tmp/uploads /tmp/temp /tmp/logs

# Pré-baixar modelos do PaddleOCR para otimizar o boot (Restaurado)
# A variável PADDLEOCR_HOME já está definida pelo ENV
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='pt', use_gpu=False, show_log=True)"

# Porta (será definida pela variável de ambiente PORT)
EXPOSE 5000

# Comando de inicialização direto com Gunicorn, usando a porta do ambiente
# O 'exec' garante que o Gunicorn seja o processo principal (PID 1)
# Revertendo para usar $PORT. Certifique-se de que a porta exposta do serviço no Railway está configurada para o valor de $PORT (provavelmente 8080).
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 600 --log-level debug --access-logfile - --error-logfile - api_server:app
