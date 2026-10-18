; Inno Setup 6 script. Builds release\ClaimViewer-Setup-<version>.exe.
; Needs release\ClaimViewer.exe first (build_exe.bat makes it, then runs this script).
#define AppName "Claim Viewer"
#define AppVersion "1.0.0"

[Setup]
; Keep this AppId fixed: it is how a new setup finds the old install and upgrades it.
AppId={{80754954-3043-4550-991A-A9D2B0246EB4}
AppName={#AppName}
AppVersion={#AppVersion}
VersionInfoVersion={#AppVersion}
; Documents, not Program Files: the user adds PDFs and edits sources.js in this folder.
DefaultDirName={userdocs}\{#AppName}
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
Source: "release\ClaimViewer.exe"; DestDir: "{app}"; Flags: ignoreversion
; index.html holds the user's claims data and sources.js their PDF list: never overwrite, never uninstall.
Source: "reader\index.html"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "reader\sources.js"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "LICENSE"; DestName: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\pdf"; Flags: uninsneveruninstall

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\ClaimViewer.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\ClaimViewer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ClaimViewer.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
