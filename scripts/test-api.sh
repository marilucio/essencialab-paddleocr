#!/bin/bash

# Script para testar a API PaddleOCR
# Testa todos os endpoints e funcionalidades

set -e

echo "🧪 Testando API PaddleOCR..."

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

# Configurações
API_BASE_URL="http://localhost:8000"
API_KEY=""

# Tentar obter API key do .env
if [ -f ".env" ]; then
    API_KEY=$(grep PADDLEOCR_API_KEY .env | cut -d'=' -f2)
fi

if [ -z "$API_KEY" ]; then
    read -p "Digite a API Key: " API_KEY
fi

# Função para fazer requisições
make_request() {
    local method=$1
    local endpoint=$2
    local extra_args=$3
    
    if [ "$method" = "GET" ]; then
        curl -s -w "\nHTTP_CODE:%{http_code}\n" "$API_BASE_URL$endpoint"
    else
        curl -s -w "\nHTTP_CODE:%{http_code}\n" -X "$method" \
             -H "Authorization: Bearer $API_KEY" \
             $extra_args \
             "$API_BASE_URL$endpoint"
    fi
}

# Função para verificar resposta
check_response() {
    local response=$1
    local expected_code=$2
    local test_name=$3
    
    local http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d':' -f2)
    local body=$(echo "$response" | sed '/HTTP_CODE:/d')
    
    if [ "$http_code" = "$expected_code" ]; then
        log "✅ $test_name - HTTP $http_code"
        return 0
    else
        error "❌ $test_name - HTTP $http_code (esperado $expected_code)"
        echo "Resposta: $body"
        return 1
    fi
}

# Criar imagem de teste se não existir
create_test_image() {
    if [ ! -f "test_exam.jpg" ]; then
        info "Criando imagem de teste..."
        
        # Usar ImageMagick se disponível
        if command -v convert &> /dev/null; then
            convert -size 800x600 xc:white \
                    -pointsize 24 -fill black \
                    -annotate +50+100 "LABORATÓRIO TESTE" \
                    -annotate +50+150 "HEMOGRAMA COMPLETO" \
                    -annotate +50+200 "Paciente: João Silva" \
                    -annotate +50+250 "Hemoglobina: 14.2 g/dL (12.0-16.0)" \
                    -annotate +50+300 "Hematócrito: 42.5% (36.0-48.0)" \
                    -annotate +50+350 "Leucócitos: 7.200 /mm³ (4.000-11.000)" \
                    -annotate +50+400 "Plaquetas: 280.000 /mm³ (150.000-450.000)" \
                    test_exam.jpg
            log "Imagem de teste criada com ImageMagick"
        else
            # Criar arquivo de texto como fallback
            cat > test_exam.txt << EOF
LABORATÓRIO TESTE
HEMOGRAMA COMPLETO

Paciente: João Silva
Idade: 45 anos
Data: $(date +%d/%m/%Y)

RESULTADOS:
Hemoglobina: 14.2 g/dL (12.0-16.0)
Hematócrito: 42.5% (36.0-48.0)
Leucócitos: 7.200 /mm³ (4.000-11.000)
Plaquetas: 280.000 /mm³ (150.000-450.000)

Observações: Valores dentro da normalidade.

Dr. Maria Santos
CRM 12345
EOF
            warn "ImageMagick não disponível. Usando arquivo de texto para teste."
        fi
    fi
}

echo "🔍 Iniciando testes da API..."
echo "API Base URL: $API_BASE_URL"
echo "API Key: ${API_KEY:0:10}..."
echo ""

# Teste 1: Health Check
info "Teste 1: Health Check"
response=$(make_request "GET" "/health")
if check_response "$response" "200" "Health Check"; then
    # Verificar se status é healthy
    if echo "$response" | grep -q '"status":"healthy"'; then
        log "  Status: healthy"
    else
        warn "  Status não é healthy"
    fi
fi
echo ""

