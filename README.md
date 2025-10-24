# EssenciaLab PaddleOCR Service

Serviço de OCR otimizado para processamento de exames médicos usando PaddleOCR, hospedado no Railway.

## 🚀 Deploy no Railway

### Configurações Aplicadas

- **Inicialização Lazy**: Processadores são inicializados apenas quando necessário
- **Health Check**: Timeout aumentado para 600s
- **Workers**: 1 worker para evitar problemas de memória
- **Timeout**: 600s para processamento de arquivos grandes
- **GPU**: Desabilitado (Railway não suporta GPU)
- **Redis**: Desabilitado para evitar erros de conexão

### Arquivos Principais

- `api_server.py` - Servidor Flask principal
- `medical_ocr.py` - Processador PaddleOCR
- `config.py` - Configurações do sistema
- `utils/image_processor.py` - Pré-processamento de imagens
- `Dockerfile` - Container Docker
- `railway.toml` - Configuração do Railway
- `.env` - Variáveis de ambiente

## 🔧 Endpoints da API

### Health Check
```
GET /health
```
Verifica status do serviço e componentes.

### Informações da API
```
GET /info
```
Retorna informações sobre a API e recursos disponíveis.

### Processamento OCR
```
POST /ocr
Headers: Authorization: Bearer paddleocr-key-2024
Body: multipart/form-data com campo 'file'
```

### Teste Simples
```
GET /test
```
Endpoint de teste para verificar se o servidor está respondendo.

## 🐛 Troubleshooting

### Problema: Servidor não inicia (SIGTERM)

**Sintomas:**
- Logs mostram "Termination signal detected"
- Erro de timeout no health check
- Conexão resetada (ERR_CONNECTION_RESET)

**Soluções Aplicadas:**
1. **Inicialização Lazy**: Processadores não são inicializados no boot
2. **Timeout aumentado**: Health check com 600s
3. **Workers reduzidos**: Apenas 1 worker
4. **Pré-download de modelos**: Modelos baixados durante build

### Problema: Erro de memória

**Sintomas:**
- Processo morto sem aviso
- Out of Memory (OOM)

**Soluções:**
1. Usar apenas 1 worker
2. Inicialização lazy dos processadores
3. Limpeza de memória após processamento

### Problema: Timeout no processamento

**Sintomas:**
- Requisições que demoram muito
- Timeout 504

**Soluções:**
1. Timeout aumentado para 600s
2. Processamento otimizado de PDFs
3. Limite de tamanho de arquivo (10MB)

## 📊 Monitoramento

### Logs Importantes

```bash
# Inicialização do servidor
"Servidor iniciado - processadores serão inicializados sob demanda"

# Primeira requisição OCR
"OCR processor não inicializado, inicializando agora..."
"Processadores inicializados com sucesso!"

# Processamento normal
"Iniciando processamento OCR"
"OCR concluído"
```

### URLs de Monitoramento

- Health Check: `https://ocr.essencialab.app/health`
- Info da API: `https://ocr.essencialab.app/info`
- Teste: `https://ocr.essencialab.app/test`

## 🔄 Deploy

### Automático (Recomendado)
1. Commit e push das alterações
2. Railway detecta mudanças e faz deploy automático
3. Monitorar logs durante deploy

### Manual
```bash
# Executar script de verificação
chmod +x deploy.sh
./deploy.sh

# Fazer commit e push
git add .
git commit -m "fix: otimizações para Railway"
git push origin main
```

## 📝 Configurações de Ambiente

### Variáveis Críticas

```env
# API
PADDLEOCR_API_KEY=paddleocr-key-2024
HOST=0.0.0.0
PORT=8080  # Definido pelo Railway

# Performance
WORKERS=1
TIMEOUT=600
MAX_FILE_SIZE=10485760

# PaddleOCR
ENABLE_GPU=false
PADDLE_OCR_LANG=pt
PADDLEOCR_HOME=/tmp/.paddleocr

# Diretórios
TEMP_DIR=/tmp/temp
UPLOAD_DIR=/tmp/uploads
LOG_FILE=/tmp/paddleocr.log
```

## 🧪 Teste Local

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar servidor
python api_server.py

# Testar endpoint
curl http://localhost:5000/health
```

## 📋 Checklist de Deploy

- [ ] Dockerfile otimizado
- [ ] railway.toml configurado
- [ ] .env com variáveis corretas
- [ ] Inicialização lazy implementada
- [ ] Health check timeout aumentado
- [ ] Workers reduzidos para 1
- [ ] Modelos pré-baixados no build
- [ ] Logs estruturados configurados
- [ ] CORS configurado para EssenciaLab
- [ ] Tratamento de erros implementado

## 🔗 Links Úteis

- [Railway Docs](https://docs.railway.app/)
- [PaddleOCR Docs](https://github.com/PaddlePaddle/PaddleOCR)
- [Flask Docs](https://flask.palletsprojects.com/)
- [Gunicorn Docs](https://gunicorn.org/)

## 📞 Suporte

Em caso de problemas:

1. Verificar logs do Railway
2. Testar endpoints de health check
3. Verificar configurações de ambiente
4. Consultar este README para troubleshooting
