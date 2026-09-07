param([string]$JonLan = "")

$ErrorActionPreference = "SilentlyContinue"

if ($JonLan -and -not (Get-NetFirewallRule -DisplayName 'Jon Wear OS' -ErrorAction SilentlyContinue)) {
    Start-Process powershell -Verb RunAs -WindowStyle Hidden -ArgumentList '-NoProfile -Command New-NetFirewallRule -DisplayName ''Jon Wear OS'' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8756 -Profile Any'
}

Get-NetTCPConnection -LocalPort 8756 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique |
    ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }

Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -match '^(python|pythonw|py|jon-backend)\.exe$' -and
        $_.CommandLine -match 'app\.main|run_backend'
    } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique |
    ForEach-Object {
        $prozess = Get-Process -Id $_ -ErrorAction SilentlyContinue
        if ($prozess -and $prozess.ProcessName -match '^(node|electron)$') {
            Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
        }
    }

$adresse = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias 'WLAN' -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty IPAddress
if (-not $adresse) {
    $adresse = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -like '192.168.*' -or $_.IPAddress -like '10.*' } |
        Select-Object -First 1 -ExpandProperty IPAddress
}
if ($adresse) { $adresse }
