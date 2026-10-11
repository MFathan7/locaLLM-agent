# ==============================================================================
#  ✦  locaLLM Installer for Windows  ✦
#  Autonomous Local AI Platform powered by Ollama and OpenAI-compatible engines
# ==============================================================================

[CmdletBinding()]
param (
    [Alias("r")]
    [switch]$Reinstall,

    [Alias("s")]
    [switch]$SkipGlobal,

    [Alias("h")]
    [switch]$Help
)

$ErrorActionPreference = "Stop"

if ($Help) {
    Write-Host @"
Usage: .\install.ps1 [OPTIONS]
       .\install.bat [OPTIONS]

Options:
  -Reinstall, -r    Recreate .venv virtual environment from scratch
  -SkipGlobal, -s   Skip creating global runner in %USERPROFILE%\.locallm\bin
  -Help, -h         Show this help message
"@
    exit 0
}

# --- Styling & Colors ---
function Log-Step($msg) {
    Write-Host "`n==> " -ForegroundColor Cyan -NoNewline
    Write-Host $msg -ForegroundColor White
}

function Log-Sub($msg) {
    Write-Host "  • " -ForegroundColor DarkGray -NoNewline
    Write-Host $msg
}

function Log-Success($msg) {
    Write-Host "  [OK] " -ForegroundColor Green -NoNewline
    Write-Host $msg -ForegroundColor Green
}

function Log-Warning($msg) {
    Write-Host "  [WARN] " -ForegroundColor Yellow -NoNewline
    Write-Host $msg -ForegroundColor Yellow
}

function Log-Error($msg) {
    Write-Host "  [ERROR] " -ForegroundColor Red -NoNewline
    Write-Host $msg -ForegroundColor Red
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ScriptDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$GlobalBinDir = Join-Path $env:USERPROFILE ".locallm\bin"

# --- Header Banner ---
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "                      *  locaLLM INSTALLER (Windows)  *                        " -ForegroundColor Cyan
Write-Host "                  Autonomous Local AI Platform Setup                            " -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

# --- 1. Detect Operating System & Architecture ---
Log-Step "Detecting Operating System & Architecture..."
$osInfo = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
$caption = if ($osInfo) { $osInfo.Caption } else { "Microsoft Windows" }
$arch = if ([Environment]::Is64BitOperatingSystem) { "64-bit" } else { "32-bit" }
Log-Success "Operating System: $caption [$arch]"

# --- 2. Find and Validate Python (>= 3.9) ---
Log-Step "Checking Python 3 environment..."

function Find-PythonExecutable {
    # Check py launcher
    $pyCmd = Get-Command "py" -ErrorAction SilentlyContinue
    if ($pyCmd) {
        try {
            $ver = & py -3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'); sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $ver) {
                return @{ Command = "py"; Args = @("-3"); Version = $ver.Trim() }
            }
        } catch {}
    }

    # Check python in PATH
    $pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        try {
            $ver = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'); sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $ver) {
                return @{ Command = "python"; Args = @(); Version = $ver.Trim() }
            }
        } catch {}
    }

    # Search common Windows Python paths
    $candidateDirs = @(
        "$env:LOCALAPPDATA\Programs\Python\Python3*",
        "C:\Program Files\Python3*",
        "C:\Python3*"
    )
    foreach ($cand in (Get-Item $candidateDirs -ErrorAction SilentlyContinue | Sort-Object Name -Descending)) {
        $pExe = Join-Path $cand.FullName "python.exe"
        if (Test-Path $pExe) {
            try {
                $ver = & $pExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'); sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>$null
                if ($LASTEXITCODE -eq 0 -and $ver) {
                    return @{ Command = $pExe; Args = @(); Version = $ver.Trim() }
                }
            } catch {}
        }
    }

    return $null
}

$pyInfo = Find-PythonExecutable

if (-not $pyInfo) {
    Log-Error "Python 3.9 or higher is required but was not found."
    Write-Host ""
    Write-Host "Recommended installation options for Windows:" -ForegroundColor White
    Write-Host "  1. Using winget:   winget install Python.Python.3.12" -ForegroundColor Cyan
    Write-Host "  2. Direct download: https://www.python.org/downloads/windows/" -ForegroundColor Cyan
    Write-Host "  Note: Ensure 'Add python.exe to PATH' is checked during installation." -ForegroundColor Yellow
    exit 1
}

