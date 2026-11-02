param([switch]$Uninstall,[switch]$Machine)
$ErrorActionPreference='Stop'
$styles=@(Get-ChildItem -Path @("$env:ProgramFiles\Microsoft Office\root\Office16\Bibliography\Style","$env:ProgramFiles\Microsoft Office\Office16\Bibliography\Style","${env:ProgramFiles(x86)}\Microsoft Office\root\Office16\Bibliography\Style","${env:ProgramFiles(x86)}\Microsoft Office\Office16\Bibliography\Style") -Filter CHICAGO.XSL -ErrorAction SilentlyContinue)
if(!$Uninstall -and !$styles.Count){throw 'Word bibliography styles were not found; APSA installation could not finish.'}
if($Machine){$targets=@($styles | ForEach-Object {[pscustomobject]@{Folder=$_.DirectoryName;Chicago=$_.FullName}})}
else{
    $folder=Join-Path $env:APPDATA 'Microsoft\Bibliography\Style'
    $chicago=Join-Path $folder 'CHICAGO.XSL'
    if(!(Test-Path -LiteralPath $chicago) -and $styles.Count){$chicago=$styles[0].FullName}
    $targets=@([pscustomobject]@{Folder=$folder;Chicago=$chicago})
}
foreach($entry in $targets){
    $target=Join-Path $entry.Folder 'ClaimViewerAPSA.xsl'
    if($Uninstall){if(Test-Path -LiteralPath $target){Remove-Item -LiteralPath $target}}
    else{
        New-Item -Path $entry.Folder -ItemType Directory -Force|Out-Null
        # Word requires a self-contained stylesheet. Adapt the local renderer;
        # never redistribute Microsoft's stylesheet in the application package.
        $base=[Xml.XmlDocument]::new();$base.PreserveWhitespace=$true
        $base.LoadXml([IO.File]::ReadAllText($entry.Chicago))
        $overlay=[Xml.XmlDocument]::new();$overlay.PreserveWhitespace=$true
        $overlay.LoadXml([IO.File]::ReadAllText((Join-Path $PSScriptRoot 'APSA.xsl')))
        $ns=[Xml.XmlNamespaceManager]::new($base.NameTable)
        $ns.AddNamespace('x','http://www.w3.org/1999/XSL/Transform')
        $original=$base.SelectSingleNode('/x:stylesheet/x:template[@match="/"]',$ns)
        $original.RemoveAttribute('match');$original.SetAttribute('name','claimViewerChicago')
        foreach($template in $overlay.DocumentElement.ChildNodes | Where-Object {$_.LocalName -eq 'template'}){
            $name=$template.GetAttribute('name')
            if($name){$existing=$base.SelectSingleNode(('/x:stylesheet/x:template[@name="'+$name+'"]'),$ns);if($existing){[void]$existing.ParentNode.RemoveChild($existing)}}
            [void]$base.DocumentElement.AppendChild($base.ImportNode($template,$true))
        }
        $base.Save($target)
    }
}
Write-Output 'Claim Viewer APSA style updated.'
