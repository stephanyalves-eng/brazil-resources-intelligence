<#
.SYNOPSIS
  Phase 4 - Raw data acquisition for Project 01 (ANM: AMB + CFEM).

.DESCRIPTION
  Downloads the official ANM open-data files into data/raw/ without modifying them and writes
  data/raw/MANIFEST.csv (url, bytes, sha256, server Last-Modified, download timestamp).

  Why PowerShell and not Python/curl: dadosabertos.anm.gov.br serves an incomplete TLS certificate
  chain. OpenSSL-based clients fail ("unable to verify the first certificate"); the Windows TLS stack
  completes the chain via AIA. Certificate validation is NEVER disabled.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File src\acquire_raw.ps1
  powershell -ExecutionPolicy Bypass -File src\acquire_raw.ps1 -SkipLarge   # AMB only
#>
param([switch]$SkipLarge)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # progress bar slows Invoke-WebRequest by ~10x
$Root = Split-Path -Parent $PSScriptRoot
$Raw  = Join-Path $Root 'data\raw'
$Base = 'https://dadosabertos.anm.gov.br'

$files = @(
  @{ path = 'AMB/Producao_Beneficiada.csv'; large = $false },
  @{ path = 'AMB/Producao_Bruta.csv';       large = $false },
  @{ path = 'AMB/metadados-amb.ods';        large = $false },
  @{ path = 'CFEM/metadados-cfem.ods';      large = $false },
  @{ path = 'CFEM/CFEM_Arrecadacao.csv';    large = $true  }
)

$rows = @()
foreach ($f in $files) {
  if ($SkipLarge -and $f.large) { continue }
  $url  = "$Base/$($f.path)"
  $dir  = Join-Path $Raw (Split-Path $f.path -Parent)
  New-Item -ItemType Directory -Force $dir | Out-Null
  $out  = Join-Path $dir (Split-Path $f.path -Leaf)
  Write-Host "Downloading $url"
  $r = Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $out -PassThru -TimeoutSec 1800
  $item = Get-Item $out
  $rows += [pscustomobject]@{
    file          = "$($f.path)"
    url           = $url
    bytes         = $item.Length
    sha256        = (Get-FileHash $out -Algorithm SHA256).Hash.ToLower()
    last_modified = $r.Headers['Last-Modified']
    downloaded_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
  }
}
$rows | Export-Csv -NoTypeInformation -Encoding UTF8 (Join-Path $Raw 'MANIFEST.csv')
$rows | Format-Table file, bytes, last_modified -AutoSize
