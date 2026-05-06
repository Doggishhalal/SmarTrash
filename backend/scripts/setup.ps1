# SmarTrash Complete Setup & Installation
# PowerShell Script für Windows

Write-Host "================================" -ForegroundColor Cyan
Write-Host "  SmarTrash Setup & Installation" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
Write-Host "[1/5] Prüfe Python Installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host $pythonVersion -ForegroundColor Green
    Write-Host "✅ Python OK" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python nicht installiert!" -ForegroundColor Red
    Write-Host "Bitte Python 3.8+ von python.org installieren" -ForegroundColor Red
    pause
    exit 1
}
Write-Host ""

# 2. Create Virtual Environment (optional but recommended)
Write-Host "[2/5] Virtual Environment (optional)" -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    Write-Host "Erstelle venv (kann 1-2 Min dauern)..."
    python -m venv venv
    if ($LASTEXITCODE -eq 0) {
        & .\venv\Scripts\Activate.ps1
        Write-Host "✅ venv erstellt & aktiviert" -ForegroundColor Green
    } else {
        Write-Host "⚠️  venv Erstellung fehlgeschlagen, fahre ohne venv fort" -ForegroundColor Yellow
    }
} else {
    Write-Host "venv existiert bereits, aktiviere..."
    try {
        & .\venv\Scripts\Activate.ps1
        Write-Host "✅ venv aktiviert" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  venv Aktivierung fehlgeschlagen, fahre ohne venv fort" -ForegroundColor Yellow
    }
}
Write-Host ""

# 3. Install Dependencies
Write-Host "[3/5] Installiere Python Dependencies (kann ~2 Min dauern)..." -ForegroundColor Yellow
Write-Host "Bitte warten..." -ForegroundColor Gray
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Dependencies installiert" -ForegroundColor Green
} else {
    Write-Host "⚠️  Einige Dependencies könnten fehlgeschlagen sein" -ForegroundColor Yellow
    Write-Host "Versuche nochmal mit Verbose-Output..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Installation fehlgeschlagen" -ForegroundColor Red
        Write-Host "Bitte manuell ausführen: pip install -r requirements.txt" -ForegroundColor Yellow
        pause
        exit 1
    }
}
Write-Host ""

# 4. Check YOLOX Model
Write-Host "[4/5] Prüfe YOLOX Model..." -ForegroundColor Yellow
$modelDir = "C:\models"
$modelFile = "$modelDir\yolox_s.pth"

if (-not (Test-Path $modelDir)) {
    New-Item -ItemType Directory -Path $modelDir -Force | Out-Null
    Write-Host "📁 Ordner erstellt: $modelDir" -ForegroundColor Cyan
}

if (Test-Path $modelFile) {
    $fileSize = (Get-Item $modelFile).Length / 1MB
    Write-Host "✅ YOLOX Model existiert: $modelFile ($([math]::Round($fileSize, 1)) MB)" -ForegroundColor Green
} else {
    Write-Host "⚠️  Model nicht gefunden: $modelFile" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Download URL (540 MB):" -ForegroundColor Cyan
    Write-Host "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1_weights/yolox_s.pth" -ForegroundColor White
    Write-Host ""
    Write-Host "Speichern unter: $modelFile" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Server startet trotzdem (für API-Tests ohne Model)" -ForegroundColor Gray
}
Write-Host ""

# 5. Validate Setup
Write-Host "[5/5] Validiere Installation..." -ForegroundColor Yellow
$validationResult = python -c "
import sys
try:
    import fastapi
    import torch
    import cv2
    import numpy
    print('✅ FastAPI OK')
    print('✅ PyTorch OK')
    print('✅ OpenCV OK')
    print('✅ NumPy OK')
    sys.exit(0)
except ImportError as e:
    print(f'❌ Fehler: {e}')
    sys.exit(1)
" 2>&1

Write-Host $validationResult

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Installation erfolgreich!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Einige Module fehlen möglicherweise" -ForegroundColor Yellow
    Write-Host "Versuche trotzdem zu starten..." -ForegroundColor Gray
}
Write-Host ""

# Start Server
Clear-Host
Write-Host "================================" -ForegroundColor Green
Write-Host "  Setup fertig! Starte Server..." -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""

Write-Host "🚀 Starte SmarTrash Server..." -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 Dashboard: http://localhost:8000/dashboard" -ForegroundColor Yellow
Write-Host "📡 API:       http://localhost:8000" -ForegroundColor Yellow
Write-Host "📖 Docs:      http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Drücke Ctrl+C um Server zu stoppen" -ForegroundColor Gray
Write-Host ""
Write-Host "Warte auf Server-Start..." -ForegroundColor Gray
Write-Host ""

python main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "================================" -ForegroundColor Red
    Write-Host "ERROR beim Starten des Servers!" -ForegroundColor Red
    Write-Host "================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Mögliche Ursachen:" -ForegroundColor Yellow
    Write-Host "1. Dependencies fehlen (pip install -r requirements.txt)" -ForegroundColor White
    Write-Host "2. Port 8000 bereits belegt" -ForegroundColor White
    Write-Host "3. Python-Pfad falsch" -ForegroundColor White
    Write-Host ""
    pause
    exit 1
}