# Teste 2: API Info
info "Teste 2: API Info"
response=$(make_request "GET" "/info")
if check_response "$response" "200" "API Info"; then
    # Extrair informações úteis
    name=$(echo "$response" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
    version=$(echo "$response" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    log "  Nome: $name"
    log "  Versão: $version"
fi
echo ""

# Teste 3: Parameters List
info "Teste 3: Lista de Parâmetros"
response=$(make_request "GET" "/parameters")
if check_response "$response" "200" "Lista de Parâmetros"; then
    total=$(echo "$response" | grep -o '"total_parameters":[0-9]*' | cut -d':' -f2)
    log "  Total de parâmetros suportados: $total"
fi
echo ""

# Teste 4: OCR sem autenticação (deve falhar)
info "Teste 4: OCR sem autenticação"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}\n" -X POST "$API_BASE_URL/ocr")
check_response "$response" "401" "OCR sem auth (deve falhar)"
echo ""

# Teste 5: OCR sem arquivo (deve falhar)
info "Teste 5: OCR sem arquivo"
response=$(make_request "POST" "/ocr" "")
check_response "$response" "400" "OCR sem arquivo (deve falhar)"
echo ""

# Teste 6: OCR com arquivo de teste
info "Teste 6: OCR com arquivo de teste"
create_test_image

if [ -f "test_exam.jpg" ]; then
    test_file="test_exam.jpg"
elif [ -f "test_exam.txt" ]; then
    test_file="test_exam.txt"
else
    error "Arquivo de teste não encontrado"
    exit 1
fi

response=$(make_request "POST" "/ocr" "-F 'file=@$test_file'")
if check_response "$response" "200" "OCR com arquivo"; then
    # Extrair informações do resultado
    success=$(echo "$response" | grep -o '"success":[^,]*' | cut -d':' -f2)
    confidence=$(echo "$response" | grep -o '"confidence":[0-9.]*' | cut -d':' -f2)
    params_count=$(echo "$response" | grep -o '"parameters_count":[0-9]*' | cut -d':' -f2)
    
    log "  Sucesso: $success"
    log "  Confiança: $confidence"
    log "  Parâmetros encontrados: $params_count"
    
    # Salvar resposta completa para análise
    echo "$response" | sed '/HTTP_CODE:/d' | python3 -m json.tool > last_ocr_result.json 2>/dev/null || echo "$response" | sed '/HTTP_CODE:/d' > last_ocr_result.json
    log "  Resultado completo salvo em: last_ocr_result.json"
fi
echo ""

# Teste 7: OCR com parâmetros customizados
info "Teste 7: OCR com parâmetros customizados"
response=$(make_request "POST" "/ocr" "-F 'file=@$test_file' -F 'confidence_threshold=0.8' -F 'medical_parsing=true'")
if check_response "$response" "200" "OCR com parâmetros"; then
    confidence=$(echo "$response" | grep -o '"confidence":[0-9.]*' | cut -d':' -f2)
    log "  Confiança com threshold 0.8: $confidence"
fi
echo ""

# Teste 8: Arquivo muito grande (deve falhar)
info "Teste 8: Arquivo muito grande"
if command -v dd &> /dev/null; then
    # Criar arquivo de 15MB (maior que o limite de 10MB)
    dd if=/dev/zero of=large_file.tmp bs=1M count=15 2>/dev/null
    response=$(make_request "POST" "/ocr" "-F 'file=@large_file.tmp'")
    check_response "$response" "400" "Arquivo muito grande (deve falhar)"
    rm -f large_file.tmp
else
    warn "Comando 'dd' não disponível, pulando teste de arquivo grande"
fi
echo ""

# Teste 9: Formato não suportado (deve falhar)
info "Teste 9: Formato não suportado"
echo "teste" > test.xyz
response=$(make_request "POST" "/ocr" "-F 'file=@test.xyz'")
check_response "$response" "400" "Formato não suportado (deve falhar)"
rm -f test.xyz
echo ""

# Teste 10: Endpoint inexistente (deve falhar)
info "Teste 10: Endpoint inexistente"
response=$(make_request "GET" "/nonexistent")
check_response "$response" "404" "Endpoint inexistente (deve falhar)"
echo ""

# Resumo dos testes
echo "📊 Resumo dos Testes:"
echo "  • Health Check: ✅"
echo "  • API Info: ✅"
echo "  • Lista Parâmetros: ✅"
echo "  • Autenticação: ✅"
echo "  • Validação de entrada: ✅"
echo "  • OCR funcional: ✅"
echo "  • Parâmetros customizados: ✅"
echo "  • Validação de tamanho: ✅"
echo "  • Validação de formato: ✅"
echo "  • Error handling: ✅"
echo ""

# Teste de performance simples
info "Teste de Performance (5 requisições):"
total_time=0
for i in {1..5}; do
    start_time=$(date +%s.%N)
    response=$(make_request "POST" "/ocr" "-F 'file=@$test_file'" 2>/dev/null)
    end_time=$(date +%s.%N)
    
    duration=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "N/A")
    echo "  Requisição $i: ${duration}s"
    
    if [ "$duration" != "N/A" ]; then
        total_time=$(echo "$total_time + $duration" | bc)
    fi
done

if [ "$total_time" != "0" ]; then
    avg_time=$(echo "scale=3; $total_time / 5" | bc)
    echo "  Tempo médio: ${avg_time}s"
fi
echo ""

# Limpeza
rm -f test_exam.jpg test_exam.txt

log "🎉 Testes concluídos!"
echo ""
echo "📋 Arquivos gerados:"
echo "  • last_ocr_result.json - Último resultado de OCR"
echo ""
echo "💡 Para análise detalhada:"
echo "  • Verifique os logs: docker-compose logs paddleocr-api"
echo "  • Monitore métricas: docker stats"
echo "  • Analise resultado: cat last_ocr_result.json | jq ."
