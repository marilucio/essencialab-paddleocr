#!/bin/bash

# Script de deploy do serviço PaddleOCR
# Automatiza todo o processo de build e inicialização

set -e  # Parar em caso de erro

echo "🚀 Iniciando deploy do PaddleOCR Service..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log colorido
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    error "Docker não está instalado. Instale o Docker primeiro."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose não está instalado. Instale o Docker Compose primeiro."
    exit 1
fi

# Verificar se estamos no diretório correto
if [ ! -f "docker-compose.yml" ]; then
    error "Arquivo docker-compose.yml não encontrado. Execute este script do diretório paddleocr-service/"
    exit 1
fi

# Criar arquivo .env se não existir
if [ ! -f ".env" ]; then
    log "Criando arquivo .env com configurações padrão..."
    cat > .env << EOF
# Configurações do PaddleOCR Service
PADDLEOCR_API_KEY=paddleocr-$(date +%s)
ENABLE_GPU=false
PADDLE_OCR_LANG=pt
MAX_FILE_SIZE=10485760
LOG_LEVEL=INFO
WORKERS=2

# Redis
REDIS_URL=redis://redis:6379

# Configurações opcionais
DEBUG=false
CACHE_TTL=3600
CONFIDENCE_THRESHOLD=0.7
EOF
    info "Arquivo .env criado. Edite conforme necessário."
fi

# Criar diretórios necessários
log "Criando diretórios necessários..."
mkdir -p logs temp uploads

# Parar containers existentes
log "Parando containers existentes..."
docker-compose down --remove-orphans || true

# Limpar imagens antigas (opcional)
read -p "Deseja remover imagens Docker antigas? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log "Removendo imagens antigas..."
    docker system prune -f
    docker-compose build --no-cache
else
    log "Fazendo build das imagens..."
    docker-compose build
fi

# Verificar se o build foi bem-sucedido
if [ $? -ne 0 ]; then
    error "Falha no build das imagens Docker"
    exit 1
fi

# Iniciar serviços
log "Iniciando serviços..."
docker-compose up -d

# Aguardar serviços ficarem prontos
log "Aguardando serviços ficarem prontos..."
sleep 10

# Verificar health dos serviços
log "Verificando health dos serviços..."

# Verificar Redis
if docker-compose exec redis redis-cli ping | grep -q "PONG"; then
    log "✅ Redis está funcionando"
else
    warn "❌ Redis não está respondendo"
fi

# Verificar API PaddleOCR
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:8000/health > /dev/null; then
        log "✅ API PaddleOCR está funcionando"
        break
    else
        info "Tentativa $attempt/$max_attempts - Aguardando API ficar pronta..."
        sleep 2
        ((attempt++))
    fi
done

if [ $attempt -gt $max_attempts ]; then
    error "❌ API PaddleOCR não ficou pronta após $max_attempts tentativas"
    echo "Logs da API:"
    docker-compose logs paddleocr-api
    exit 1
fi

# Testar endpoint básico
log "Testando endpoints da API..."

# Health check
health_response=$(curl -s http://localhost:8000/health)
if echo "$health_response" | grep -q '"status":"healthy"'; then
    log "✅ Health check passou"
else
    warn "❌ Health check falhou"
    echo "Resposta: $health_response"
fi

# Info endpoint
info_response=$(curl -s http://localhost:8000/info)
if echo "$info_response" | grep -q '"name":"PaddleOCR Medical API"'; then
    log "✅ Info endpoint funcionando"
else
    warn "❌ Info endpoint com problemas"
fi

# Mostrar status dos containers
log "Status dos containers:"
docker-compose ps

# Mostrar informações de acesso
echo ""
echo "🎉 Deploy concluído com sucesso!"
echo ""
echo "📋 Informações de acesso:"
echo "  • API Health: http://localhost:8000/health"
echo "  • API Info: http://localhost:8000/info"
echo "  • API OCR: http://localhost:8000/ocr (POST com Authorization header)"
echo "  • Redis: localhost:6379"
echo ""
echo "🔑 API Key: $(grep PADDLEOCR_API_KEY .env | cut -d'=' -f2)"
echo ""
echo "📊 Comandos úteis:"
echo "  • Ver logs: docker-compose logs -f"
echo "  • Parar serviços: docker-compose down"
echo "  • Reiniciar: docker-compose restart"
echo "  • Status: docker-compose ps"
echo ""

# Exemplo de teste
echo "🧪 Exemplo de teste da API:"
echo "curl -X POST http://localhost:8000/ocr \\"
echo "  -H 'Authorization: Bearer $(grep PADDLEOCR_API_KEY .env | cut -d'=' -f2)' \\"
echo "  -F 'file=@/caminho/para/exame.jpg'"
echo ""

log "Deploy finalizado! 🚀"
