# Deploy PaddleOCR no Railway

## Problemas Identificados e Soluções

### 1. Erro de CORS
**Problema**: O servidor estava retornando erro de CORS ao receber requisições do frontend.

**Solução**: Corrigido o tratamento de CORS no `api_server.py`:
- Adicionado handler para requisições OPTIONS (preflight)
- Configurado headers CORS adequados
- Adicionado `Access-Control-Max-Age` para cache de preflight

### 2. API Key Incompatível
**Problema**: A API key no servidor (.env) era diferente da configurada no cliente.

**Solução**: Sincronizada a API key:
- Servidor: `paddleocr-key-2024`
- Cliente: `paddleocr-key-2024`

### 3. Timeout de Conexão
**Problema**: O servidor pode estar com problemas de inicialização ou não estar rodando.

## Instruções para Deploy

### 1. Fazer Push das Alterações
```bash
cd essencialab-paddleocr
git add .
git commit -m "Fix CORS and API key issues"
git push origin main
```

### 2. Configurar Variáveis de Ambiente no Railway
No painel do Railway, configure as seguintes variáveis:

```
PADDLEOCR_API_KEY=paddleocr-key-2024
HOST=0.0.0.0
PORT=5000
DEBUG=false
WORKERS=1
ENABLE_GPU=false
PADDLE_OCR_LANG=pt
USE_ANGLE_CLS=true
USE_SPACE_CHAR=true
PADDLEOCR_HOME=/tmp/.paddleocr
MAX_FILE_SIZE=10485760
CONFIDENCE_THRESHOLD=0.7
TEMP_DIR=/tmp/temp
UPLOAD_DIR=/tmp/uploads
LOG_FILE=/tmp/paddleocr.log
```

### 3. Verificar Deployment
Após o deploy, teste os endpoints:

1. **Health Check**: `GET /health`
2. **CORS Preflight**: `OPTIONS /ocr`
3. **API Info**: `GET /info`

### 4. Testar Localmente (Opcional)
```bash
# Instalar dependências
pip install -r requirements.txt

# Executar servidor
python api_server.py
```

## Arquivos Modificados

1. **api_server.py**:
   - Corrigido tratamento de CORS com `@app.before_request` para OPTIONS
   - Melhorado `@app.after_request` com headers adequados
   - Implementada inicialização lazy dos processadores para evitar timeout
   - Removido teste de PaddleOCR no health check
   - Corrigidas todas as referências aos processadores lazy-loaded

2. **.env**:
   - Sincronizada API key: `PADDLEOCR_API_KEY=paddleocr-key-2024`
   - Configurações otimizadas para Railway

3. **config.py**:
   - Validação de configuração melhorada
   - Fallback para diretórios temporários

4. **Arquivos de teste criados**:
   - `test_cors.cjs` - Script Node.js para testar conectividade
   - `test_cors.py` - Script Python para testar conectividade

## Verificação de Funcionamento

Execute o teste de conectividade:
```bash
node test_cors.cjs
```

Ou teste manualmente:
```bash
curl -X OPTIONS \
  -H "Origin: https://essencialab.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type,Authorization,X-Requested-With" \
  https://essencialab-paddleocr-production.up.railway.app/ocr
```

## Logs de Debug

Para verificar logs no Railway:
1. Acesse o painel do Railway
2. Vá para a aba "Deployments"
3. Clique no deployment ativo
4. Verifique os logs para erros de inicialização

## Próximos Passos

1. Fazer o redeploy no Railway
2. Testar a extração de exames no frontend
3. Monitorar logs para possíveis erros
4. Otimizar performance se necessário
