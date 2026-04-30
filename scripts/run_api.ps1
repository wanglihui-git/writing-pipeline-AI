# 启动 FastAPI（需已创建 .venv 并安装依赖）。默认 WRITING_PIPELINE_ROOT 为本仓库目录。
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$env:WRITING_PIPELINE_ROOT = $repoRoot
Set-Location $repoRoot
$py = Join-Path $repoRoot ".venv\Scripts\uvicorn.exe"
if (-not (Test-Path $py)) {
    Write-Error "Missing $py — run: python -m venv .venv && pip install -r requirements.txt"
}
& $py app.api.main:app --host 127.0.0.1 --port 8980 --reload
