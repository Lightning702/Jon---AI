& {
    $ErrorActionPreference = 'Stop'
    $altFortschritt = $ProgressPreference
    $ProgressPreference = 'SilentlyContinue'
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    } catch {}

    function Zeile([string]$Text, [string]$Farbe = 'Gray') { Write-Host $Text -ForegroundColor $Farbe }

    Write-Host ''
    Write-Host '     ██╗ ██████╗ ███╗   ██╗' -ForegroundColor Blue
    Write-Host '     ██║██╔═══██╗████╗  ██║' -ForegroundColor Blue
    Write-Host '     ██║██║   ██║██╔██╗ ██║' -ForegroundColor Cyan
    Write-Host '██   ██║██║   ██║██║╚██╗██║' -ForegroundColor Cyan
    Write-Host '╚█████╔╝╚██████╔╝██║ ╚████║' -ForegroundColor Yellow
    Write-Host ' ╚════╝  ╚═════╝ ╚═╝  ╚═══╝' -ForegroundColor Yellow
    Write-Host '  H A R N E S S  ·  von FelWorks' -ForegroundColor Yellow
    Write-Host ''

    $quelle = if ($env:JON_HARNESS_URL) { $env:JON_HARNESS_URL } else { 'https://github.com/Lightning702/Jon---AI/releases/latest/download/jon-harness.exe' }
    $summen = 'https://github.com/Lightning702/Jon---AI/releases/latest/download/SHA256SUMS.txt'
    $basis = if ($env:JON_HARNESS_ZIEL) { $env:JON_HARNESS_ZIEL } else { Join-Path $env:LOCALAPPDATA 'Jon' }
    $ziel = Join-Path $basis 'Harness'
    $bin = Join-Path $basis 'bin'
    $exe = Join-Path $ziel 'jon-harness.exe'
    $neu = Join-Path $ziel 'jon-harness.neu'

    try {
        New-Item -ItemType Directory -Force -Path $ziel, $bin | Out-Null
        Zeile '  Lade Jon Harness herunter …'
        Invoke-WebRequest -Uri $quelle -OutFile $neu -UseBasicParsing -Headers @{ 'User-Agent' = 'Jon-Harness-Installer' }
        $datei = Get-Item $neu
        if ($datei.Length -lt 1000000) { throw "Die heruntergeladene Datei ist zu klein ($($datei.Length) Bytes)." }
        $kopf = [byte[]]::new(2)
        $strom = [IO.File]::OpenRead($neu)
        try { [void]$strom.Read($kopf, 0, 2) } finally { $strom.Dispose() }
        if ($kopf[0] -ne 0x4D -or $kopf[1] -ne 0x5A) { throw 'Die heruntergeladene Datei ist kein Windows-Programm.' }
        $erwartet = ''
        try {
            $liste = (Invoke-WebRequest -Uri $summen -UseBasicParsing -Headers @{ 'User-Agent' = 'Jon-Harness-Installer' }).Content
            if ($liste -is [byte[]]) { $liste = [Text.Encoding]::UTF8.GetString($liste) }
            $erwartet = [string]($liste -split "`n" | Where-Object { $_ -match 'jon-harness\.exe' } | ForEach-Object { ($_ -split '\s+')[0] } | Select-Object -First 1)
        } catch {}
        if ($erwartet) {
            $ist = (Get-FileHash -Algorithm SHA256 -Path $neu).Hash.ToLower()
            if ($ist -ne $erwartet.Trim().ToLower()) { throw 'Die Prüfsumme stimmt nicht – Download abgebrochen.' }
            Zeile '  ✓ Prüfsumme stimmt' 'Green'
        }
        if (Test-Path $exe) {
            $alt = "$exe.alt"
            Remove-Item $alt -Force -ErrorAction SilentlyContinue
            Move-Item $exe $alt -Force
        }
        Move-Item $neu $exe -Force
        Remove-Item "$exe.alt" -Force -ErrorAction SilentlyContinue
        Unblock-File -Path $exe -ErrorAction SilentlyContinue
        Zeile '  ✓ Installiert nach' 'Green'
        Zeile "    $exe" 'DarkGray'

        $weiche = "if exist `"%LOCALAPPDATA%\Jon\Harness\jon-harness.exe`" (`r`n  `"%LOCALAPPDATA%\Jon\Harness\jon-harness.exe`" %*`r`n  exit /b`r`n)`r`n"
        foreach ($name in @('jon.cmd', 'jon-harness.cmd', 'jon-code.cmd')) {
            $shim = Join-Path $bin $name
            $vorhanden = if (Test-Path $shim) { [IO.File]::ReadAllText($shim) } else { '' }
            if ($vorhanden -match 'Harness\\jon-harness\.exe') { continue }
            if ($vorhanden -match '(?i)cli') {
                $inhalt = $vorhanden -replace '^@echo off\r?\n', ("@echo off`r`n" + $weiche)
            } else {
                $inhalt = "@echo off`r`n`"%LOCALAPPDATA%\Jon\Harness\jon-harness.exe`" %*`r`n"
            }
            [IO.File]::WriteAllText($shim, $inhalt, [Text.Encoding]::ASCII)
        }

        $pfad = [Environment]::GetEnvironmentVariable('Path', 'User')
        $teile = @($pfad -split ';' | Where-Object { $_ })
        if (-not $env:JON_HARNESS_ZIEL -and -not ($teile | Where-Object { $_.TrimEnd('\') -ieq $bin.TrimEnd('\') })) {
            [Environment]::SetEnvironmentVariable('Path', (@($bin) + $teile) -join ';', 'User')
            Zeile '  ✓ Befehl „jon“ zum PATH hinzugefügt' 'Green'
        }
        if (-not (($env:Path -split ';') | Where-Object { $_.TrimEnd('\') -ieq $bin.TrimEnd('\') })) {
            $env:Path = "$bin;$env:Path"
        }

        $jonDa = (Test-Path (Join-Path $basis 'data')) -or (Test-Path (Join-Path $env:LOCALAPPDATA 'Programs\Jon\Jon.exe'))
        $jonLaeuft = $false
        try {
            $antwort = Invoke-WebRequest -Uri 'http://127.0.0.1:8756/api/health' -UseBasicParsing -TimeoutSec 2
            $jonLaeuft = $antwort.StatusCode -eq 200
        } catch {}
        Write-Host ''
        if ($jonLaeuft) {
            Zeile '  ● Jon läuft auf diesem PC – das Terminal verbindet sich automatisch.' 'Green'
        } elseif ($jonDa) {
            Zeile '  ● Jon ist installiert – sobald Jon läuft, verbindet sich das Terminal automatisch.' 'Green'
        } else {
            Zeile '  ○ Jon ist nicht installiert – kein Problem: Das Terminal läuft eigenständig.' 'Yellow'
            Zeile '    Kostenlos über FelWorks, eigene Schlüssel jederzeit mit /api.' 'DarkGray'
        }
        Write-Host ''
        Write-Host '  Fertig! Starte jetzt mit:  ' -NoNewline -ForegroundColor Gray
        Write-Host 'jon' -ForegroundColor Yellow
        Zeile '  (in einem neuen Fenster oder direkt hier)' 'DarkGray'
        Write-Host ''
    } catch {
        Remove-Item $neu -Force -ErrorAction SilentlyContinue
        Write-Host ''
        Zeile "  ✕ Die Installation hat nicht geklappt: $($_.Exception.Message)" 'Red'
        Zeile '  Prüfe die Internetverbindung und versuche es noch einmal. Hilfe: https://getjon.info' 'DarkGray'
        Write-Host ''
    } finally {
        $ProgressPreference = $altFortschritt
    }
}
