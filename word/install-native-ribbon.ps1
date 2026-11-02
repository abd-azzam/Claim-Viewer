param([switch]$Uninstall)
$ErrorActionPreference='Stop'
$result=Join-Path $PSScriptRoot 'ribbon-install-result.json'
try {
    if($Uninstall){
        & (Join-Path $PSScriptRoot 'install-citation-styles.ps1') -Uninstall -Machine
        & (Join-Path $PSScriptRoot 'uninstall-ribbon.ps1') -Machine
    }else{
        & (Join-Path $PSScriptRoot 'install-citation-styles.ps1') -Machine
        $target=Join-Path $env:ProgramFiles 'Claim Viewer\Word'
        New-Item -Path $target -ItemType Directory -Force|Out-Null
        $dll=Join-Path $target 'ClaimViewerWord.dll'
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ClaimViewerWord.dll') -Destination $dll -Force
        foreach($name in @('Microsoft.Web.WebView2.Core.dll','Microsoft.Web.WebView2.WinForms.dll')){Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination $target -Force}
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'runtimes') -Destination $target -Recurse -Force
        foreach($framework in @('Framework64','Framework')){
            & (Join-Path $env:WINDIR "Microsoft.NET\$framework\v4.0.30319\RegAsm.exe") $dll /codebase
            if($LASTEXITCODE){throw 'Microsoft Office component registration failed.'}
        }
        & (Join-Path $PSScriptRoot 'install-ribbon.ps1') -Machine -DllPath $dll
    }
    @{ok=$true}|ConvertTo-Json|Set-Content -LiteralPath $result -Encoding UTF8
}catch{
    @{ok=$false;error=$_.Exception.Message}|ConvertTo-Json|Set-Content -LiteralPath $result -Encoding UTF8
    exit 1
}
