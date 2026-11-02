$ErrorActionPreference='Stop'
foreach ($view in @([Microsoft.Win32.RegistryView]::Registry64,[Microsoft.Win32.RegistryView]::Registry32)) {
    $hive=[Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine,$view)
    foreach ($key in @('Software\Classes\CLSID\{40A65F77-5B1E-4A73-A208-441CBF848BF8}','Software\Classes\ClaimViewer.Word','Software\Microsoft\Office\Word\Addins\ClaimViewer.Word')) {
        $hive.DeleteSubKeyTree($key,$false)
    }
    $hive.Close()
}
$dll=Join-Path $env:ProgramFiles 'Claim Viewer\Word\ClaimViewerWord.dll'
if(Test-Path -LiteralPath $dll){Remove-Item -LiteralPath $dll}
Write-Output 'Machine-wide Claim Viewer Word ribbon removed. Documents and library data are retained.'
