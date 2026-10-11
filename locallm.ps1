$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvExe = Join-Path $scriptDir ".venv\Scripts\locallm.exe"
$venvPy = Join-Path $scriptDir ".venv\Scripts\python.exe"

if (Test-Path $venvExe) {
    & $venvExe @args
} elseif (Test-Path $venvPy) {
    & $venvPy -m locallm @args
} else {
    Write-Error "Error: locaLLM virtual environment not found. Please run .\install.ps1 first."
}
