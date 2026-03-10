# Run as Administrator to create scheduled task. IPO check runs daily at 11:11 AM local time.
# For 11:11 Nepal time, set system timezone to Nepal (UTC+5:45).

param(
    [string]$TaskTime = "11:11"
)

$ProjectDir = $PSScriptRoot
$BatPath = Join-Path $ProjectDir "run_check.bat"
if (-not (Test-Path $BatPath)) {
    Write-Error "run_check.bat not found in $ProjectDir"
    exit 1
}

$TaskName = "IPO-Check-MeroShare"
$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$BatPath`"" -WorkingDirectory $ProjectDir
$Trigger = New-ScheduledTaskTrigger -Daily -At $TaskTime
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Runs MeroShare IPO check daily"

Write-Host "Scheduled task '$TaskName' created. Runs daily at $TaskTime (local time)."
Write-Host "To use 11:11 Nepal time, set system timezone to Nepal (UTC+5:45) or run at 05:26 UTC."
Write-Host "View: Task Scheduler -> Task Scheduler Library -> $TaskName"
