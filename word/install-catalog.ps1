param([string]$ExpectedSid='', [switch]$Uninstall)
$ErrorActionPreference='Stop'
$resultPath=Join-Path $PSScriptRoot 'catalog-install-result.json'
$created=$false
try {
    $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
    if($ExpectedSid -and $identity.User.Value -ne $ExpectedSid){throw 'Approve installation as the same Windows account that runs Claim Viewer.'}
    $catalog=Join-Path $PSScriptRoot 'catalog'
    $shareName='ClaimViewerWord'
    $catalogId='{f7947c71-8a31-47de-8f55-0a57ea702d27}'
    if($Uninstall){
        $share=Get-SmbShare -Name $shareName -ErrorAction SilentlyContinue
        if($share -and $share.Path -eq $catalog){Remove-SmbShare -Name $shareName -Force}
        @{ok=$true} | ConvertTo-Json | Set-Content -LiteralPath $resultPath -Encoding utf8
        exit 0
    }
    New-Item -ItemType Directory -Path $catalog -Force | Out-Null
    $manifest=Join-Path $catalog 'ClaimViewer.xml'
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'manifest.xml') -Destination $manifest -Force
    & icacls.exe $manifest /inheritance:r /grant:r ('*'+$identity.User.Value+':(F)') '*S-1-5-18:(F)' '*S-1-5-32-544:(F)' | Out-Null
    if($LASTEXITCODE -ne 0){throw 'Could not restrict catalog manifest access.'}
    $share=Get-SmbShare -Name $shareName -ErrorAction SilentlyContinue
    if($share -and $share.Path -ne $catalog){throw 'The ClaimViewerWord share name is already used by another folder.'}
    if(!$share){New-SmbShare -Name $shareName -Path $catalog -ReadAccess $identity.Name -FolderEnumerationMode AccessBased -EncryptData $true | Out-Null;$created=$true}
    $access=@(Get-SmbShareAccess -Name $shareName)
    if(@($access | Where-Object {$_.AccessControlType -eq 'Allow' -and $_.AccountName -ne $identity.Name}).Count){throw 'Catalog share has unexpected access. Installation stopped.'}
    $url='\\localhost\'+$shareName
    if(!(Test-Path -LiteralPath (Join-Path $url 'ClaimViewer.xml'))){throw 'Word catalog cannot be read through its share path.'}
    $key='HKCU:\Software\Microsoft\Office\16.0\WEF\TrustedCatalogs\'+$catalogId
    New-Item -Path $key -Force | Out-Null
    New-ItemProperty -Path $key -Name Id -Value $catalogId -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $key -Name Url -Value $url -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $key -Name Flags -Value 1 -PropertyType DWord -Force | Out-Null
    @{url=$url;id=$catalogId;share=$shareName;sid=$identity.User.Value} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'catalog-config.json') -Encoding utf8
    @{ok=$true;message='Word catalog registered. Only your Windows account has read access. No firewall rule was changed.'} | ConvertTo-Json | Set-Content -LiteralPath $resultPath -Encoding utf8
} catch {
    if($created){Remove-SmbShare -Name $shareName -Force -ErrorAction SilentlyContinue}
    @{ok=$false;error=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath $resultPath -Encoding utf8
    exit 1
}
