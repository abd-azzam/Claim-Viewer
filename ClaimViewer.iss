; Inno Setup 6 script. Builds release\ClaimViewer-Setup-<version>.exe.
; Needs dist\ClaimViewer.exe, dist\index.html (the empty reader page) and dist\lib first.
; tools/build-release.ps1 builds, verifies and stages the distribution.
#define AppName "Claim Viewer"
#define AppVersion "2.6.0"
; A page holding someone's claims is ~6 MB; the empty reader page is ~200 KB.
; This refuses to package a page that big, whatever ran before ISCC.
#if FileExists("dist\index.html")
  #if FileSize("dist\index.html") > 1048576
    #error "dist\index.html is too big to be the empty reader page. Refusing to package a personal page."
  #endif
#endif

[Setup]
; Keep this AppId fixed: it is how a new setup finds the old install and upgrades it.
AppId={{80754954-3043-4550-991A-A9D2B0246EB4}
AppName={#AppName}
AppVersion={#AppVersion}
VersionInfoVersion={#AppVersion}
AppPublisher=Azzam Abdullah
; The app folder, not Program Files: no admin needed, and the library PDFs live here.
DefaultDirName={localappdata}\Programs\Claim Viewer
MinVersion=10.0.17763
DisableDirPage=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=release
OutputBaseFilename=ClaimViewer-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\ClaimViewer.exe
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "wordaddin"; Description: "Add Claim Viewer to Microsoft Word's ribbon (administrator approval required)"; GroupDescription: "Integrations:"; Check: IsWordInstalled
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\ClaimViewer.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "release\prerequisites\MicrosoftEdgeWebview2Setup.exe"; Flags: dontcopy
; pdf.js and pdf-lib, so the viewer works offline. Replaced on every upgrade.
Source: "dist\lib\*"; DestDir: "{app}\lib"; Flags: ignoreversion
Source: "dist\word\*"; DestDir: "{app}\word"; Flags: ignoreversion recursesubdirs
Source: "dist\tools\*"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "dist\template\template.html"; DestDir: "{app}\template"; Flags: ignoreversion
Source: "dist\library.json"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall
; The page and the reading list: user data, never replaced on upgrade, never uninstalled.
Source: "dist\index.html"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall skipifsourcedoesntexist
Source: "dist\sources.js"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall skipifsourcedoesntexist

[Dirs]
Name: "{app}\pdf"; Flags: uninsneveruninstall
Name: "{app}\data"; Flags: uninsneveruninstall

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\ClaimViewer.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\ClaimViewer.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\ClaimViewer.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\word\uninstall-web-addin.ps1"""; Tasks: wordaddin; RunOnceId: "ClaimViewerWord"; Flags: runhidden waituntilterminated

[UninstallDelete]
; Only the uninstaller's own leftovers. index.html, sources.js, pdf/ and data/ are yours.
Type: files; Name: "{app}\*.tmp"

[Code]
function IsWordInstalled: Boolean;
begin
  Result := RegKeyExists(HKCR64, 'Word.Application\CLSID') or
    RegKeyExists(HKCR32, 'Word.Application\CLSID');
end;

function HasWebView2: Boolean;
var Version: String;
begin
  Result := (RegQueryStringValue(HKLM32, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0')) or
    (RegQueryStringValue(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0'));
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var Code: Integer;
begin
  Result := '';
  if WizardIsTaskSelected('wordaddin') and (FindWindowByClassName('OpusApp') <> 0) then begin
    Result := 'Save your Word documents and close Word, then click Next to continue. Or go back and clear the Word ribbon option.';
    Exit;
  end;
  if not HasWebView2 then begin
    ExtractTemporaryFile('MicrosoftEdgeWebview2Setup.exe');
    if not Exec(ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe'), '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, Code) then begin
      Result := 'Microsoft WebView2 could not start. Install the Evergreen Runtime from https://developer.microsoft.com/microsoft-edge/webview2/ and retry.';
      Exit;
    end;
    if not HasWebView2 then
      Result := 'Microsoft WebView2 installation did not finish. An internet connection is required. Install the Evergreen Runtime and retry.';
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var Code: Integer;
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('wordaddin') then begin
    WizardForm.StatusLabel.Caption := 'Installing the Word ribbon. Accept the Windows administrator prompt.';
    if not Exec(ExpandConstant('{app}\ClaimViewer.exe'), '--install-word', ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, Code) then
      Code := -1;
    if Code <> 0 then begin
      Log('Word integration failed, exit code: ' + IntToStr(Code));
      SuppressibleMsgBox('Claim Viewer is installed, but Word setup did not finish. Open Settings > Word Add-in > Install Word add-in to retry. Details: ' + ExpandConstant('{app}\word\installation-error.txt'), mbInformation, MB_OK, IDOK);
    end;
  end;
end;
