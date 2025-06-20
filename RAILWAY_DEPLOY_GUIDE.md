# 🚂 Guia de Deploy no Railway - PaddleOCR Service

## 📋 Resumo das Correções Implementadas

### ✅ Problemas Identificados e Corrigidos:

1. **Inconsistência no comando de inicialização**
   - ❌ Antes: `railway.toml` usava `python api_server.py` mas `Dockerfile` configurado para `gunicorn`
   - ✅ Agora: Ambos alinhados para usar `gunicorn --bind 0.0.0.0:5000 api_server:app`

2. **Variáveis de ambiente inconsistentes**
   - ❌ Antes: `config.py` esperava `API_KEY` mas `.env.example` usava `PADDLEOCR_API_KEY`
   - ✅ Agora: `config.py` aceita ambas as variáveis com fallback

3. **Versões de dependências incompatíveis**
   - ❌ Antes: Versões flexíveis que podiam causar conflitos
   - ✅ Agora: Versões específicas testadas e compatíveis

4. **Diagnóstico melhorado**
   - ✅ Logs mais detalhados durante build e runtime
   - ✅ Verificação de PaddleOCR na inicialização

## 🚀 Passos para Deploy

### 1. Preparar o Projeto

```bash
# Navegar para o diretório
cd essencialab-paddleocr

# Verificar arquivos essenciais
ls -la
# Deve mostrar: Dockerfile, railway.toml, requirements.txt, .env, api_server.py
```

### 2. Deploy no Railway

#### Opção A: Via CLI do Railway
```bash
# Instalar Railway CLI (se não tiver)
npm install -g @railway/cli

# Login
railway login

# Deploy
railway up
```

#### Opção B: Via GitHub (Recomendado)
1. Fazer commit das alterações:
```bash
git add .
git commit -m "fix: corrigir deploy PaddleOCR no Railway"
git push
```

2. No Railway Dashboard:
   - Conectar repositório GitHub
   - Selecionar branch
   - Railway detectará automaticamente o Dockerfile

### 3. Configurar Variáveis de Ambiente no Railway

No Railway Dashboard, adicionar as seguintes variáveis:

```bash
# Essenciais
PADDLEOCR_API_KEY=paddleocr-essencialab-2024-secure
ENABLE_GPU=false
PADDLE_OCR_LANG=pt

# Opcionais (já têm defaults)
CONFIDENCE_THRESHOLD=0.7
MAX_FILE_SIZE=10485760
LOG_LEVEL=INFO
```

**⚠️ Importante**: Railway injeta automaticamente a variável `PORT`, não definir manualmente.

### 4. Verificar Deploy

#### Health Check
```bash
curl https://seu-app.railway.app/health
```

Resposta esperada:
```json
{
  "status": "healthy",
  "components": {
    "paddleocr": "healthy",
    "redis": "unhealthy",
    "image_processor": "healthy",
    "medical_parser": "healthy"
  }
}
```

#### Teste da API
```bash
curl -X POST https://seu-app.railway.app/ocr \
  -H "Authorization: Bearer paddleocr-essencialab-2024-secure" \
  -F "file=@exemplo.jpg"
```

### 5. Monitoramento

#### Ver Logs em Tempo Real
No Railway Dashboard:
- Ir para o projeto
- Aba "Deployments"
- Clicar no deployment ativo
- Ver logs em tempo real

#### Comandos de Debug
```bash
# Via Railway CLI
railway logs

# Verificar status
railway status
```

## 🔧 Configurações Específicas do Railway

### railway.toml
```toml
[build]
builder = "DOCKERFILE"

[deploy]
startCommand = "gunicorn --bind 0.0.0.0:5000 api_server:app"
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

### Dockerfile Otimizado
- ✅ Dependências do sistema para OpenCV
- ✅ Versões específicas do Python packages
- ✅ Diagnóstico detalhado durante build
- ✅ Logs de inicialização melhorados
- ✅ Diretórios temporários em `/tmp`

### Variáveis de Ambiente
- ✅ Fallback para diferentes nomes de variáveis
- ✅ Defaults seguros para produção
- ✅ Configuração otimizada para Railway

## 🐛 Troubleshooting

### Problema: "PaddleOCR não disponível"
**Solução**: Verificar logs de build para ver se instalação foi bem-sucedida
```bash
railway logs --deployment [deployment-id]
```

### Problema: Timeout na inicialização
**Solução**: Aumentar timeout no railway.toml
```toml
[deploy]
healthcheckTimeout = 300  # 5 minutos
```

### Problema: Erro de memória
**Solução**: Usar plano com mais RAM no Railway ou otimizar workers
```bash
# No .env
WORKERS=1  # Reduzir workers se necessário
```

### Problema: Redis não disponível
**Solução**: Adicionar Redis service no Railway ou desabilitar cache
```python
# Em config.py, o código já trata Redis opcional
redis_client = None  # Cache desabilitado
```

## 📊 Métricas de Sucesso

### ✅ Deploy Bem-sucedido Quando:
1. **Health check retorna 200**
2. **Logs mostram "PaddleOCR disponível!"**
3. **API responde em `/info`**
4. **OCR processa imagens de teste**

### 📈 Performance Esperada:
- **Tempo de build**: 5-10 minutos
- **Tempo de inicialização**: 30-60 segundos
- **Processamento OCR**: 2-10 segundos por imagem
- **Uso de memória**: 500MB-1GB

## 🔗 Integração com EssenciaLab

### Atualizar Frontend
No projeto principal, atualizar variáveis:

```bash
# .env do EssenciaLab
PADDLE_OCR_ENDPOINT=https://seu-app.railway.app/ocr
PADDLE_OCR_API_KEY=paddleocr-essencialab-2024-secure
```

### Netlify Functions
Atualizar `netlify/functions/paddleocr-processor.js`:
```javascript
const PADDLE_OCR_ENDPOINT = process.env.PADDLE_OCR_ENDPOINT || 'https://seu-app.railway.app/ocr';
const PADDLE_OCR_API_KEY = process.env.PADDLE_OCR_API_KEY;
```

## 🎉 Próximos Passos

1. **Testar com exames reais** do EssenciaLab
2. **Monitorar performance** e ajustar se necessário
3. **Configurar alertas** para falhas
4. **Implementar backup** de configurações
5. **Documentar API** para equipe

---

**🌿 EssenciaLab - OCR médico funcionando na nuvem!**

## 📞 Suporte

Se encontrar problemas:
1. Verificar logs no Railway Dashboard
2. Testar health check endpoint
3. Validar variáveis de ambiente
4. Consultar este guia para troubleshooting
