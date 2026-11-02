$ErrorActionPreference='Stop'
$target=Join-Path $env:ProgramFiles 'Claim Viewer\Word'
New-Item -Path $target -ItemType Directory -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ClaimViewerWord.dll') -Destination $target -Force
& (Join-Path $PSScriptRoot 'install-ribbon.ps1') -Machine -DllPath (Join-Path $target 'ClaimViewerWord.dll')
