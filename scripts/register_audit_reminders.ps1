# Registers one weekly Windows Task Scheduler toast per scripts/*_weekly.sh, staggered across Mon-Fri.
# The reminder only notifies you; run the named script yourself (bash scripts/<name>).
# Run from a Windows PowerShell prompt (not the devcontainer):  powershell -ExecutionPolicy Bypass -File scripts\register_audit_reminders.ps1
# Remove with:  powershell -File scripts\register_audit_reminders.ps1 -Unregister
param([switch]$Unregister)

$prefix = 'FrictionlessArchitect-Audit-'

# Script, day, time. Two days carry two audits, 10 minutes apart.
$reminders = @(
  @{ Script = 'vuln_audit_weekly.sh';           Day = 'Monday';    Time = '09:00' },
  @{ Script = 'quality_audit_weekly.sh';        Day = 'Tuesday';   Time = '09:00' },
  @{ Script = 'spec_alignment_weekly.sh';       Day = 'Wednesday'; Time = '09:00' },
  @{ Script = 'adr_audit_weekly.sh';            Day = 'Thursday';  Time = '09:00' },
  @{ Script = 'commit_audit_weekly.sh';         Day = 'Thursday';  Time = '09:10' },
  @{ Script = 'docs_audit_weekly.sh';           Day = 'Friday';    Time = '09:00' },
  @{ Script = 'wiki_audit_weekly.sh';           Day = 'Friday';    Time = '09:10' }
)

foreach ($r in $reminders) {
  $name = $prefix + ($r.Script -replace '_weekly\.sh$', '')
  if ($Unregister) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
    continue
  }

  $title = "Audit due: $($r.Script)"
  $body  = "Run: bash scripts/$($r.Script)"
  $toast = @"
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
`$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
`$text = `$xml.GetElementsByTagName('text')
`$text[0].AppendChild(`$xml.CreateTextNode('$title')) | Out-Null
`$text[1].AppendChild(`$xml.CreateTextNode('$body')) | Out-Null
`$appId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier(`$appId).Show([Windows.UI.Notifications.ToastNotification]::new(`$xml))
"@
  $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($toast))

  $action   = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -EncodedCommand $encoded"
  $trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $r.Day -At $r.Time
  # StartWhenAvailable: a reminder missed while the PC was off fires at next wake.
  $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
  Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
  Write-Host "$name -> $($r.Day) $($r.Time)"
}