Log-Success "Found Python ($($pyInfo.Command)): v$($pyInfo.Version)"

# --- 3. Virtual Environment Setup ---
Log-Step "Setting up virtual environment in .venv..."

if ($Reinstall -and (Test-Path $VenvDir)) {
    Log-Sub "Removing existing virtual environment (-Reinstall requested)..."
    Remove-Item -Recurse -Force $VenvDir
}

if (-not (Test-Path $VenvPython)) {
    Log-Sub "Creating virtual environment at $VenvDir..."
    if ($pyInfo.Args.Count -gt 0) {
        & $pyInfo.Command @($pyInfo.Args) -m venv $VenvDir
    } else {
        & $pyInfo.Command -m venv $VenvDir
    }

    if (-not (Test-Path $VenvPython)) {
        Log-Error "Failed to create virtual environment."
        exit 1
    }
    Log-Success "Virtual environment created."
} else {
    Log-Success "Existing virtual environment found."
}

# Check pip inside venv
Log-Sub "Verifying pip inside virtual environment..."
$pipVer = & $VenvPython -m pip --version 2>$null
if (-not $pipVer) {
    Log-Sub "Bootstrapping pip via ensurepip..."
    & $VenvPython -m ensurepip --upgrade 2>$null
}

$pipVerOutput = & $VenvPython -m pip --version 2>$null
if (-not $pipVerOutput) {
    Log-Error "pip could not be initialized inside the virtual environment."
    exit 1
}
Log-Success "pip is ready ($pipVerOutput)"

# --- 4. Install Dependencies & locaLLM Package ---
Log-Step "Installing project dependencies and registering editable package..."

Log-Sub "Upgrading build tools (pip, setuptools, wheel)..."
& $VenvPython -m pip install --upgrade pip setuptools wheel --quiet

$reqFile = Join-Path $ScriptDir "requirements.txt"
if (Test-Path $reqFile) {
    Log-Sub "Installing requirements from requirements.txt..."
    & $VenvPython -m pip install -r $reqFile --quiet
    Log-Success "Dependencies installed successfully."
}

Log-Sub "Installing locaLLM in editable mode ('pip install -e .')..."
& $VenvPython -m pip install -e $ScriptDir --quiet
Log-Success "locaLLM package registered."

# --- 5. Setup Local Runner Scripts ---
Log-Step "Configuring repository runner scripts..."

# Update locallm.cmd
$localCmdPath = Join-Path $ScriptDir "locallm.cmd"
$cmdContent = @"
@echo off
if exist "%~dp0.venv\Scripts\locallm.exe" (
    "%~dp0.venv\Scripts\locallm.exe" %*
) else if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m locallm %*
) else (
    py -m locallm %* 2>nul || python -m locallm %*
)
"@
Set-Content -Path $localCmdPath -Value $cmdContent -Encoding ASCII

# Update locaLLM.bat
$localBatPath = Join-Path $ScriptDir "locaLLM.bat"
Copy-Item -Path $localCmdPath -Destination $localBatPath -Force

# Create locallm.ps1 local runner
$localPs1Path = Join-Path $ScriptDir "locallm.ps1"
$ps1Content = @"
`$scriptDir = Split-Path -Parent `$MyInvocation.MyCommand.Path
`$venvExe = Join-Path `$scriptDir ".venv\Scripts\locallm.exe"
`$venvPy = Join-Path `$scriptDir ".venv\Scripts\python.exe"

if (Test-Path `$venvExe) {
    & `$venvExe @args
} elseif (Test-Path `$venvPy) {
    & `$venvPy -m locallm @args
} else {
    Write-Error "Error: locaLLM virtual environment not found. Please run .\install.ps1 first."
}
"@
Set-Content -Path $localPs1Path -Value $ps1Content -Encoding UTF8
Log-Success "Local runners updated: .\locallm.cmd, .\locaLLM.bat, and .\locallm.ps1"

