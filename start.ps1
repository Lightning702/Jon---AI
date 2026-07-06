param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

if (-not (Test-Path (Join-Path $root ".env"))) {
    Copy-Item (Join-Path $root ".env.example") (Join-Path $root ".env")
    Write-Host "[.env erstellt] Bitte API-Keys in .env eintragen." -ForegroundColor Yellow
}

Write-Host "Starte Jon-Backend ..." -ForegroundColor Cyan
$backend = Start-Process -FilePath "python" -ArgumentList "-m", "app.main" `
    -WorkingDirectory (Join-Path $root "backend") -PassThru

Start-Sleep -Seconds 2

Push-Location (Join-Path $root "frontend")
try {
    if ($Build) {
        npm run build
        npm run start
    }
    else {
        npm run dev
    }
}
finally {
    Pop-Location
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force -Confirm:$false
    }
}
