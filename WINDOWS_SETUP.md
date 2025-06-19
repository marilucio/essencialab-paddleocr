# 🪟 Setup PaddleOCR no Windows

## ⚠️ Pré-requisitos

### 1. Iniciar Docker Desktop
O Docker Desktop precisa estar rodando antes de executar os comandos.

**Passos:**
1. Abra o Docker Desktop manualmente (ícone na área de trabalho ou menu iniciar)
2. Aguarde até aparecer "Docker Desktop is running" na bandeja do sistema
3. Verifique se está funcionando: `docker --version`

### 2. Verificar se Docker está rodando
```powershell
docker info
```
Se aparecer erro "cannot connect", o Docker Desktop não está rodando.

## 🚀 Deploy Manual (Windows)

### Passo 1: Preparar Ambiente
```powershell
# Navegar para o diretório
cd paddleocr-service

# Verificar se arquivos existem
ls

# Copiar configurações (se não existir .env)
copy .env.example .env
```

### Passo 2: Criar Diretórios
```powershell
# Criar diretórios necessários
mkdir logs -ErrorAction SilentlyContinue
mkdir temp -ErrorAction SilentlyContinue  
mkdir uploads -ErrorAction SilentlyContinue
```

### Passo 3: Build Docker
```powershell
# Fazer build das imagens
docker-compose build

# Se der erro de "version obsolete", ignore o warning
```

### Passo 4: Iniciar Serviços
```powershell
# Iniciar todos os serviços
docker-compose up -d

# Verificar se subiram
docker-compose ps
```

### Passo 5: Verificar Funcionamento
```powershell
# Aguardar 30 segundos para inicialização

# Testar health check
curl http://localhost:8000/health

# Ou no navegador: http://localhost:8000/health
```

## 🧪 Teste da API

### Teste Básico
```powershell
# Ver informações da API
curl http://localhost:8000/info

# Testar OCR (precisa de arquivo de imagem)
curl -X POST http://localhost:8000/ocr -H "Authorization: Bearer paddleocr-key-2024" -F "file=@caminho\para\exame.jpg"
```

## 📊 Monitoramento

### Ver Logs
```powershell
# Logs de todos os serviços
docker-compose logs

# Logs apenas da API
docker-compose logs paddleocr-api

# Logs em tempo real
docker-compose logs -f paddleocr-api
```

### Status dos Containers
```powershell
# Ver status
docker-compose ps

# Ver recursos utilizados
docker stats
```

## 🐛 Troubleshooting Windows

### Problema: Docker não conecta
**Solução:**
1. Abrir Docker Desktop manualmente
2. Aguardar inicialização completa
3. Tentar novamente

### Problema: Porta 8000 ocupada
**Solução:**
```powershell
# Ver o que está usando a porta
netstat -ano | findstr :8000

# Matar processo se necessário
taskkill /PID <PID_NUMBER> /F
```

### Problema: Erro de permissão
**Solução:**
1. Executar PowerShell como Administrador
2. Ou adicionar usuário ao grupo docker-users

### Problema: Build falha
**Solução:**
```powershell
# Limpar cache do Docker
docker system prune -f

# Rebuild sem cache
docker-compose build --no-cache
```

## 🔄 Comandos Úteis Windows

### Parar Serviços
```powershell
docker-compose down
```

### Reiniciar Serviços
```powershell
docker-compose restart
```

### Limpar Tudo
```powershell
# Parar e remover containers
docker-compose down -v

# Limpar imagens não utilizadas
docker system prune -f
```

### Ver API Key
```powershell
# Ver chave configurada
type .env | findstr PADDLEOCR_API_KEY
```

## ✅ Verificação Final

Após o deploy, verifique:

1. **Docker Desktop rodando** ✅
2. **Containers ativos**: `docker-compose ps` ✅
3. **API respondendo**: http://localhost:8000/health ✅
4. **Redis funcionando**: `docker-compose exec redis redis-cli ping` ✅

## 🔗 Integração com EssenciaLab

### Configurar no projeto principal
Adicione no `.env` do projeto principal:
```
PADDLEOCR_API_ENDPOINT=http://localhost:8000/ocr
PADDLEOCR_API_KEY=paddleocr-key-2024
```

### Testar no Frontend
1. Abra o EssenciaLab
2. Vá para ExamUploader
3. Faça upload de um exame
4. Verifique se dados são extraídos

## 📞 Suporte

Se tiver problemas:

1. **Verificar Docker Desktop** está rodando
2. **Ver logs**: `docker-compose logs paddleocr-api`
3. **Reiniciar**: `docker-compose restart`
4. **Rebuild**: `docker-compose build --no-cache`

---

**🎯 Objetivo**: Ter a API PaddleOCR rodando em http://localhost:8000 e integrando com o EssenciaLab para extrair dados reais de exames médicos.
