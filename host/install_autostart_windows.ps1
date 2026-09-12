$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Pythonw = Join-Path $Root ".venv\Scripts\pythonw.exe"
$Bridge = Join-Path $Root "control_deck_bridge.py"
$Config = Join-Path $Root "config.json"

if (-not (Test-Path $Pythonw)) {
    throw "Python virtual environment not found. Run host\run_windows.bat once first."
}
if (-not (Test-Path $Config)) {
    throw "host\config.json not found. Run host\run_windows.bat once first."
}

$Startup = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $Startup "PC Control Deck Bridge.lnk"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $Pythonw
$Shortcut.Arguments = '"' + $Bridge + '" --config "' + $Config + '"'
$Shortcut.WorkingDirectory = $Root
$Shortcut.Description = "ESP32 PC Control Deck telemetry bridge"
$Shortcut.Save()

Write-Host "Installed PC Control Deck Bridge startup shortcut:"
Write-Host $ShortcutPath
