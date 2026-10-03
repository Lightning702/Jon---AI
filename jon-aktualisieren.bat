@echo off
set "JON_BAT=%~f0" & title Jon aktualisieren & powershell -NoProfile -ExecutionPolicy Bypass -Command "iex ((Get-Content -LiteralPath $env:JON_BAT | Select-Object -Skip 2) -join [char]10)" & exit /b
$ErrorActionPreference = 'Continue'
$ordner = Split-Path -Parent $env:JON_BAT
Set-Location -LiteralPath $ordner
function Zeige([string]$text, [string]$farbe = 'Gray') { Write-Host $text -ForegroundColor $farbe }
function G { $ausgabe = (& git @args 2>&1 | Out-String).Trim(); [pscustomobject]@{Code = $LASTEXITCODE; Text = $ausgabe} }
function Liste([string]$text) { @($text -split "`r?`n" | Where-Object { $_.Trim() } | ForEach-Object { $_.Trim() }) }
function Aktualisieren {
  $ersetzen = $false
  Zeige ''
  Zeige '  Jon aktualisieren - es wird nichts geloescht' 'Yellow'
  Zeige "  Ordner: $ordner"
  Zeige ''
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Zeige '  Git wurde nicht gefunden. Bitte Git von https://git-scm.com installieren.' 'Red'; return }
  if (-not (Test-Path -LiteralPath (Join-Path $ordner '.git'))) { Zeige '  Dieser Ordner ist kein Git-Ordner. Lege die Datei in deinen Jon-Ordner, dort wo start-jon.bat liegt.' 'Red'; return }
  if ((Test-Path (Join-Path $ordner '.git\MERGE_HEAD')) -or (Test-Path (Join-Path $ordner '.git\rebase-merge')) -or (Test-Path (Join-Path $ordner '.git\rebase-apply'))) { Zeige '  In diesem Ordner laeuft noch ein unfertiges Zusammenfuehren. Bitte zuerst abschliessen.' 'Red'; return }
  $remotes = Liste (G remote).Text
  if (-not $remotes.Count) { Zeige '  Kein Git-Server eingetragen.' 'Red'; return }
  $remote = if ($remotes -contains 'origin') { 'origin' } else { $remotes[0] }
  Zeige "  Lade die neueste Version von $remote ..."
  $abruf = G fetch $remote main
  if ($abruf.Code -ne 0) { Zeige "  Laden fehlgeschlagen: $($abruf.Text)" 'Red'; return }
  $neu = (G rev-parse FETCH_HEAD).Text
  $start = (G rev-parse HEAD).Text
  $basisAbfrage = G merge-base HEAD $neu
  $basis = if ($basisAbfrage.Code -eq 0) { $basisAbfrage.Text } else { 'HEAD' }
  if ($basis -eq $neu) { Zeige '  Jon ist schon auf dem neuesten Stand.' 'Green'; return }
  $kommend = Liste (G diff --name-only $basis $neu).Text
  $lokal = Liste (G diff --name-only HEAD).Text
  $eigene = Liste (G ls-files --others --exclude-standard).Text
  $selbst = 'jon-aktualisieren.bat'
  $konflikte = @($kommend | Where-Object { $_ -ne $selbst -and (($lokal -contains $_) -or ($eigene -contains $_)) })
  if ($konflikte.Count) {
    Zeige '  Die neue Version aendert Dateien, die du selbst bearbeitet hast:' 'Yellow'
    $konflikte | Select-Object -First 25 | ForEach-Object { Zeige "    $_" 'Yellow' }
    Zeige ''
    Zeige '  Es wurde NICHTS veraendert. Sichere oder committe diese Dateien und starte das Update erneut.' 'Yellow'
    return
  }
  if ((Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) -and (Get-NetTCPConnection -LocalPort 8756 -State Listen -ErrorAction SilentlyContinue)) { Zeige '  Hinweis: Jon laeuft gerade. Starte ihn nach dem Update neu.' 'Yellow' }
  $sicherung = 'sicherung-vor-update-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
  $null = G branch $sicherung HEAD
  Zeige "  Sicherungsstand angelegt: $sicherung"
  if ($lokal.Count) { Zeige "  Deine $($lokal.Count) lokal geaenderten Dateien bleiben unveraendert." }
  if ($eigene.Count) { Zeige "  Deine $($eigene.Count) eigenen Dateien bleiben unveraendert." }
  if (-not (G config user.email).Text) { $env:GIT_AUTHOR_NAME = 'Jon Update'; $env:GIT_AUTHOR_EMAIL = 'update@jon.local'; $env:GIT_COMMITTER_NAME = 'Jon Update'; $env:GIT_COMMITTER_EMAIL = 'update@jon.local' }
  $env:GIT_MERGE_AUTOEDIT = 'no'
  $vorher = Join-Path $ordner ($selbst + '.vorher')
  if (($kommend -contains $selbst) -and ($eigene -contains $selbst)) {
    $ersetzen = (G hash-object $selbst).Text -eq (G rev-parse "$($neu):$selbst").Text
    if ($ersetzen) { Move-Item -LiteralPath (Join-Path $ordner $selbst) -Destination $vorher -Force }
    else { Rename-Item -LiteralPath (Join-Path $ordner $selbst) -NewName 'jon-aktualisieren.alt.bat' -Force; Zeige '  Deine bisherige Update-Datei heisst jetzt jon-aktualisieren.alt.bat.' }
  }
  $zusammen = G merge --no-edit $neu
  if ($zusammen.Code -ne 0) {
    $null = G merge --abort
    if ($ersetzen -and (Test-Path -LiteralPath $vorher)) { Move-Item -LiteralPath $vorher -Destination (Join-Path $ordner $selbst) -Force }
    Zeige "  Zusammenfuehren nicht moeglich, dein Stand ist unveraendert: $($zusammen.Text)" 'Red'
    return
  }
  if ($ersetzen -and (Test-Path -LiteralPath $vorher)) { Remove-Item -LiteralPath $vorher -Force }
  $dateien = Liste (G diff --name-only $start HEAD).Text
  Zeige "  $($dateien.Count) Dateien aktualisiert." 'Green'
  function Python { if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 @args } else { & python @args } }
  if ($dateien | Where-Object { $_ -like 'backend/requirements*' }) {
    Zeige '  Installiere neue Backend-Abhaengigkeiten ...'
    Python -m pip install --disable-pip-version-check -r (Join-Path $ordner 'backend\requirements.txt')
  }
  $frontend = Join-Path $ordner 'frontend'
  if ((Test-Path $frontend) -and ((-not (Test-Path (Join-Path $frontend 'node_modules'))) -or ($dateien | Where-Object { $_ -like 'frontend/package*.json' }))) {
    if (Get-Command npm -ErrorAction SilentlyContinue) {
      Zeige '  Installiere Frontend-Abhaengigkeiten ...'
      Push-Location $frontend
      & npm install --no-audit --no-fund
      Pop-Location
    }
  }
  $version = Select-String -LiteralPath (Join-Path $ordner 'backend\app\core\config.py') -Pattern 'app_version: str = "([^"]+)"' | Select-Object -First 1
  Zeige ''
  if ($version) { Zeige "  Fertig! Jon ist jetzt auf Version $($version.Matches[0].Groups[1].Value)." 'Green' } else { Zeige '  Fertig!' 'Green' }
  Zeige '  Starte Jon jetzt mit start-jon.bat neu.' 'Green'
  Zeige "  Zurueck zum alten Stand jederzeit mit:  git reset --keep $sicherung"
  $stashes = Liste (G stash list).Text
  if ($stashes.Count) { Zeige "  Hinweis: Es liegen $($stashes.Count) aeltere Aenderungen im Git-Stash, vermutlich von frueheren Updates. Ansehen mit: git stash list" 'Yellow' }
}
Aktualisieren
Zeige ''
$null = Read-Host '  Enter druecken zum Schliessen'
