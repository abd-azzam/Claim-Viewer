$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
if (!(New-Object Security.Principal.WindowsPrincipal($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell.exe -Verb RunAs -WindowStyle Hidden -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -File "' + $PSCommandPath + '"')
    exit
}
$installTarget = Join-Path $env:ProgramFiles 'Claim Viewer'
$ribbonUninstall = 'C:\Apps\ClaimViewer\word\uninstall-ribbon.ps1'
if (Test-Path -LiteralPath $ribbonUninstall) { & $ribbonUninstall }
$webAddinUninstall = 'C:\Apps\ClaimViewer\word\uninstall-web-addin.ps1'
if (Test-Path -LiteralPath $webAddinUninstall) { & $webAddinUninstall }
foreach ($name in @('ClaimViewer.exe','data-root.txt')) {
    $target = Join-Path $installTarget $name
    if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target }
}
$shortcutShell = New-Object -ComObject WScript.Shell
foreach ($folder in @([Environment]::GetFolderPath('CommonPrograms'),[Environment]::GetFolderPath('Programs'),[Environment]::GetFolderPath('Desktop'),[Environment]::GetFolderPath('CommonDesktopDirectory'))) {
    $link = Join-Path $folder 'Claim Viewer.lnk'
    if ((Test-Path -LiteralPath $link) -and ($shortcutShell.CreateShortcut($link).TargetPath -eq (Join-Path $installTarget 'ClaimViewer.exe'))) { Remove-Item -LiteralPath $link }
}
Remove-Item -LiteralPath 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\ClaimViewerWorkspace'
# User library, PDFs, settings and browser profile are deliberately retained.
Remove-Item -LiteralPath $PSCommandPath
if (!(Get-ChildItem -LiteralPath $installTarget -Force)) { Remove-Item -LiteralPath $installTarget }
