$Startup = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $Startup "PC Control Deck Bridge.lnk"
if (Test-Path $ShortcutPath) {
    Remove-Item $ShortcutPath -Force
    Write-Host "Removed PC Control Deck Bridge startup shortcut."
} else {
    Write-Host "PC Control Deck Bridge startup shortcut was not installed."
}
