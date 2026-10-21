; Inno Setup 6 script. Builds release\ClaimViewer-Setup-<version>.exe.
; Needs dist\ClaimViewer.exe, dist\index.html (the empty reader page) and dist\lib first.
; build_exe.bat stages all three; a bare ISCC run packs whatever sits in dist\.
; Installs like a normal per-user app in C:\Apps\ClaimViewer, with a Start menu entry.
#define AppName "Claim Viewer"
#define AppVersion "2.1.0"
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
DefaultDirName={sd}\Apps\ClaimViewer
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

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\ClaimViewer.exe"; DestDir: "{app}"; Flags: ignoreversion
; pdf.js and pdf-lib, so the viewer works offline. Replaced on every upgrade.
Source: "dist\lib\*"; DestDir: "{app}\lib"; Flags: ignoreversion
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

[UninstallDelete]
; Only the uninstaller's own leftovers. index.html, sources.js, pdf/ and data/ are yours.
Type: files; Name: "{app}\*.tmp"
