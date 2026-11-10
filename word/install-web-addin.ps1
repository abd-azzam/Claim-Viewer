param([string]$AppExe='')
$ErrorActionPreference='Stop'
if(Get-Process WINWORD -ErrorAction SilentlyContinue){throw 'Save your documents and close Microsoft Word before installing or repairing the add-in.'}
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
$resultPath=Join-Path $root 'ribbon-install-result.json'
if(Test-Path -LiteralPath $resultPath){Remove-Item -LiteralPath $resultPath}
try{$process=Start-Process powershell.exe -ArgumentList $ribbonArgs -Verb RunAs -WindowStyle Hidden -Wait -PassThru}
catch{throw ('Could not start the administrator step for Word setup: '+$_.Exception.Message)}
if(!(Test-Path -LiteralPath $resultPath)){throw 'The administrator step did not finish. Run Repair installation and approve the Windows prompt.'}
$result=Get-Content -Raw -LiteralPath $resultPath|ConvertFrom-Json
if($process.ExitCode -ne 0 -or !$result.ok){throw ('Word ribbon setup failed: '+$result.error)}
& (Join-Path $root 'install-ribbon.ps1') -DllPath (Join-Path $env:ProgramFiles 'Claim Viewer\Word\ClaimViewerWord.dll')
$healthUrl='https://127.0.0.1:38491/health'
$old=$null
try{$old=Invoke-RestMethod $healthUrl -TimeoutSec 2}catch{}
if($old.service -eq 'Claim Viewer Word'){
    $config=Get-Content -Raw -LiteralPath (Join-Path $root 'service-config.json')|ConvertFrom-Json
    Invoke-RestMethod 'https://127.0.0.1:38491/api' -Method Post -ContentType 'application/json' -Headers @{Authorization=('Bearer '+$config.token)} -Body '{"method":"shutdown"}' -TimeoutSec 5|Out-Null
    for($attempt=0;$attempt -lt 10;$attempt++){
        Start-Sleep -Milliseconds 300
        try{Invoke-RestMethod $healthUrl -TimeoutSec 2|Out-Null}catch{break}
    }
    if($attempt -eq 10){throw 'The old Word service did not stop. Restart Windows and run Repair installation.'}
}
# The service outlives setup and needs its own extracted copy of the runtime.
$previousReset=$env:PYINSTALLER_RESET_ENVIRONMENT
try{
    $env:PYINSTALLER_RESET_ENVIRONMENT='1'
    Start-Process -FilePath $exe -ArgumentList '--word-service' -WindowStyle Hidden
}finally{$env:PYINSTALLER_RESET_ENVIRONMENT=$previousReset}
$ready=$false
$healthError=''
for($attempt=0;$attempt -lt 20 -and !$ready;$attempt++){
    Start-Sleep -Milliseconds 400
    try{$health=Invoke-RestMethod $healthUrl -TimeoutSec 3;$ready=$health.service -eq 'Claim Viewer Word'}catch{$healthError=$_.Exception.Message}
}
if(!$ready){throw ('The Word local service did not respond: '+$healthError)}
Write-Output 'Installed. Restart Word, then choose Claim Viewer > Insert citation.'
