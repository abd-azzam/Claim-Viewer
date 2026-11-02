param([string]$Python='python',[string]$ISCC='')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
if(Test-Path -LiteralPath $Python){$Python=(Resolve-Path -LiteralPath $Python).Path}
else{$Python=(Get-Command $Python -ErrorAction Stop).Source}
$previous=Get-Location
try{
    Set-Location -LiteralPath $root
    & (Join-Path $PSScriptRoot 'build-word-ribbon.ps1') -Python $Python
    & $Python -m PyInstaller --noconfirm --distpath release/settings-build --workpath release/settings-work release/ClaimViewer.spec
    if($LASTEXITCODE){throw 'Application build failed.'}
    & $Python tools/stage-distribution.py
    if($LASTEXITCODE){throw 'Staging failed.'}
    & $Python tools/verify-distribution.py
    if($LASTEXITCODE){throw 'Distribution verification failed.'}
    $prerequisite=Join-Path $root 'release\prerequisites\MicrosoftEdgeWebview2Setup.exe'
    if(!(Test-Path -LiteralPath $prerequisite)){
        New-Item -Path (Split-Path -Parent $prerequisite) -ItemType Directory -Force|Out-Null
        Invoke-WebRequest -UseBasicParsing -Uri 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile $prerequisite
    }
    $signature=Get-AuthenticodeSignature -LiteralPath $prerequisite
    if($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Microsoft Corporation'){throw 'WebView2 bootstrapper signature verification failed.'}
    if(!$ISCC){
        $found=Get-Command ISCC.exe -ErrorAction SilentlyContinue
        if($found){$ISCC=$found.Source}
        else{$ISCC=@("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe","$env:ProgramFiles\Inno Setup 6\ISCC.exe","$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe")|Where-Object {Test-Path -LiteralPath $_}|Select-Object -First 1}
    }
    if(!$ISCC){throw 'Install Inno Setup 6 or pass -ISCC with its compiler path.'}
    & $ISCC /Q ClaimViewer.iss
    if($LASTEXITCODE){throw 'Setup compilation failed.'}
    $definition=[IO.File]::ReadAllText((Join-Path $root 'ClaimViewer.iss'))
    $version=[regex]::Match($definition,'#define AppVersion "([^"]+)"').Groups[1].Value
    $installer=Join-Path $root "release\ClaimViewer-Setup-$version.exe"
    $checksum=(Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLower()+'  '+[IO.Path]::GetFileName($installer)+"`r`n"
    [IO.File]::WriteAllText(($installer+'.sha256'),$checksum,[Text.UTF8Encoding]::new($false))
    Write-Output "Release built and verified: $installer"
}finally{Set-Location -LiteralPath $previous}
