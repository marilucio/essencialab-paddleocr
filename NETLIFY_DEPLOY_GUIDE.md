# 🚀 Guia de Deploy PaddleOCR para Netlify

## 🎯 Estratégia de Deploy

Como o Docker não funciona no Windows, vamos fazer o deploy da API PaddleOCR em um serviço cloud e configurar o Netlify para usar essa API externa.

## 📋 Passo a Passo

### 1️⃣ Deploy da API PaddleOCR no Railway

#### Passo 1: Preparar o Repositório
```powershell
# Verificar se está no diretório correto
cd paddleocr-service

# Verificar arquivos necessários
ls
```

#### Passo 2: Fazer Deploy no Railway
1. Acesse: https://railway.app
2. Faça login com GitHub
3. Clique em "New Project"
4. Selecione "Deploy from GitHub repo"
5. Escolha seu repositório
6. Selecione a pasta `paddleocr-service`

#### Passo 3: Configurar Variáveis de Ambiente no Railway
No Railway Dashboard, adicione estas variáveis:
```
PADDLEOCR_API_KEY=paddleocr-key-2024
PORT=8000
REDIS_URL=redis://localhost:6379
```

#### Passo 4: Aguardar Deploy
- O Railway vai automaticamente detectar o Dockerfile
- O deploy pode levar 5-10 minutos
- Você receberá uma URL como: `https://paddleocr-service-production.up.railway.app`

### 2️⃣ Configurar Netlify para Usar a API Externa

#### Passo 1: Configurar Variáveis de Ambiente no Netlify
No painel do Netlify (Site settings > Environment variables):
```
PADDLE_OCR_ENDPOINT=https://sua-url-railway.up.railway.app/ocr
PADDLE_OCR_API_KEY=paddleocr-key-2024
```

#### Passo 2: A função `process-exam-ocr.js` já está configurada
A função existente já tem o código para usar a API PaddleOCR externa e fazer fallback para Tesseract se necessário.

### 3️⃣ Testar a Integração

#### Teste 1: Verificar API Railway
```powershell
# Testar health check
curl https://sua-url-railway.up.railway.app/health

# Testar info da API
curl https://sua-url-railway.up.railway.app/info
```

#### Teste 2: Testar Função Netlify
```powershell
# Testar função local (se necessário)
netlify dev

# Ou testar diretamente no site após deploy
```

## 🔧 Alternativa: Deploy no Render

Se o Railway não funcionar, use o Render:

### Passo 1: Deploy no Render
1. Acesse: https://render.com
2. Conecte GitHub
3. Clique "New Web Service"
4. Selecione seu repositório
5. Configure:
   - **Root Directory**: `paddleocr-service`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT api_server:app`

### Passo 2: Configurar Variáveis no Render
```
PADDLEOCR_API_KEY=paddleocr-key-2024
```

## 📝 Configuração Final

### Atualizar URL no Netlify
Depois que a API estiver rodando, atualize a variável no Netlify:
```
PADDLE_OCR_ENDPOINT=https://sua-url-do-servico.com/ocr
```

### Testar Integração Completa
1. Abra o EssenciaLab
2. Vá para o ExamUploader
3. Faça upload de um exame
4. Verifique se os dados são extraídos corretamente

## 🎉 Resultado Final

- ✅ API PaddleOCR rodando em serviço cloud
- ✅ Netlify Functions usando a API externa
- ✅ Fallback para Tesseract se API falhar
- ✅ Integração completa funcionando

## 🆘 Troubleshooting

### Problema: API não responde
```powershell
# Verificar logs no Railway/Render
# Verificar se variáveis estão configuradas
# Testar URL diretamente
```

### Problema: Netlify não encontra API
```powershell
# Verificar variáveis de ambiente no Netlify
# Verificar se URL está correta
# Verificar logs da função Netlify
```

## 📞 Próximos Passos

1. **Escolha o serviço** (Railway recomendado)
2. **Faça o deploy** seguindo os passos
3. **Configure as variáveis** no Netlify
4. **Teste a integração** completa
5. **Monitore o funcionamento**

---

**🌿 EssenciaLab - OCR de exames médicos funcionando sem Docker!**
