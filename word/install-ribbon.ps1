param([switch]$Machine, [string]$DllPath)
$ErrorActionPreference = 'Stop'
$dll = if ($DllPath) {$DllPath} else {Join-Path $PSScriptRoot 'ClaimViewerWord.dll'}
if (!(Test-Path -LiteralPath $dll)) { throw 'Build ClaimViewerWord.dll first.' }
$assemblyName = [Reflection.AssemblyName]::GetAssemblyName($dll).FullName
$versionName=[Reflection.AssemblyName]::GetAssemblyName($dll).Version.ToString()
$classId = '{908A5489-769B-4BB8-855A-7BB05A1E2158}'
# Register only Claim Viewer classes in the selected Windows scope.
foreach ($view in @([Microsoft.Win32.RegistryView]::Registry64,[Microsoft.Win32.RegistryView]::Registry32)) {
    $scope = if ($Machine) {[Microsoft.Win32.RegistryHive]::LocalMachine} else {[Microsoft.Win32.RegistryHive]::CurrentUser}
    $hive = [Microsoft.Win32.RegistryKey]::OpenBaseKey($scope,$view)
    foreach($old in @('Software\Classes\CLSID\{40A65F77-5B1E-4A73-A208-441CBF848BF8}','Software\Classes\ClaimViewer.Word','Software\Microsoft\Office\Word\Addins\ClaimViewer.Word')){$hive.DeleteSubKeyTree($old,$false)}
    $server = $hive.CreateSubKey("Software\Classes\CLSID\$classId\InprocServer32")
    $codeBase=[Uri]::UnescapeDataString(([Uri]$dll).AbsoluteUri)
    $values = @{''='mscoree.dll';ThreadingModel='Both';Class='ClaimViewerWord.Connect';Assembly=$assemblyName;RuntimeVersion='v4.0.30319';CodeBase=$codeBase}
    foreach ($pair in $values.GetEnumerator()) { $server.SetValue($pair.Key,$pair.Value) }
    $server.Close()
    $version = $hive.CreateSubKey("Software\Classes\CLSID\$classId\InprocServer32\$versionName")
    foreach ($name in @('Class','Assembly','RuntimeVersion','CodeBase')) { $version.SetValue($name,$values[$name]) };$version.Close()
    $rootKey=$hive.CreateSubKey("Software\Classes\CLSID\$classId");$rootKey.SetValue('','ClaimViewerWord.Connect');$rootKey.Close()
    $category=$hive.CreateSubKey("Software\Classes\CLSID\$classId\Implemented Categories\{62C8FE65-4EBB-45E7-B440-6E39B2CDBF29}");$category.Close()
    $classProg=$hive.CreateSubKey("Software\Classes\CLSID\$classId\ProgId");$classProg.SetValue('','ClaimViewer.Citations');$classProg.Close()
    $named=$hive.CreateSubKey('Software\Classes\ClaimViewer.Citations');$named.SetValue('','ClaimViewerWord.Connect');$named.Close()
    $progid=$hive.CreateSubKey('Software\Classes\ClaimViewer.Citations\CLSID');$progid.SetValue('',$classId);$progid.Close()
    $paneId='{FF33A1A7-BFE3-4CA3-9809-13717A51FDF8}'
    $paneValues=@{''='mscoree.dll';ThreadingModel='Both';Class='ClaimViewerWord.CitationPane';Assembly=$assemblyName;RuntimeVersion='v4.0.30319';CodeBase=$codeBase}
    foreach($id in @($classId,$paneId)){
        $key=$hive.OpenSubKey("Software\Classes\CLSID\$id\InprocServer32",$true)
        if($key){foreach($name in $key.GetSubKeyNames()){if($name -match '^\d+\.\d+\.\d+\.\d+$' -and $name -ne $versionName){$key.DeleteSubKeyTree($name,$false)}};$key.Close()}
    }
    foreach($suffix in @('', ('\'+$versionName))){
        $paneServer=$hive.CreateSubKey("Software\Classes\CLSID\$paneId\InprocServer32"+$suffix)
        foreach($pair in $paneValues.GetEnumerator()){$paneServer.SetValue($pair.Key,$pair.Value)}
        $paneServer.Close()
    }
    $paneKey=$hive.CreateSubKey("Software\Classes\CLSID\$paneId");$paneKey.SetValue('','Claim Viewer citation pane');$paneKey.Close()
    $control=$hive.CreateSubKey("Software\Classes\CLSID\$paneId\Control");$control.Close()
    $paneProg=$hive.CreateSubKey("Software\Classes\CLSID\$paneId\ProgId");$paneProg.SetValue('','ClaimViewer.WordPane');$paneProg.Close()
    $namedPane=$hive.CreateSubKey('Software\Classes\ClaimViewer.WordPane\CLSID');$namedPane.SetValue('',$paneId);$namedPane.Close()
    $addin=$hive.CreateSubKey('Software\Microsoft\Office\Word\Addins\ClaimViewer.Citations')
    $addin.SetValue('FriendlyName','Claim Viewer citations');$addin.SetValue('Description','Library folders, citations, styles and bibliography')
    $addin.SetValue('LoadBehavior',3,[Microsoft.Win32.RegistryValueKind]::DWord)
    $addin.SetValue('CommandLineSafe',1,[Microsoft.Win32.RegistryValueKind]::DWord);$addin.Close();$hive.Close()
}
# Word's "Always enable this add-in" preference, scoped only to Claim Viewer.
if(!$Machine){
    $resiliency='HKCU:\Software\Microsoft\Office\16.0\Word\Resiliency\DoNotDisableAddinList'
    New-Item -Path $resiliency -Force|Out-Null
    New-ItemProperty -Path $resiliency -Name 'ClaimViewer.Citations' -Value 1 -PropertyType DWord -Force|Out-Null
}
Write-Output 'Claim Viewer Word ribbon registered for this Windows user. Restart Word to load it.'
