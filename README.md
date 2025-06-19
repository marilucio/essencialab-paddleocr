# 🚀 PaddleOCR Medical Service

Serviço completo de OCR especializado para exames médicos usando PaddleOCR 2.7+ com análise inteligente de parâmetros.

## 📋 Características

- **OCR Real**: PaddleOCR 2.7+ com PP-Structure para layout e tabelas
- **Análise Médica**: Extração automática de parâmetros de qualquer exame
- **Cache Inteligente**: Redis para performance otimizada
- **API RESTful**: Endpoints completos com autenticação
- **Docker Ready**: Deploy com um comando
- **Fallback Robusto**: Múltiplas estratégias de processamento
- **Logs Estruturados**: Monitoramento completo

## 🎯 Tipos de Exames Suportados

- **Hemogramas**: Hemoglobina, Hematócrito, Leucócitos, Plaquetas
- **Bioquímica**: Glicose, Colesterol, Triglicerídeos, HDL, LDL
- **Função Renal**: Creatinina, Ureia, TFG
- **Hormonal**: TSH, T3, T4, Cortisol
- **Função Hepática**: ALT, AST, GGT, Bilirrubinas
- **E muito mais**: Identifica automaticamente qualquer parâmetro

## 🏗️ Arquitetura

```
paddleocr-service/
├── api_server.py          # Servidor Flask principal
├── medical_ocr.py         # Processador PaddleOCR
├── config.py              # Configurações centralizadas
├── utils/
│   ├── image_processor.py # Pré-processamento de imagens
│   └── medical_parser.py  # Parser médico especializado
├── scripts/
│   ├── deploy.sh          # Deploy automatizado
│   ├── test-api.sh        # Testes da API
│   └── logs.sh            # Gerenciador de logs
├── docker-compose.yml     # Orquestração Docker
├── Dockerfile             # Imagem da aplicação
└── requirements.txt       # Dependências Python
```

## 🚀 Quick Start

### 1. Clone e Configure

```bash
# Clonar o projeto (se necessário)
cd paddleocr-service

# Copiar configurações
cp .env.example .env

# Editar configurações (opcional)
nano .env
```

### 2. Deploy com Docker

```bash
# Executar deploy automatizado
chmod +x scripts/*.sh
./scripts/deploy.sh
```

### 3. Testar API

```bash
# Executar testes completos
./scripts/test-api.sh
```

## 📡 Endpoints da API

### Health Check
```bash
GET /health
```

### Informações da API
```bash
GET /info
```

### Lista de Parâmetros Suportados
```bash
GET /parameters
```

### Processamento OCR
```bash
POST /ocr
Authorization: Bearer YOUR_API_KEY
Content-Type: multipart/form-data

# Parâmetros:
# - file: Arquivo de imagem ou PDF
# - confidence_threshold: Threshold de confiança (0.0-1.0)
# - extract_tables: Extrair tabelas (true/false)
# - extract_layout: Extrair layout (true/false)
# - medical_parsing: Análise médica (true/false)
```

## 🔧 Configuração

### Variáveis de Ambiente Principais

```bash
# API
PADDLEOCR_API_KEY=sua-chave-aqui
ENABLE_GPU=false
PADDLE_OCR_LANG=pt
MAX_FILE_SIZE=10485760

# Cache
REDIS_URL=redis://redis:6379
CACHE_TTL=3600

# Performance
WORKERS=2
CONFIDENCE_THRESHOLD=0.7
```

### Configuração de GPU (Opcional)

Para usar GPU (requer NVIDIA Docker):

```bash
# No .env
ENABLE_GPU=true

# Modificar docker-compose.yml para adicionar:
runtime: nvidia
environment:
  - NVIDIA_VISIBLE_DEVICES=all
```

## 📊 Exemplo de Uso

### Curl
```bash
curl -X POST http://localhost:8000/ocr \
  -H "Authorization: Bearer paddleocr-key-2024" \
  -F "file=@exame.jpg" \
  -F "confidence_threshold=0.8"
```

### Python
```python
import requests

url = "http://localhost:8000/ocr"
headers = {"Authorization": "Bearer paddleocr-key-2024"}
files = {"file": open("exame.jpg", "rb")}
data = {"confidence_threshold": 0.8}

response = requests.post(url, headers=headers, files=files, data=data)
result = response.json()

print(f"Confiança: {result['confidence']}")
print(f"Parâmetros encontrados: {result['parameters_count']}")
```

### JavaScript/TypeScript
```typescript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('confidence_threshold', '0.8');

const response = await fetch('http://localhost:8000/ocr', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer paddleocr-key-2024'
  },
  body: formData
});

const result = await response.json();
console.log('Resultado:', result);
```

## 📈 Formato de Resposta

