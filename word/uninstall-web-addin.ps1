$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'install-citation-styles.ps1') -Uninstall
$native='HKLM:\Software\Microsoft\Office\Word\Addins\ClaimViewer.Citations'
if(Test-Path $native){
    $args='-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $PSScriptRoot 'install-native-ribbon.ps1')+'" -Uninstall'
    $process=Start-Process powershell.exe -ArgumentList $args -Verb RunAs -WindowStyle Hidden -Wait -PassThru
    if($process.ExitCode -ne 0){throw 'Could not remove the Word ribbon component.'}
}
& (Join-Path $PSScriptRoot 'uninstall-ribbon.ps1')
Remove-ItemProperty 'HKCU:\Software\ClaimViewer' -Name WordRoot -ErrorAction SilentlyContinue
$configPath=Join-Path $PSScriptRoot 'catalog-config.json'
if(Test-Path -LiteralPath $configPath){
    $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $args='-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $PSScriptRoot 'install-catalog.ps1')+'" -ExpectedSid "'+$sid+'" -Uninstall'
    $process=Start-Process -FilePath powershell.exe -ArgumentList $args -Verb RunAs -WindowStyle Hidden -Wait -PassThru
    if($process.ExitCode -ne 0){throw 'Could not remove the Word catalog share. Uninstall stopped.'}
}
try{
    $config=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'service-config.json')|ConvertFrom-Json
    Invoke-RestMethod 'https://localhost:38491/api' -Method Post -ContentType 'application/json' -Headers @{Authorization=('Bearer '+$config.token)} -Body '{"method":"shutdown"}' -TimeoutSec 3|Out-Null
}catch{}
Remove-ItemProperty 'HKCU:\Software\Microsoft\Office\16.0\WEF\Developer' -Name 'b1a3d266-67e6-4232-a98b-7935cda2930c' -ErrorAction SilentlyContinue
Remove-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'ClaimViewerWordService' -ErrorAction SilentlyContinue
$catalogKey='HKCU:\Software\Microsoft\Office\16.0\WEF\TrustedCatalogs\{f7947c71-8a31-47de-8f55-0a57ea702d27}'
if(Test-Path $catalogKey){
    $catalogUrl=Get-ItemPropertyValue $catalogKey -Name Url -ErrorAction SilentlyContinue
    $configPath=Join-Path $PSScriptRoot 'catalog-config.json'
    if(Test-Path -LiteralPath $configPath){
        $catalogConfig=Get-Content -LiteralPath $configPath -Raw|ConvertFrom-Json
        if($catalogUrl -eq $catalogConfig.url){Remove-Item -LiteralPath $catalogKey}
    }
}
$path=Join-Path $PSScriptRoot 'localhost.cer'
if(Test-Path -LiteralPath $path){$cert=[Security.Cryptography.X509Certificates.X509Certificate2]::new($path);$entry="Cert:\CurrentUser\Root\$($cert.Thumbprint)";if(Test-Path $entry){Remove-Item -LiteralPath $entry}}
Write-Output 'Per-user Word web add-in, its startup entry and its localhost certificate trust removed. Documents and library data retained.'
