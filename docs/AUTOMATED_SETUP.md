# Instalação Automatizada - ENEM Questions RAG

## Visão Geral

Este documento descreve a instalação completa automatizada do ambiente de desenvolvimento usando Chocolatey para Windows 10/11.

## Pré-requisitos do Sistema

### Hardware Recomendado
- **CPU**: AMD Ryzen 5 1600x ou superior
- **GPU**: NVIDIA RTX 3060 12GB VRAM ou superior  
- **RAM**: 16GB DDR4 mínimo
- **Armazenamento**: 200GB SSD disponível
- **OS**: Windows 10/11

## Comandos Chocolatey para Instalação Completa

### Ferramentas Base de Desenvolvimento
```powershell
choco install git -y
choco install vscode -y
choco install powershell-core -y
choco install windows-terminal -y
choco install 7zip -y
choco install curl -y
choco install wget -y
```

### Runtime e SDKs
```powershell
choco install dotnet-9.0-sdk -y
choco install python311 -y
choco install nodejs-lts -y
choco install vcredist-all -y
```

### Containerização e Orquestração
```powershell
choco install docker-desktop -y
choco install docker-compose -y
choco install kubernetes-cli -y
```

### Drivers GPU NVIDIA
```powershell
choco install nvidia-display-driver -y
choco install cuda -y
```

### Ferramentas de Database
```powershell
choco install postgresql -y
choco install pgadmin4 -y
choco install redis -y
```

### Editores e IDEs Auxiliares
```powershell
choco install notepadplusplus -y
choco install postman -y
choco install insomnia-rest-api-client -y
```

### Ferramentas de Análise e Monitoramento
```powershell
choco install cpu-z -y
choco install gpu-z -y
choco install hwinfo -y
choco install procexp -y
```

### Utilitários de Sistema
```powershell
choco install ccleaner -y
choco install windirstat -y
choco install everything -y
choco install bulk-crap-uninstaller -y
```

## Script de Instalação Completa

### install-dev-environment.ps1

```powershell
param(
    [switch]$SkipOptional,
    [switch]$GPUOnly,
    [switch]$Minimal
)

Write-Host "=== ENEM RAG Development Environment Setup ===" -ForegroundColor Green

if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Instalando Chocolatey..." -ForegroundColor Yellow
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
}

choco upgrade chocolatey -y

Write-Host "Instalando ferramentas base..." -ForegroundColor Cyan
$baseTools = @(
    'git', 'vscode', 'powershell-core', 'windows-terminal',
    'dotnet-9.0-sdk', 'python311', 'docker-desktop', 
    'postgresql', '7zip', 'curl'
)

foreach ($tool in $baseTools) {
    Write-Host "Instalando $tool..." -ForegroundColor White
    choco install $tool -y
}

if (!$Minimal) {
    Write-Host "Instalando drivers GPU e CUDA..." -ForegroundColor Cyan
    choco install nvidia-display-driver -y
    choco install cuda -y
}

if (!$SkipOptional -and !$Minimal) {
    Write-Host "Instalando ferramentas opcionais..." -ForegroundColor Cyan
    $optionalTools = @(
        'nodejs-lts', 'redis', 'pgadmin4', 'postman', 
        'notepadplusplus', 'cpu-z', 'gpu-z'
    )
    
    foreach ($tool in $optionalTools) {
        choco install $tool -y
    }
}

Write-Host "=== Instalação Concluída ===" -ForegroundColor Green
```

### setup-python-environment.ps1

```powershell
Write-Host "Configurando ambiente Python..." -ForegroundColor Green

python -m pip install --upgrade pip

Write-Host "Instalando PyTorch com suporte CUDA..." -ForegroundColor Cyan
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

Write-Host "Instalando dependências do projeto..." -ForegroundColor Cyan
pip install sentence-transformers transformers numpy
pip install psycopg2-binary sqlalchemy pgvector
pip install fastapi uvicorn[standard] python-dotenv
pip install tqdm pytest pdfplumber PyPDF2 pillow
pip install easyocr ollama

Write-Host "Ambiente Python configurado!" -ForegroundColor Green
```

### setup-docker-services.ps1

```powershell
Write-Host "Configurando serviços Docker..." -ForegroundColor Green

if (!(docker info 2>$null)) {
    Write-Host "Docker não está rodando!" -ForegroundColor Red
    exit 1
}

Set-Location $PSScriptRoot

Write-Host "Iniciando PostgreSQL e Redis..." -ForegroundColor Cyan
docker-compose up -d postgres redis

Start-Sleep -Seconds 30

Write-Host "Configurando Ollama com GPU..." -ForegroundColor Cyan
docker run -d --gpus all --name ollama-gpu -v ollama:/root/.ollama -p 11434:11434 ollama/ollama

Write-Host "Baixando modelos LLM..." -ForegroundColor Cyan
docker exec ollama-gpu ollama pull llama3.1:8b
docker exec ollama-gpu ollama pull llama3.2-vision

Write-Host "Serviços configurados!" -ForegroundColor Green
```

### validate-installation.ps1

```powershell
Write-Host "=== Validação da Instalação ===" -ForegroundColor Green

$tools = @{
    'Git' = 'git --version'
    'Python' = 'python --version'
    '.NET' = 'dotnet --version'
    'Docker' = 'docker --version'
}

foreach ($tool in $tools.Keys) {
    try {
        $version = Invoke-Expression $tools[$tool]
        Write-Host "$tool`: OK" -ForegroundColor Green
    }
    catch {
        Write-Host "$tool`: ERRO" -ForegroundColor Red
    }
}

Write-Host "Testando CUDA..." -ForegroundColor Cyan
python -c "import torch; print('CUDA:', torch.cuda.is_available())"

Write-Host "Testando serviços Docker..." -ForegroundColor Cyan
docker ps --filter "name=postgres" --format "table {{.Names}}\t{{.Status}}"
docker ps --filter "name=ollama" --format "table {{.Names}}\t{{.Status}}"
```

## Uso dos Scripts

### Instalação Completa
```powershell
.\install-dev-environment.ps1
.\setup-python-environment.ps1
.\setup-docker-services.ps1
.\validate-installation.ps1
```

### Instalação Mínima
```powershell
.\install-dev-environment.ps1 -Minimal
```

## Troubleshooting

### Problemas Comuns

1. **Política de Execução**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

2. **Docker não inicia**: Verificar WSL2 e Hyper-V habilitados

3. **CUDA não detectado**: Reinstalar drivers NVIDIA e reiniciar

4. **Chocolatey não encontrado**: Fechar/reabrir terminal

## Notas Importantes

- Reiniciar após instalação de drivers GPU
- Executar PowerShell como Administrador
- Verificar 200GB SSD livres
- Conexão internet estável necessária

---

**Compatibilidade**: Windows 10/11, RTX 3060+, 16GB RAM+