```json
{
  "success": true,
  "request_id": "abc123",
  "text": "texto extraído completo...",
  "confidence": 0.85,
  "processing_time_ms": 1200,
  "structured_data": {
    "patient": {
      "name": "João Silva",
      "age": "45",
      "gender": "masculino"
    },
    "laboratory": {
      "name": "Lab Exemplo",
      "responsible": "Dr. Maria"
    },
    "parameters": [
      {
        "name": "Hemoglobina",
        "value": 14.2,
        "unit": "g/dL",
        "reference_range": {"min": 12.0, "max": 16.0},
        "status": "normal",
        "category": "hematologia",
        "confidence": 0.9
      }
    ],
    "exam_type": "hemograma",
    "total_parameters": 12
  },
  "parameters_count": 12,
  "file_info": {
    "filename": "exame.jpg",
    "size_bytes": 245760,
    "format": "jpg"
  }
}
```

## 🛠️ Scripts Utilitários

### Deploy
```bash
./scripts/deploy.sh
# - Build e inicialização completa
# - Verificação de health
# - Testes básicos
```

### Testes
```bash
./scripts/test-api.sh
# - Testa todos os endpoints
# - Validações de segurança
# - Teste de performance
```

### Logs
```bash
./scripts/logs.sh
# - Visualização interativa
# - Busca e filtros
# - Estatísticas
# - Monitoramento em tempo real
```

## 🔍 Monitoramento

### Verificar Status
```bash
docker-compose ps
curl http://localhost:8000/health
```

### Ver Logs
```bash
# Logs em tempo real
docker-compose logs -f

# Logs específicos
docker-compose logs paddleocr-api
docker-compose logs redis

# Usar script interativo
./scripts/logs.sh
```

### Métricas de Performance
```bash
# Recursos dos containers
docker stats

# Estatísticas da API
curl http://localhost:8000/info
```

## 🐛 Troubleshooting

### Problemas Comuns

#### 1. API não responde
```bash
# Verificar containers
docker-compose ps

# Verificar logs
docker-compose logs paddleocr-api

# Reiniciar serviços
docker-compose restart
```

#### 2. Erro de memória
```bash
# Aumentar recursos no docker-compose.yml
services:
  paddleocr-api:
    deploy:
      resources:
        limits:
          memory: 4G
```

#### 3. OCR com baixa qualidade
```bash
# Ajustar threshold
curl -X POST http://localhost:8000/ocr \
  -F "confidence_threshold=0.5"

# Verificar qualidade da imagem
# Usar imagens com pelo menos 300 DPI
```

#### 4. Cache não funciona
```bash
# Verificar Redis
docker-compose exec redis redis-cli ping

# Limpar cache
docker-compose exec redis redis-cli FLUSHALL
```

### Logs de Debug

```bash
# Ativar debug no .env
DEBUG=true
LOG_LEVEL=DEBUG

# Reiniciar
docker-compose restart

# Ver logs detalhados
./scripts/logs.sh
```

## 🔒 Segurança

### API Key
- Sempre use uma API key forte
- Rotacione regularmente
- Não exponha em logs

### CORS
```bash
# Configurar origins específicos no .env
CORS_ORIGINS=https://meuapp.com,https://localhost:3000
```

### Rate Limiting
```bash
# Configurar no .env
RATE_LIMIT_PER_MINUTE=60
```

## 📦 Produção

### Configurações Recomendadas

```bash
# .env para produção
DEBUG=false
LOG_LEVEL=INFO
WORKERS=4
ENABLE_GPU=true  # Se disponível
CACHE_TTL=7200
MAX_REQUESTS=2000
```

### Backup e Restore

```bash
# Backup dos dados
docker-compose exec redis redis-cli BGSAVE

# Backup dos logs
./scripts/logs.sh  # Opção 9: Exportar logs
```

### Monitoramento Avançado

```bash
# Adicionar ao docker-compose.yml
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```

## 🤝 Integração com EssenciaLab

### Configurar no Frontend

```typescript
// No .env do projeto principal
PADDLEOCR_API_ENDPOINT=http://localhost:8000/ocr
PADDLEOCR_API_KEY=sua-chave-aqui
```

### Atualizar Netlify Function

A função `netlify/functions/process-exam-ocr.js` já está configurada para usar este serviço como endpoint principal.

## 📚 Referências

- [PaddleOCR Documentation](https://github.com/PaddlePaddle/PaddleOCR)
- [PP-Structure Guide](https://github.com/PaddlePaddle/PaddleOCR/blob/release/2.7/ppstructure/README.md)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [Flask Documentation](https://flask.palletsprojects.com/)

## 📄 Licença

Este projeto é parte do EssenciaLab e segue as mesmas diretrizes de licenciamento.

## 🆘 Suporte

Para problemas ou dúvidas:

1. Verificar logs: `./scripts/logs.sh`
2. Executar testes: `./scripts/test-api.sh`
3. Consultar este README
4. Verificar issues conhecidos

---

**Desenvolvido para EssenciaLab** 🌿
*Transformando exames médicos em insights inteligentes*
