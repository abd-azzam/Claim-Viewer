param([switch]$Machine)
$ErrorActionPreference = 'Stop'
foreach ($view in @([Microsoft.Win32.RegistryView]::Registry64,[Microsoft.Win32.RegistryView]::Registry32)) {
    $scope=if($Machine){[Microsoft.Win32.RegistryHive]::LocalMachine}else{[Microsoft.Win32.RegistryHive]::CurrentUser}
    $hive = [Microsoft.Win32.RegistryKey]::OpenBaseKey($scope,$view)
    foreach ($key in @('Software\Classes\CLSID\{40A65F77-5B1E-4A73-A208-441CBF848BF8}','Software\Classes\ClaimViewer.Word','Software\Microsoft\Office\Word\Addins\ClaimViewer.Word','Software\Classes\CLSID\{908A5489-769B-4BB8-855A-7BB05A1E2158}','Software\Classes\CLSID\{FF33A1A7-BFE3-4CA3-9809-13717A51FDF8}','Software\Classes\ClaimViewer.Citations','Software\Classes\ClaimViewer.WordPane','Software\Microsoft\Office\Word\Addins\ClaimViewer.Citations')) {
        $hive.DeleteSubKeyTree($key,$false)
    }
    $hive.Close()
}
if(!$Machine){Remove-ItemProperty 'HKCU:\Software\Microsoft\Office\16.0\Word\Resiliency\DoNotDisableAddinList' -Name 'ClaimViewer.Citations' -ErrorAction SilentlyContinue}
Write-Output 'Claim Viewer Word ribbon registration removed. Documents and citations are retained.'