# --- 6. Setup Global CLI Command in %USERPROFILE%\.locallm\bin ---
if (-not $SkipGlobal) {
    Log-Step "Configuring global CLI command..."

    if (-not (Test-Path $GlobalBinDir)) {
        New-Item -ItemType Directory -Path $GlobalBinDir -Force | Out-Null
    }

    # Global cmd wrapper pointing to repository venv
    $globalCmd = Join-Path $GlobalBinDir "locallm.cmd"
    $globalBat = Join-Path $GlobalBinDir "locaLLM.cmd"
    $globalCmdContent = @"
@echo off
if exist "$VenvDir\Scripts\locallm.exe" (
    "$VenvDir\Scripts\locallm.exe" %*
) else (
    "$VenvDir\Scripts\python.exe" -m locallm %*
)
"@
    Set-Content -Path $globalCmd -Value $globalCmdContent -Encoding ASCII
    Set-Content -Path $globalBat -Value $globalCmdContent -Encoding ASCII

    # Global ps1 wrapper
    $globalPs1 = Join-Path $GlobalBinDir "locallm.ps1"
    $globalPs1Content = @"
`$venvExe = "$VenvDir\Scripts\locallm.exe"
`$venvPy = "$VenvDir\Scripts\python.exe"

if (Test-Path `$venvExe) {
    & `$venvExe @args
} elseif (Test-Path `$venvPy) {
    & `$venvPy -m locallm @args
} else {
    Write-Error "Error: locaLLM environment not found at $VenvDir"
}
"@
    Set-Content -Path $globalPs1 -Value $globalPs1Content -Encoding UTF8

    # Check User PATH
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notlike "*$GlobalBinDir*") {
        Log-Sub "Adding $GlobalBinDir to User PATH environment variable..."
        try {
            $newPath = "$GlobalBinDir;$userPath"
            [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
            $env:Path = "$GlobalBinDir;$env:Path"
            Log-Success "Added $GlobalBinDir to User PATH."
        } catch {
            Log-Warning "Could not update User PATH automatically. You can add '$GlobalBinDir' manually."
        }
    } else {
        Log-Success "$GlobalBinDir is already in User PATH."
    }

    Log-Success "Global CLI launcher installed to $GlobalBinDir\locallm.cmd"
}

# --- 7. Check Ollama & Backend Status ---
Log-Step "Checking local Ollama service status..."

$ollamaCmd = Get-Command "ollama" -ErrorAction SilentlyContinue
if ($ollamaCmd) {
    Log-Success "Ollama binary found: $($ollamaCmd.Source)"
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 2 -ErrorAction Stop
        Log-Success "Ollama daemon is ONLINE and responding at http://127.0.0.1:11434"
    } catch {
        Log-Warning "Ollama daemon is currently stopped or unreachable at http://127.0.0.1:11434"
        Write-Host "  Start Ollama from the Windows Start menu or run: ollama serve" -ForegroundColor DarkGray
    }
} else {
    Log-Warning "Ollama was not detected on this system."
    Write-Host "  To install Ollama on Windows, download installer from: https://ollama.com/download/windows" -ForegroundColor DarkGray
}

# --- 8. Complete & Quickstart Guide ---
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Green
Write-Host "      *  locaLLM installation completed successfully on Windows!  *             " -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Quick Ways to Run locaLLM:" -ForegroundColor White
Write-Host "  1. Global command:    locallm   or   locaLLM (open a new terminal to reload PATH)" -ForegroundColor Cyan
Write-Host "  2. Repository runner: .\locallm.cmd   or   .\locallm.ps1" -ForegroundColor Cyan
Write-Host "  3. Manual activation: .venv\Scripts\Activate.ps1 && locallm" -ForegroundColor Cyan
Write-Host ""
Write-Host "Essential Commands:" -ForegroundColor White
Write-Host "  locallm               Launch interactive menu with live telemetry banner" -ForegroundColor Cyan
Write-Host "  locallm top           Open real-time GPU VRAM HUD and hardware monitor" -ForegroundColor Cyan
Write-Host "  locallm chat          Interactive conversational chat with auto-routing" -ForegroundColor Cyan
Write-Host "  locallm agent         Autonomous ReAct coding agent" -ForegroundColor Cyan
Write-Host "  locallm serve         Start OpenAI-compatible HTTP API gateway (:8080)" -ForegroundColor Cyan
Write-Host "  locallm --help        Display full CLI guide and documentation" -ForegroundColor Cyan
Write-Host ""
