$log = Join-Path $PSScriptRoot "scheduler.log"

"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] START user=$env:USERNAME" |
    Add-Content $log

$env:RESEND_API_KEY = [Environment]::GetEnvironmentVariable("RESEND_API_KEY", "User")
$env:SENDER_EMAIL = [Environment]::GetEnvironmentVariable("SENDER_EMAIL", "User")
$env:RECIPIENT_EMAIL = [Environment]::GetEnvironmentVariable("RECIPIENT_EMAIL", "User")

Set-Location $PSScriptRoot

$localAppData = [Environment]::GetFolderPath("LocalApplicationData")
$python = Join-Path $localAppData "Programs\Python\Python314\python.exe"

if (-not (Test-Path $python)) {
    "Pythonが見つかりません: $python" | Add-Content $log
    exit 1
}

& $python -m flask --app app send-notifications *>> $log

$exitCode = $LASTEXITCODE

"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] END exit=$exitCode" |
    Add-Content $log

exit $exitCode