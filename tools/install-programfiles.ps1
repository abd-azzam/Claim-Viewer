$ErrorActionPreference = 'Stop'
Start-Transcript -Path 'C:\Apps\ClaimViewer\tools\installation-update.log' -Force | Out-Null
$installTarget = Join-Path $env:ProgramFiles 'Claim Viewer'
$buildExe = 'C:\Apps\ClaimViewer\release\programfiles\ClaimViewer.exe'
if (!(Test-Path -LiteralPath $buildExe)) { throw 'Build the executable first.' }
if (!(Test-Path -LiteralPath 'C:\Apps\ClaimViewer\index.html') -or !(Test-Path -LiteralPath 'C:\Apps\ClaimViewer\library.json')) { throw 'Existing library is missing. Installation stopped.' }
New-Item -ItemType Directory -Path $installTarget -Force | Out-Null
Copy-Item -LiteralPath $buildExe -Destination (Join-Path $installTarget 'ClaimViewer.exe') -Force
[IO.File]::WriteAllText((Join-Path $installTarget 'data-root.txt'), 'C:\Apps\ClaimViewer')
$shortcutShell = New-Object -ComObject WScript.Shell
$shortcutPath = Join-Path ([Environment]::GetFolderPath('CommonPrograms')) 'Claim Viewer.lnk'
$shortcut = $shortcutShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = Join-Path $installTarget 'ClaimViewer.exe'
$shortcut.WorkingDirectory = 'C:\Apps\ClaimViewer'
$shortcut.Save()
foreach ($shortcutFolder in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'), [Environment]::GetFolderPath('CommonDesktopDirectory'))) {
    $legacyShortcut = Join-Path $shortcutFolder 'Claim Viewer.lnk'
    if (Test-Path -LiteralPath $legacyShortcut) {
        $legacyLink = $shortcutShell.CreateShortcut($legacyShortcut)
        $legacyLink.TargetPath = Join-Path $installTarget 'ClaimViewer.exe'
        $legacyLink.WorkingDirectory = 'C:\Apps\ClaimViewer'
        $legacyLink.Save()
    }
}
Copy-Item -LiteralPath 'C:\Apps\ClaimViewer\tools\uninstall-programfiles.ps1' -Destination $installTarget -Force
$registration = 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\ClaimViewerWorkspace'
New-Item -Path $registration -Force | Out-Null
$uninstallCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $installTarget 'uninstall-programfiles.ps1') + '"'
$registrationValues = @{DisplayName='Claim Viewer'; DisplayVersion='2.2.1'; Publisher='Claim Viewer'; InstallLocation=$installTarget; DisplayIcon=(Join-Path $installTarget 'ClaimViewer.exe'); UninstallString=$uninstallCommand}
$registrationValues.GetEnumerator() | ForEach-Object { New-ItemProperty -Path $registration -Name $_.Key -Value $_.Value -PropertyType String -Force | Out-Null }
New-ItemProperty -Path $registration -Name NoModify -Value 1 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $registration -Name NoRepair -Value 1 -PropertyType DWord -Force | Out-Null
if ((Get-FileHash -LiteralPath $buildExe).Hash -ne (Get-FileHash -LiteralPath $shortcut.TargetPath).Hash) { throw 'Installed executable differs from build.' }
Write-Output "Installed and verified: $($shortcut.TargetPath)"
Stop-Transcript | Out-Null
