param(
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $Root "quant_lab.pid"
$LogFile = Join-Path $Root "quant_lab.log"
$ErrFile = Join-Path $Root "quant_lab.err.log"
$Port = 8091
$Url = "http://127.0.0.1:$Port"

function Test-Health {
    try {
        $response = Invoke-WebRequest -Uri "$Url/api/health" -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Get-AppProcess {
    if (Test-Path -LiteralPath $PidFile) {
        $raw = (Get-Content -LiteralPath $PidFile -Raw).Trim()
        if ($raw -match '^\d+$') {
            $process = Get-Process -Id ([int]$raw) -ErrorAction SilentlyContinue
            if ($process) {
                try {
                    $info = Get-CimInstance Win32_Process -Filter "ProcessId=$($process.Id)"
                    if ($info.CommandLine -match "quant_lab\.main:app") {
                        return $process
                    }
                } catch {}
            }
        }
    }
    try {
        $candidates = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
            Where-Object { $_.CommandLine -match "quant_lab\.main:app" -and $_.CommandLine -match "uvicorn" }
        if ($candidates) {
            return Get-Process -Id ($candidates | Select-Object -First 1).ProcessId -ErrorAction SilentlyContinue
        }
    } catch {}
    return $null
}

function Stop-App {
    $process = Get-AppProcess
    if (-not $process) {
        Write-Host "Quant Trading Lab no esta corriendo."
        Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
        return
    }
    Write-Host "Deteniendo Quant Trading Lab (PID $($process.Id))..."
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 600
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    Write-Host "Detenido."
}

function Start-App {
    $existing = Get-AppProcess
    if ($existing) {
        if (Test-Health) {
            Write-Host "Quant Trading Lab ya esta activo en $Url"
            if (-not $env:QUANT_LAB_NO_BROWSER) { Start-Process $Url }
            return
        }
        Stop-App
    }

    $listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($listening) {
        throw "El puerto $Port esta ocupado por otro proceso. Liberalo antes de iniciar Quant Trading Lab."
    }

    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $python) {
        $python = (Get-Command py -ErrorAction SilentlyContinue).Source
    }
    if (-not $python) {
        throw "No se encontro Python en PATH."
    }

    $tmp = Join-Path $Root ".tmp"
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    $env:TEMP = $tmp
    $env:TMP = $tmp

    Write-Host "Iniciando Quant Trading Lab en $Url ..."
    $arguments = @(
        "-m", "uvicorn", "quant_lab.main:app",
        "--host", "127.0.0.1",
        "--port", "$Port"
    )
    $process = Start-Process -FilePath $python -ArgumentList $arguments `
        -WorkingDirectory $Root -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $LogFile -RedirectStandardError $ErrFile
    $process.Id | Set-Content -LiteralPath $PidFile -Encoding ASCII

    for ($i = 0; $i -lt 80; $i++) {
        Start-Sleep -Milliseconds 350
        if (Test-Health) {
            Write-Host "Listo. Motor local activo."
            if (-not $env:QUANT_LAB_NO_BROWSER) { Start-Process $Url }
            return
        }
        if ($process.HasExited) {
            $tail = ""
            if (Test-Path -LiteralPath $ErrFile) {
                $tail = (Get-Content -LiteralPath $ErrFile -Tail 20) -join [Environment]::NewLine
            }
            throw "El servidor termino antes de responder.`n$tail"
        }
    }
    throw "El servidor no respondio en 28 segundos. Revisa quant_lab.log y quant_lab.err.log."
}

switch ($Action) {
    "start" { Start-App }
    "stop" { Stop-App }
    "restart" { Stop-App; Start-Sleep -Milliseconds 500; Start-App }
    "status" {
        if (Test-Health) { Write-Host "Activo en $Url" } else { Write-Host "Detenido." }
    }
}
