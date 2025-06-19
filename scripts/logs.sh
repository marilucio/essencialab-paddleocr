#!/bin/bash

# Script para visualizar e gerenciar logs do PaddleOCR Service
# Oferece diferentes opções de visualização e análise

echo "📋 Gerenciador de Logs - PaddleOCR Service"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')] INFO: $1${NC}"
}

# Verificar se Docker Compose está disponível
if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose não encontrado"
    exit 1
fi

# Verificar se estamos no diretório correto
if [ ! -f "docker-compose.yml" ]; then
    error "Execute este script do diretório paddleocr-service/"
    exit 1
fi

# Função para mostrar menu
show_menu() {
    echo ""
    echo "Escolha uma opção:"
    echo "1) Ver logs em tempo real (todos os serviços)"
    echo "2) Ver logs da API PaddleOCR"
    echo "3) Ver logs do Redis"
    echo "4) Ver logs do Nginx"
    echo "5) Ver últimas 100 linhas (todos)"
    echo "6) Ver últimas 50 linhas da API"
    echo "7) Buscar por termo nos logs"
    echo "8) Ver logs de erro apenas"
    echo "9) Exportar logs para arquivo"
    echo "10) Limpar logs antigos"
    echo "11) Estatísticas dos logs"
    echo "12) Monitorar performance"
    echo "0) Sair"
    echo ""
    read -p "Digite sua escolha [0-12]: " choice
}

# Função para logs em tempo real
live_logs() {
    local service=$1
    if [ -z "$service" ]; then
        log "Mostrando logs em tempo real de todos os serviços..."
        log "Pressione Ctrl+C para parar"
        docker-compose logs -f
    else
        log "Mostrando logs em tempo real do serviço: $service"
        log "Pressione Ctrl+C para parar"
        docker-compose logs -f "$service"
    fi
}

# Função para logs com limite
tail_logs() {
    local service=$1
    local lines=$2
    
    if [ -z "$service" ]; then
        log "Últimas $lines linhas de todos os serviços:"
        docker-compose logs --tail="$lines"
    else
        log "Últimas $lines linhas do serviço: $service"
        docker-compose logs --tail="$lines" "$service"
    fi
}

# Função para buscar termo
search_logs() {
    read -p "Digite o termo para buscar: " term
    if [ -z "$term" ]; then
        warn "Termo não pode estar vazio"
        return
    fi
    
    log "Buscando por: '$term'"
    docker-compose logs | grep -i "$term" --color=always | tail -50
}

# Função para logs de erro
error_logs() {
    log "Mostrando apenas logs de erro:"
    docker-compose logs | grep -i -E "(error|exception|failed|fatal)" --color=always | tail -50
}

# Função para exportar logs
export_logs() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local filename="paddleocr_logs_$timestamp.txt"
    
    log "Exportando logs para: $filename"
    
    echo "=== PaddleOCR Service Logs - $(date) ===" > "$filename"
    echo "" >> "$filename"
    
    echo "=== Status dos Containers ===" >> "$filename"
    docker-compose ps >> "$filename"
    echo "" >> "$filename"
    
    echo "=== Logs da API PaddleOCR ===" >> "$filename"
    docker-compose logs paddleocr-api >> "$filename"
    echo "" >> "$filename"
    
    echo "=== Logs do Redis ===" >> "$filename"
    docker-compose logs redis >> "$filename"
    echo "" >> "$filename"
    
    if docker-compose ps | grep -q nginx; then
        echo "=== Logs do Nginx ===" >> "$filename"
        docker-compose logs nginx >> "$filename"
        echo "" >> "$filename"
    fi
    
    log "Logs exportados para: $filename"
    log "Tamanho do arquivo: $(du -h "$filename" | cut -f1)"
}

