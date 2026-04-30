# 启动飞书长连接 Bot（需 config/app.yaml 中填写 feishu.app_id / app_secret）
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$env:WRITING_PIPELINE_ROOT = $repoRoot
Set-Location $repoRoot
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Error "Missing $py"
}
& $py -m app.feishu.bot_loop
