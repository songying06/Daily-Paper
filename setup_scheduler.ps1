# setup_scheduler.ps1 — 设置 Windows 每日 7:00 自动推送
# 以管理员身份运行此脚本

$TaskName = "DailyPaperPush"
$ScriptDir = "C:\Users\songy\Desktop\daily-paper-push"
$PythonPath = (Get-Command python).Source
$MainScript = Join-Path $ScriptDir "main.py"

$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$MainScript`"" -WorkingDirectory $ScriptDir
$Trigger = New-ScheduledTaskTrigger -Daily -At "07:00AM"
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

$Task = Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description "计算固体力学每日文献推送" -Force

if ($Task) {
    Write-Host "定时任务已创建: $TaskName"
    Write-Host "  运行时间: 每天 7:00 AM"
    Write-Host "  脚本路径: $MainScript"
    Write-Host ""
    Write-Host "管理命令:"
    Write-Host "  taskschd.msc          # 打开任务计划程序查看"
    Write-Host "  schtasks /Run /TN $TaskName    # 手动运行一次"
} else {
    Write-Host "创建失败，请以管理员身份运行此脚本"
}
