$ErrorActionPreference='Stop'
$build='C:\Apps\ClaimViewer\release\settings-build\ClaimViewer.exe'
$installed='C:\Program Files\Claim Viewer\ClaimViewer.exe'
$result='C:\Apps\ClaimViewer\tools\settings-install-result.txt'
try {
    foreach($view in @([Microsoft.Win32.RegistryView]::Registry64,[Microsoft.Win32.RegistryView]::Registry32)){
        $hive=[Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine,$view)
        $hive.DeleteSubKeyTree('Software\Microsoft\Office\Word\Addins\ClaimViewer.Word',$false)
        $hive.Close()
    }
    Copy-Item -LiteralPath $build -Destination $installed -Force
    if((Get-FileHash -LiteralPath $build).Hash -ne (Get-FileHash -LiteralPath $installed).Hash){throw 'Installed executable verification failed.'}
    [IO.File]::WriteAllText($result,'Installed executable updated and verified.')
} catch {
    [IO.File]::WriteAllText($result,('Update failed: '+$_.Exception.Message))
    exit 1
}