# Função para limpar logs
clean_logs() {
    warn "Esta ação irá limpar todos os logs dos containers"
    read -p "Tem certeza? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "Limpando logs..."
        
        # Parar containers
        docker-compose stop
        
        # Limpar logs do Docker
        docker system prune -f
        
        # Limpar logs locais se existirem
        if [ -d "logs" ]; then
            rm -rf logs/*
            log "Logs locais limpos"
        fi
        
        # Reiniciar containers
        docker-compose up -d
        
        log "Logs limpos e containers reiniciados"
    else
        info "Operação cancelada"
    fi
}

# Função para estatísticas
log_stats() {
    log "Calculando estatísticas dos logs..."
    
    echo ""
    echo "📊 Estatísticas dos Logs:"
    echo ""
    
    # Status dos containers
    echo "🐳 Status dos Containers:"
    docker-compose ps
    echo ""
    
    # Contagem de logs por serviço
    echo "📈 Contagem de Linhas por Serviço:"
    for service in paddleocr-api redis nginx; do
        if docker-compose ps | grep -q "$service"; then
            count=$(docker-compose logs "$service" 2>/dev/null | wc -l)
            echo "  $service: $count linhas"
        fi
    done
    echo ""
    
    # Logs de erro
    echo "❌ Logs de Erro (últimas 24h):"
    error_count=$(docker-compose logs --since="24h" | grep -i -c -E "(error|exception|failed|fatal)" || echo "0")
    echo "  Total de erros: $error_count"
    echo ""
    
    # Logs de sucesso OCR
    echo "✅ Processamentos OCR (últimas 24h):"
    ocr_success=$(docker-compose logs paddleocr-api --since="24h" | grep -c "Processamento concluído com sucesso" || echo "0")
    ocr_total=$(docker-compose logs paddleocr-api --since="24h" | grep -c "Iniciando processamento OCR" || echo "0")
    echo "  Sucessos: $ocr_success"
    echo "  Total: $ocr_total"
    if [ "$ocr_total" -gt 0 ]; then
        success_rate=$(echo "scale=2; $ocr_success * 100 / $ocr_total" | bc 2>/dev/null || echo "N/A")
        echo "  Taxa de sucesso: $success_rate%"
    fi
    echo ""
    
    # Uso de recursos
    echo "💾 Uso de Recursos:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep -E "(paddleocr|redis)"
    echo ""
}

# Função para monitorar performance
monitor_performance() {
    log "Iniciando monitoramento de performance..."
    log "Pressione Ctrl+C para parar"
    
    echo ""
    echo "🔍 Monitoramento em Tempo Real:"
    echo ""
    
    # Monitorar em loop
    while true; do
        clear
        echo "📊 Performance - $(date)"
        echo "=================================="
        
        # Status dos containers
        echo ""
        echo "🐳 Status dos Containers:"
        docker-compose ps
        
        # Recursos
        echo ""
        echo "💾 Uso de Recursos:"
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" | head -4
        
        # Logs recentes
        echo ""
        echo "📋 Últimos Logs (5 linhas):"
        docker-compose logs --tail=5 | tail -5
        
        # Health check
        echo ""
        echo "🏥 Health Check:"
        health_status=$(curl -s http://localhost:8000/health 2>/dev/null | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "N/A")
        echo "  API Status: $health_status"
        
        # Redis check
        redis_status=$(docker-compose exec redis redis-cli ping 2>/dev/null || echo "N/A")
        echo "  Redis Status: $redis_status"
        
        echo ""
        echo "Atualizando em 5 segundos... (Ctrl+C para parar)"
        sleep 5
    done
}

# Loop principal
while true; do
    show_menu
    
    case $choice in
        1)
            live_logs
            ;;
        2)
            live_logs "paddleocr-api"
            ;;
        3)
            live_logs "redis"
            ;;
        4)
            live_logs "nginx"
            ;;
        5)
            tail_logs "" 100
            ;;
        6)
            tail_logs "paddleocr-api" 50
            ;;
        7)
            search_logs
            ;;
        8)
            error_logs
            ;;
        9)
            export_logs
            ;;
        10)
            clean_logs
            ;;
        11)
            log_stats
            ;;
        12)
            monitor_performance
            ;;
        0)
            log "Saindo..."
            exit 0
            ;;
        *)
            warn "Opção inválida. Tente novamente."
            ;;
    esac
    
    echo ""
    read -p "Pressione Enter para continuar..."
done
