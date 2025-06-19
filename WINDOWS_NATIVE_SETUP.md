# 🪟 Setup PaddleOCR Nativo no Windows (SEM DOCKER)

## 🎯 Alternativas de Deploy sem Docker

Como o Docker não está funcionando no seu Windows, aqui estão **3 alternativas eficazes**:

### 🥇 **OPÇÃO 1: Deploy no Railway (RECOMENDADO)**
- ✅ **Gratuito** até 500 horas/mês
- ✅ **Deploy automático** via GitHub
- ✅ **URL pública** automática
- ✅ **Sem configuração complexa**

### 🥈 **OPÇÃO 2: Python Local + ngrok**
- ✅ **Roda direto no Windows**
- ✅ **Sem Docker necessário**
- ✅ **Controle total**
- ⚠️ **Requer Python 3.9+**

### 🥉 **OPÇÃO 3: Netlify Functions Melhorada**
- ✅ **Integração direta**
- ✅ **Sem servidor externo**
- ⚠️ **OCR mais simples (Tesseract)**

---

## 🚀 OPÇÃO 1: Deploy no Railway

### Passo 1: Preparar para Railway
```powershell
# Criar arquivo railway.json
cd paddleocr-service
```

### Passo 2: Configurar Railway
1. Acesse: https://railway.app
2. Conecte sua conta GitHub
3. Clique "Deploy from GitHub repo"
4. Selecione seu repositório
5. Escolha a pasta `paddleocr-service`

### Passo 3: Configurar Variáveis
No Railway Dashboard:
```
PADDLEOCR_API_KEY=paddleocr-key-2024
PORT=8000
REDIS_URL=redis://localhost:6379
```

### Passo 4: Testar
```powershell
# Sua URL será algo como:
# https://paddleocr-service-production.up.railway.app

curl https://sua-url-railway.up.railway.app/health
```

---

## 🐍 OPÇÃO 2: Python Local + ngrok

### Passo 1: Instalar Python
```powershell
# Verificar se Python está instalado
python --version

# Se não tiver, baixar de: https://python.org
# Versão recomendada: Python 3.9 ou superior
```

### Passo 2: Criar Ambiente Virtual
```powershell
cd paddleocr-service

# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
venv\Scripts\activate

# Verificar ativação (deve aparecer (venv) no prompt)
```

### Passo 3: Instalar Dependências
```powershell
# Instalar dependências (pode demorar 10-15 minutos)
pip install -r requirements.txt

# Se der erro, instalar uma por vez:
pip install paddlepaddle==2.5.2
pip install paddleocr==2.7.3
pip install flask==2.3.3
pip install flask-cors==4.0.0
pip install opencv-python==4.8.1.78
pip install pillow==10.0.1
pip install numpy==1.24.4
```

### Passo 4: Configurar Ambiente
```powershell
# Copiar configurações
copy .env.example .env

# Editar .env (opcional)
notepad .env
```

### Passo 5: Instalar Redis (Opcional)
```powershell
# Opção A: Redis via Chocolatey
choco install redis-64

# Opção B: Usar Redis online (recomendado)
# Editar .env e colocar:
# REDIS_URL=redis://localhost:6379
# ou usar Redis Cloud gratuito
```

### Passo 6: Executar Servidor
```powershell
# Executar servidor Flask
python api_server.py

# Deve aparecer:
# * Running on http://127.0.0.1:8000
```

### Passo 7: Expor com ngrok
```powershell
# Instalar ngrok
# Baixar de: https://ngrok.com/download

# Em outro terminal:
ngrok http 8000

# Copiar URL pública (ex: https://abc123.ngrok.io)
```

### Passo 8: Testar
```powershell
# Testar localmente
curl http://localhost:8000/health

# Testar via ngrok
curl https://sua-url-ngrok.ngrok.io/health
```

---

## 🌐 OPÇÃO 3: Netlify Functions Melhorada

### Passo 1: Melhorar Função Netlify
Vamos melhorar a função existente para usar OCR mais robusto:

```javascript
// netlify/functions/process-exam-ocr-enhanced.js
const Tesseract = require('tesseract.js');
const sharp = require('sharp');

exports.handler = async (event, context) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  try {
    // Processar imagem com sharp para melhor qualidade
    const imageBuffer = Buffer.from(event.body, 'base64');
    const processedImage = await sharp(imageBuffer)
      .resize(2000, null, { withoutEnlargement: true })
      .sharpen()
      .normalize()
      .toBuffer();

    // OCR com Tesseract otimizado
    const { data: { text } } = await Tesseract.recognize(processedImage, 'por', {
      logger: m => console.log(m),
      tessedit_pageseg_mode: Tesseract.PSM.AUTO,
      tessedit_ocr_engine_mode: Tesseract.OEM.LSTM_ONLY,
    });

    // Parser médico melhorado
    const extractedData = parseExamData(text);

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        success: true,
        data: extractedData,
        raw_text: text
      })
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: error.message })
    };
  }
};

function parseExamData(text) {
  // Implementar parser médico aqui
  // Similar ao medical_parser.py
  return {
    parameters: [],
    patient_info: {},
    exam_type: 'unknown'
  };
}
```

---

## 🎯 RECOMENDAÇÃO FINAL

### Para Deploy Rápido: **OPÇÃO 1 (Railway)**
- Mais fácil e confiável
- URL pública automática
- Sem configuração local

### Para Desenvolvimento: **OPÇÃO 2 (Python Local)**
- Controle total
- Debugging fácil
- Performance máxima

### Para Simplicidade: **OPÇÃO 3 (Netlify)**
- Integração direta
- Sem servidor externo
- OCR básico mas funcional

---

## 🔧 Scripts de Automação

### Script para Opção 2 (Python Local)
```powershell
# scripts/setup-windows-native.ps1
Write-Host "🐍 Configurando PaddleOCR nativo no Windows..."

# Verificar Python
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python não encontrado. Instale Python 3.9+ primeiro."
    exit 1
}

# Criar ambiente virtual
python -m venv venv
venv\Scripts\activate

# Instalar dependências
Write-Host "📦 Instalando dependências (pode demorar)..."
pip install -r requirements.txt

# Configurar ambiente
if (!(Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "✅ Arquivo .env criado"
}

# Executar servidor
Write-Host "🚀 Iniciando servidor..."
python api_server.py
```

### Script para Testar
```powershell
# scripts/test-windows-native.ps1
Write-Host "🧪 Testando API PaddleOCR..."

# Testar health
$health = Invoke-RestMethod -Uri "http://localhost:8000/health"
Write-Host "Health: $($health.status)"

# Testar info
$info = Invoke-RestMethod -Uri "http://localhost:8000/info"
Write-Host "API Info: $($info.name)"

Write-Host "✅ Testes concluídos!"
```

---

## 📞 Próximos Passos

1. **Escolha uma opção** (recomendo Railway)
2. **Execute os passos** da opção escolhida
3. **Teste a API** com curl ou Postman
4. **Configure no EssenciaLab** a nova URL
5. **Teste integração** completa

### Para Railway:
- URL será: `https://paddleocr-service-production.up.railway.app`

### Para Python Local:
- URL será: `https://sua-url-ngrok.ngrok.io`

### Para Netlify:
- URL será: `https://seu-site.netlify.app/.netlify/functions/process-exam-ocr-enhanced`

---

**🎉 Problema do Docker resolvido! Escolha a opção que preferir e vamos colocar o OCR funcionando!**
