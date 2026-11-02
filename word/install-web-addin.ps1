param([string]$AppExe='')
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
& (Join-Path $root 'install-citation-styles.ps1')
$manifest=Join-Path $root 'manifest.xml'
$certificate=Join-Path $root 'localhost.cer'
$exe=Join-Path (Split-Path -Parent $root) 'ClaimViewer.exe'
if($AppExe){$exe=$AppExe}
if(!(Test-Path -LiteralPath $manifest) -or !(Test-Path -LiteralPath $certificate) -or !(Test-Path -LiteralPath $exe)){throw 'Prepare the manifest/certificate and update Claim Viewer first.'}
# Protect the bearer token, its manifest copy and the local TLS key for this Windows account.
$user=[Security.Principal.WindowsIdentity]::GetCurrent().User
foreach($name in @('service-config.json','manifest.xml','localhost-key.pem')){
    $path=Join-Path $root $name
    & icacls.exe $path /inheritance:r /grant:r ("*"+$user.Value+':(F)') '*S-1-5-18:(F)' '*S-1-5-32-544:(F)' | Out-Null
    if($LASTEXITCODE -ne 0){throw "Could not restrict access to $name"}
    $acl=Get-Acl -LiteralPath $path
    $allowed=@($user.Value,'S-1-5-18','S-1-5-32-544')
    if(!$acl.AreAccessRulesProtected -or @($acl.Access | Where-Object {$_.AccessControlType -eq 'Allow' -and $_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -notin $allowed}).Count){throw "Unexpected public access on $name; installation stopped."}
}
$cert=[Security.Cryptography.X509Certificates.X509Certificate2]::new($certificate)
if(!(Test-Path "Cert:\CurrentUser\Root\$($cert.Thumbprint)")){
    Import-Certificate -FilePath $certificate -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
}
$developer='HKCU:\Software\Microsoft\Office\16.0\WEF\Developer'
New-Item -Path $developer -Force | Out-Null
New-ItemProperty -Path $developer -Name 'b1a3d266-67e6-4232-a98b-7935cda2930c' -Value $manifest -PropertyType String -Force | Out-Null
$run='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
New-ItemProperty -Path $run -Name 'ClaimViewerWordService' -Value ('"'+$exe+'" --word-service') -PropertyType String -Force | Out-Null
$ready=$false
$healthError=''
try{$health=Invoke-RestMethod 'https://127.0.0.1:38491/health' -TimeoutSec 5;$ready=$health.service -eq 'Claim Viewer Word'}catch{$healthError=$_.Exception.Message}
if(!$ready){Start-Process -FilePath $exe -ArgumentList '--word-service' -WindowStyle Hidden}
for($attempt=0;$attempt -lt 20 -and !$ready;$attempt++){
    Start-Sleep -Milliseconds 400
    try{$health=Invoke-RestMethod 'https://127.0.0.1:38491/health' -TimeoutSec 3;$ready=$health.service -eq 'Claim Viewer Word'}catch{$healthError=$_.Exception.Message}
}
if(!$ready){throw ('The Word local service did not respond: '+$healthError)}
$preference='HKCU:\Software\ClaimViewer'
New-Item -Path $preference -Force|Out-Null
New-ItemProperty -Path $preference -Name WordRoot -Value (Split-Path -Parent $root) -PropertyType String -Force|Out-Null
$disabled='HKCU:\Software\Microsoft\Office\16.0\Word\Resiliency\DisabledItems'
if(Test-Path $disabled){
    $key=Get-Item $disabled
    foreach($name in $key.GetValueNames()){
        $bytes=$key.GetValue($name)
        if([Text.Encoding]::Unicode.GetString($bytes) -match 'claimviewer\.(word|citations)'){
            $backup=Join-Path $root 'disabled-entry-backups'
            New-Item -Path $backup -ItemType Directory -Force|Out-Null
            [IO.File]::WriteAllBytes((Join-Path $backup ($name+'.bin')),$bytes)
            Remove-ItemProperty -LiteralPath $disabled -Name $name
        }
    }
}
$ribbonArgs='-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $root 'install-native-ribbon.ps1')+'"'
$process=Start-Process powershell.exe -ArgumentList $ribbonArgs -Verb RunAs -WindowStyle Hidden -Wait -PassThru
$result=Get-Content -Raw -LiteralPath (Join-Path $root 'ribbon-install-result.json')|ConvertFrom-Json
if($process.ExitCode -ne 0 -or !$result.ok){throw ('Word ribbon setup failed: '+$result.error)}
& (Join-Path $root 'install-ribbon.ps1') -DllPath (Join-Path $env:ProgramFiles 'Claim Viewer\Word\ClaimViewerWord.dll')
Write-Output 'Installed. Restart Word, then choose Claim Viewer > Insert citation.'
