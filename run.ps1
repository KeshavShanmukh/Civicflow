param(
    [ValidateRange(0, 65535)]
    [int]$Port = 0
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m backend --host 127.0.0.1 --port $Port
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
