$ErrorActionPreference='Stop'
try {
 $root='C:\Apps\ClaimViewer'
 $dll='C:\Program Files\Claim Viewer\Word\ClaimViewerWord.dll'
 Copy-Item -LiteralPath (Join-Path $root 'word\ClaimViewerWord.dll') -Destination $dll -Force
 & "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe" $dll /codebase
 if($LASTEXITCODE){throw 'Ribbon registration failed.'}
 & (Join-Path $root 'word\install-ribbon.ps1') -Machine -DllPath $dll
 [IO.File]::WriteAllText((Join-Path $root 'tools\ribbon-component-result.txt'),'Updated Office interfaces and registered ribbon.')
} catch { [IO.File]::WriteAllText('C:\Apps\ClaimViewer\tools\ribbon-component-result.txt',$_.Exception.Message); exit 1 }
