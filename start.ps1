# PowerShell script to start Ollama and Django server for FAIX Chatbot
# Usage: .\start.ps1

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "FAIX Chatbot - Starting Server" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
$venvPath = Join-Path $PSScriptRoot "venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please create it first: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/3] Virtual environment found" -ForegroundColor Green
Write-Host ""

# Function to check if Ollama is running
function Test-OllamaRunning {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        return $true
    }
    catch {
        return $false
    }
}

# Check if Ollama is already running
Write-Host "[2/3] Checking Ollama service..." -ForegroundColor Yellow
$ollamaRunning = Test-OllamaRunning

if (-not $ollamaRunning) {
    Write-Host "Ollama is not running. Starting Ollama..." -ForegroundColor Yellow
    
    # Check if Ollama is installed
    $ollamaExists = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $ollamaExists) {
        Write-Host "ERROR: Ollama not found in PATH" -ForegroundColor Red
        Write-Host "Please install Ollama from https://ollama.ai" -ForegroundColor Yellow
        Write-Host "Continuing without Ollama (LLM features will be disabled)" -ForegroundColor Yellow
        $ollamaProcess = $null
    }
    else {
        # Start Ollama in a new window
        Write-Host "Starting Ollama server in new window..." -ForegroundColor Yellow
        $ollamaProcess = Start-Process -FilePath "ollama" -ArgumentList "serve" -PassThru -WindowStyle Normal
        
        # Wait for Ollama to start
        $maxWait = 30
        $waited = 0
        Write-Host "Waiting for Ollama to start" -NoNewline -ForegroundColor Yellow
        
        while (-not (Test-OllamaRunning) -and $waited -lt $maxWait) {
            Start-Sleep -Seconds 2
            $waited += 2
            Write-Host "." -NoNewline -ForegroundColor Yellow
        }
        Write-Host ""
        
        if (Test-OllamaRunning) {
            Write-Host "✓ Ollama is running" -ForegroundColor Green
        }
        else {
            Write-Host "⚠ Warning: Ollama may not have started properly" -ForegroundColor Yellow
        }
    }
}
else {
    Write-Host "✓ Ollama is already running" -ForegroundColor Green
    $ollamaProcess = $null
}

Write-Host ""

# Start Django server
Write-Host "[3/3] Starting Django development server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Server starting at http://0.0.0.0:8000" -ForegroundColor Cyan
Write-Host "Access from this device: http://localhost:8000 or http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Access from other devices: http://<your-ip-address>:8000" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Track if cleanup has been done
$script:cleanupDone = $false

# Function to cleanup on exit
function Cleanup {
    param([string]$Message = $null)
    
    # Prevent duplicate cleanup
    if ($script:cleanupDone) {
        return
    }
    
    # Only cleanup if we started Ollama
    if ($ollamaProcess -and -not $ollamaProcess.HasExited) {
        if ($Message) {
            Write-Host ""
            Write-Host $Message -ForegroundColor Yellow
        }
        Write-Host "Stopping Ollama..." -ForegroundColor Yellow
        try {
            Stop-Process -Id $ollamaProcess.Id -Force -ErrorAction SilentlyContinue
        }
        catch {
            # Ignore errors when stopping process
        }
        Write-Host "Done!" -ForegroundColor Green
        $script:cleanupDone = $true
    }
}

try {
    # Activate virtual environment and run Django server
    & $venvPython manage.py runserver 0.0.0.0:8000
}
catch {
    # Ctrl+C will throw PipelineStoppedException or OperationCanceledException
    if ($_.Exception.Message -match "PipelineStoppedException|OperationCanceledException") {
        Cleanup "Shutting down (Ctrl+C pressed)..."
        exit 0
    }
    else {
        Write-Host ""
        Write-Host "Error occurred: $_" -ForegroundColor Red
        Cleanup "Shutting down due to error..."
        exit 1
    }
}
finally {
    # Ensure cleanup runs (only if we started Ollama and haven't cleaned up yet)
    Cleanup
}
