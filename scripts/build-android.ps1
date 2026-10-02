param([string]$AndroidRoot = (Join-Path $PSScriptRoot '../android'), [switch]$PlayBundle)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$androidPath = (Resolve-Path -LiteralPath $AndroidRoot).Path
$gradleFile = Join-Path $androidPath 'device-app/build.gradle.kts'
if (-not (Test-Path -LiteralPath $gradleFile)) { throw 'Jon Android-Projekt fehlt.' }
Push-Location (Join-Path $projectRoot 'frontend')
try {
    & npm.cmd run build:mobile
    if ($LASTEXITCODE -ne 0) { throw 'Die mobile Oberfläche konnte nicht gebaut werden.' }
} finally { Pop-Location }
$assets = Join-Path $androidPath 'device-app/src/main/assets'
$webAssets = [IO.Path]::GetFullPath((Join-Path $assets 'device-web'))
if (-not $webAssets.StartsWith(([IO.Path]::GetFullPath($assets) + [IO.Path]::DirectorySeparatorChar), [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsicherer Asset-Pfad.' }
if (Test-Path -LiteralPath $webAssets) {
    if ((Get-Item -LiteralPath $webAssets).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Asset-Pfad darf kein Link sein.' }
    Remove-Item -LiteralPath $webAssets -Recurse -Force
}
New-Item -ItemType Directory -Path $webAssets -Force | Out-Null
Copy-Item -Path (Join-Path $projectRoot 'frontend/mobile-dist/*') -Destination $webAssets -Recurse -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'frontend/electron/pet3d.js') -Destination (Join-Path $assets 'mini-jon/pet3d.js') -Force
Push-Location $androidPath
try {
    $buildTasks = @(':device-app:assembleDirektRelease', ':device-app:testDirektDebugUnitTest')
    if ($PlayBundle) { $buildTasks += ':device-app:jonAusgabe' }
    & ./gradlew.bat @buildTasks --max-workers=2 --console=plain
    if ($LASTEXITCODE -ne 0) { throw 'Der Android-Build ist fehlgeschlagen.' }
} finally { Pop-Location }
$gradleText = Get-Content -LiteralPath $gradleFile -Raw
$version = [regex]::Match($gradleText, 'val jonVersion = "([^"]+)"').Groups[1].Value
$code = [int][regex]::Match($gradleText, 'val jonCode = (\d+)').Groups[1].Value
if (-not $version) { throw 'Android-Version fehlt.' }
$output = Join-Path $projectRoot ('artifacts/minijon-' + $version)
New-Item -ItemType Directory -Path $output -Force | Out-Null
$apkName = 'Jon-Geraet-' + $version + '.apk'
$apk = Join-Path $output $apkName
Copy-Item -LiteralPath (Join-Path $androidPath 'device-app/build/outputs/apk/direkt/release/device-app-direkt-release.apk') -Destination $apk -Force
$sha = (Get-FileHash -LiteralPath $apk -Algorithm SHA256).Hash.ToLowerInvariant()
$manifest = @{ version = $version; code = $code; apk = $apkName; sha256 = $sha; groesse = (Get-Item -LiteralPath $apk).Length }
$manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'jon-geraet.json') -Encoding utf8
$checksum = $sha + '  ' + $apkName
if ($PlayBundle) {
    $aabName = 'Jon-Geraet-' + $version + '-play.aab'
    $aab = Join-Path $output $aabName
    Copy-Item -LiteralPath (Join-Path $androidPath ('device-app/ausgabe/' + $aabName)) -Destination $aab -Force
    $checksum += "`n" + (Get-FileHash -LiteralPath $aab -Algorithm SHA256).Hash.ToLowerInvariant() + '  ' + $aabName
}
$checksum | Set-Content -LiteralPath (Join-Path $output 'SHA256SUMS.txt') -Encoding utf8
Write-Output ('Fertig: ' + $apk)
