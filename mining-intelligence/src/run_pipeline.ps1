<#
.SYNOPSIS
  Project 01 end-to-end build: (optional download) -> staging -> marts -> checks.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File src\run_pipeline.ps1
  powershell -ExecutionPolicy Bypass -File src\run_pipeline.ps1 -Download
#>
param([switch]$Download)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Py   = Join-Path (Split-Path -Parent $Root) '.venv\Scripts\python.exe'
Set-Location $Root

if ($Download) { & (Join-Path $PSScriptRoot 'acquire_raw.ps1') }

$db = 'data\interim\mining.duckdb'
& $Py src\run_sql.py sql\10_staging.sql sql\20_marts.sql --db $db
if ($LASTEXITCODE -ne 0) { throw "SQL build failed" }
& $Py src\run_sql.py sql\19_staging_checks.sql sql\29_mart_checks.sql --db $db --out data\interim\checks
if ($LASTEXITCODE -ne 0) { throw "Checks failed" }
New-Item -ItemType Directory -Force tableau\data | Out-Null
& $Py src\run_sql.py sql\40_tableau_export.sql --db $db
if ($LASTEXITCODE -ne 0) { throw "Tableau export failed" }
