<#
.SYNOPSIS
    Jalankan pemindaian garak lokal terhadap chatbot RAG di 127.0.0.1:5000.

.DESCRIPTION
    Hanya menargetkan server Flask lokal (http://127.0.0.1:5000/api/chat) sesuai
    AGENTS.md Bagian 2. Memerlukan .venv-garak yang sudah terpasang dan server
    Flask + Ollama yang berjalan di mesin lokal.

.EXAMPLE
    .\garak\run_scan.ps1 -Mode baseline
    .\garak\run_scan.ps1 -Mode m1 -Generations 1
#>
[CmdletBinding()]
param(
    [ValidateSet("baseline", "m1")]
    [string]$Mode = "baseline",

    [string]$Probes = "promptinject.HijackLongPrompt,latentinjection.LatentWhois",

    [ValidateRange(1, 10)]
    [int]$Generations = 1
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$GarakExe = Join-Path $RepoRoot ".venv-garak\Scripts\garak.exe"
$ConfigPath = Join-Path $PSScriptRoot "rest_$Mode.json"
$ReportsDir = Join-Path $RepoRoot "logs\garak"

if (-not (Test-Path $GarakExe)) {
    throw "garak belum terpasang di .venv-garak. Jalankan setup di garak/README.md terlebih dahulu."
}

if (-not (Test-Path $ConfigPath)) {
    throw "File konfigurasi tidak ditemukan: $ConfigPath"
}

# Validasi wajib: target harus loopback 127.0.0.1 (AGENTS.md Bagian 2).
$Config = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$TargetUri = [string]$Config.rest.RestGenerator.uri
if ($TargetUri -notmatch '^http://127\.0\.0\.1:\d+/api/chat$') {
    throw "Ditolak: URI target ($TargetUri) bukan http://127.0.0.1:<port>/api/chat."
}

# Pastikan server Flask lokal aktif sebelum garak mulai mengirim probe.
$HealthUri = $TargetUri -replace '/api/chat$', '/api/options'
try {
    $null = Invoke-RestMethod -Uri $HealthUri -Method Get -TimeoutSec 5
} catch {
    throw "Server Flask lokal tidak dapat dijangkau di $HealthUri. Jalankan `flask --app app run --host 127.0.0.1 --port 5000`."
}

New-Item -ItemType Directory -Force -Path $ReportsDir | Out-Null
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Prefix = Join-Path $ReportsDir "garak-$Mode-$Timestamp"

Write-Host "Menjalankan garak (mode=$Mode, target=$TargetUri, probes=$Probes, generations=$Generations)..."
& $GarakExe `
    --model_type rest `
    --generator_option_file $ConfigPath `
    --probes $Probes `
    --generations $Generations `
    --report_prefix $Prefix

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Selesai. Laporan mentah tersimpan di $Prefix.* (di-gitignore; salin ringkasannya ke garak/README.md)."
