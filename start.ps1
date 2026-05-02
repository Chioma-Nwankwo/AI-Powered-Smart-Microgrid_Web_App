# Smart Microgrid Analytics - Quick Start Script
# Run this script to check prerequisites and start the application

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Smart Microgrid Analytics - Quick Start" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python 3\.(1[0-9]|[2-9][0-9])") {
    Write-Host "✓ $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "✗ Python 3.10+ required. Current: $pythonVersion" -ForegroundColor Red
    Write-Host "Please install Python 3.10 or higher from python.org" -ForegroundColor Yellow
    exit 1
}

# Check if virtual environment exists
Write-Host "`nChecking virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "✓ Virtual environment found" -ForegroundColor Green
    
    # Activate virtual environment
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & "venv\Scripts\Activate.ps1"
    Write-Host "✓ Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "✗ Virtual environment not found" -ForegroundColor Red
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    
    if ($?) {
        Write-Host "✓ Virtual environment created" -ForegroundColor Green
        & "venv\Scripts\Activate.ps1"
    } else {
        Write-Host "✗ Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
}

# Check if requirements are installed
Write-Host "`nChecking dependencies..." -ForegroundColor Yellow
$streamlitInstalled = pip list | Select-String "streamlit"
if ($streamlitInstalled) {
    Write-Host "✓ Dependencies appear to be installed" -ForegroundColor Green
} else {
    Write-Host "✗ Dependencies not found" -ForegroundColor Red
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
    
    if ($?) {
        Write-Host "✓ Dependencies installed successfully" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
}

# Check for .env file
Write-Host "`nChecking configuration..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "✓ .env file found" -ForegroundColor Green
} else {
    Write-Host "✗ .env file not found" -ForegroundColor Red
    if (Test-Path ".env.example") {
        Write-Host "Creating .env from template..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "✓ .env file created" -ForegroundColor Green
        Write-Host "⚠ Please edit .env file with your credentials before running" -ForegroundColor Yellow
    }
}

# Check PostgreSQL
Write-Host "`nChecking PostgreSQL..." -ForegroundColor Yellow
$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
if ($pgService) {
    if ($pgService.Status -eq "Running") {
        Write-Host "✓ PostgreSQL is running" -ForegroundColor Green
    } else {
        Write-Host "⚠ PostgreSQL is installed but not running" -ForegroundColor Yellow
        Write-Host "  Start it with: net start postgresql-x64-14" -ForegroundColor Gray
    }
} else {
    Write-Host "⚠ PostgreSQL not detected" -ForegroundColor Yellow
    Write-Host "  Install from: https://www.postgresql.org/download/windows/" -ForegroundColor Gray
}

# Check MongoDB
Write-Host "`nChecking MongoDB..." -ForegroundColor Yellow
$mongoService = Get-Service -Name "MongoDB" -ErrorAction SilentlyContinue
if ($mongoService) {
    if ($mongoService.Status -eq "Running") {
        Write-Host "✓ MongoDB is running" -ForegroundColor Green
    } else {
        Write-Host "⚠ MongoDB is installed but not running" -ForegroundColor Yellow
        Write-Host "  Start it with: net start MongoDB" -ForegroundColor Gray
    }
} else {
    Write-Host "⚠ MongoDB not detected" -ForegroundColor Yellow
    Write-Host "  Install from: https://www.mongodb.com/try/download/community" -ForegroundColor Gray
}

# Check if databases are initialized
Write-Host "`nChecking database initialization..." -ForegroundColor Yellow
Write-Host "If databases aren't initialized, run: python database/init_db.py" -ForegroundColor Gray

# Display summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Ensure PostgreSQL and MongoDB are running" -ForegroundColor White
Write-Host "2. Configure your .env file if needed" -ForegroundColor White
Write-Host "3. Initialize databases: python database/init_db.py" -ForegroundColor White
Write-Host "4. (Optional) Train ML models: python models/train_models.py" -ForegroundColor White
Write-Host "`n" -ForegroundColor White

# Ask if user wants to start the app
$response = Read-Host "Would you like to start the application now? (Y/N)"
if ($response -eq "Y" -or $response -eq "y") {
    Write-Host "`nStarting Smart Microgrid Analytics..." -ForegroundColor Cyan
    Write-Host "The application will open in your browser at http://localhost:8501" -ForegroundColor Gray
    Write-Host "Press Ctrl+C to stop the server`n" -ForegroundColor Gray
    
    # Start Streamlit
    streamlit run app.py
} else {
    Write-Host "`nTo start the application later, run:" -ForegroundColor Yellow
    Write-Host "  streamlit run app.py`n" -ForegroundColor White
}
