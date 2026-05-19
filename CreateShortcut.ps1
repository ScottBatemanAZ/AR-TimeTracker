# CreateShortcut.ps1
# Run this once to create the desktop shortcut for Azazel's Razer Time Tracker
# Right-click > Run with PowerShell  OR  run from PowerShell terminal

$TrackerDir  = "R:\Azazel's Razer\timetracker"
$BatFile     = Join-Path $TrackerDir "launch.bat"
$IconFile    = Join-Path $TrackerDir "ARSymbol.ico"
$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "Azazel's Razer Time Tracker.lnk"

$WScript = New-Object -ComObject WScript.Shell
$Shortcut = $WScript.CreateShortcut($ShortcutPath)

$Shortcut.TargetPath       = $BatFile
$Shortcut.WorkingDirectory = $TrackerDir
$Shortcut.IconLocation     = "$IconFile, 0"
$Shortcut.Description      = "Azazel's Razer Time Tracker"
$Shortcut.WindowStyle      = 1   # 1 = Normal, 7 = Minimized (hides the cmd window)

$Shortcut.Save()

Write-Host ""
Write-Host "  Shortcut created at:"
Write-Host "  $ShortcutPath"
Write-Host ""
Write-Host "  Pointing to: $BatFile"
Write-Host "  Icon:        $IconFile"
Write-Host ""
