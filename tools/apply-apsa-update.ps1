$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$result=Join-Path $PSScriptRoot 'apsa-install-result.txt'
try{
    $source=Join-Path $root 'release\settings-build\ClaimViewer.exe'
    $target='C:\Program Files\Claim Viewer\ClaimViewer.exe'
    Copy-Item -LiteralPath $source -Destination $target -Force
    if((Get-FileHash -LiteralPath $source).Hash -ne (Get-FileHash -LiteralPath $target).Hash){throw 'Installed executable verification failed.'}
    & (Join-Path $root 'word\install-citation-styles.ps1') -Machine
    & (Join-Path $root 'word\install-ribbon.ps1') -Machine -DllPath 'C:\Program Files\Claim Viewer\Word\ClaimViewerWord.dll'
    [IO.File]::WriteAllText($result,'Updated app, APSA style and automatic ribbon registration verified.')
}catch{[IO.File]::WriteAllText($result,('Update failed: '+$_.Exception.Message));exit 1}
