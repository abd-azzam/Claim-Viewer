$ErrorActionPreference='Stop'
$root='C:\Apps\ClaimViewer'
$result=Join-Path $root 'tools\combined-install-result.txt'
try {
    Copy-Item -LiteralPath (Join-Path $root 'release\settings-build\ClaimViewer.exe') -Destination 'C:\Program Files\Claim Viewer\ClaimViewer.exe' -Force
    & (Join-Path $root 'word\install-native-ribbon.ps1')
    $status=Get-Content -Raw (Join-Path $root 'word\ribbon-install-result.json')|ConvertFrom-Json
    if(!$status.ok){throw $status.error}
    foreach($pair in @(@((Join-Path $root 'release\settings-build\ClaimViewer.exe'),'C:\Program Files\Claim Viewer\ClaimViewer.exe'),@((Join-Path $root 'word\ClaimViewerWord.dll'),'C:\Program Files\Claim Viewer\Word\ClaimViewerWord.dll'))){
        if((Get-FileHash -LiteralPath $pair[0]).Hash -ne (Get-FileHash -LiteralPath $pair[1]).Hash){throw 'Installed file verification failed.'}
    }
    [IO.File]::WriteAllText($result,'Installed executable and Word ribbon match the verified build.')
} catch { [IO.File]::WriteAllText($result,$_.Exception.Message); exit 1 }
