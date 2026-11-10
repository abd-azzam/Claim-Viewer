param([string]$Python='python')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$compiler=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$office=Get-ChildItem (Join-Path $env:WINDIR 'assembly\GAC_MSIL\office') -Recurse -Filter office.dll | Select-Object -First 1 -ExpandProperty FullName
$extensibility=Get-ChildItem (Join-Path $env:WINDIR 'assembly\GAC\Extensibility') -Recurse -Filter Extensibility.dll | Select-Object -First 1 -ExpandProperty FullName
if(!$office){throw 'Microsoft Office interop assembly is required to build the ribbon.'}
$web=(& $Python -c "import pathlib,webview;print(pathlib.Path(webview.__file__).parent/'lib')").Trim()
if($LASTEXITCODE -ne 0){throw 'Install pywebview in the selected Python environment.'}
foreach($name in @('Microsoft.Web.WebView2.Core.dll','Microsoft.Web.WebView2.WinForms.dll')){Copy-Item -LiteralPath (Join-Path $web $name) -Destination (Join-Path $root 'word') -Force}
foreach($arch in @('win-x64','win-x86')){$destination=Join-Path $root "word\runtimes\$arch\native";New-Item -Path $destination -ItemType Directory -Force|Out-Null;Copy-Item -LiteralPath (Join-Path $web "runtimes\$arch\native\WebView2Loader.dll") -Destination $destination -Force}
& $compiler /nologo /target:library /platform:anycpu /optimize+ ("/out:"+(Join-Path $root 'word\ClaimViewerWord.dll')) ("/link:"+$office+","+$extensibility) /reference:word\Microsoft.Web.WebView2.Core.dll /reference:word\Microsoft.Web.WebView2.WinForms.dll /reference:System.dll /reference:System.Core.dll /reference:System.Net.Http.dll /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:System.Web.Extensions.dll /reference:Microsoft.CSharp.dll (Join-Path $root 'word\Ribbon.cs') (Join-Path $root 'word\CitationPane.cs')
if($LASTEXITCODE -ne 0){throw 'Word ribbon compilation failed.'}
