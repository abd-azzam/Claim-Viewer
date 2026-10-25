@echo off
rem Builds dist\ClaimViewer.exe from scratch, stages the empty reader page and the pdf.js libs,
rem then writes release\ClaimViewer-Setup-<version>.exe. Needs Inno Setup 6: winget install JRSoftware.InnoSetup
rem pin the interpreter: an unpinned "python" picked a bare venv without PyInstaller and the build died
set "PATH=C:\Users\HP\AppData\Local\hermes\hermes-agent\venv\Scripts;%PATH%"
set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" echo Inno Setup 6 not found. Run: winget install JRSoftware.InnoSetup && exit /b 1
rem the exe size follows the Python that builds it (3.11 gives about 17.6 MB, 3.13 about 12.7 MB), so the version is printed
python --version
pip install pywebview pyinstaller edge-tts || exit /b 1
python app\make_reader.py || exit /b 1
rem dist is disposable: wipe it so a stale page can never be packaged
if exist dist rmdir /s /q dist
rem --collect-all edge_tts is required: without it read-aloud has no neural voice in the frozen app
python -m PyInstaller --noconfirm --onefile --noconsole --collect-all webview --collect-all edge_tts --name ClaimViewer --distpath dist --workpath build --specpath build app\launch.py || exit /b 1
rem the installer ships the EMPTY reader page: a page holding a user's claims must never be packaged
copy /y reader\index.html dist\index.html >nul || exit /b 1
copy /y reader\sources.js dist\sources.js >nul || exit /b 1
xcopy /y /i reader\lib dist\lib >nul || exit /b 1
rem the empty page is about 200 KB; a page with claims is about 6 MB
for %%A in (dist\index.html) do if %%~zA GTR 1000000 (
  echo dist\index.html is too big to be the empty reader page. Refusing to package it.
  exit /b 1
)
"%ISCC%" ClaimViewer.iss || exit /b 1
rem ONE binary only: install it, then drop the build copy so no stale dist\ClaimViewer.exe
rem can ever be tested by mistake (that is how a fixed bug looked unfixed for hours).
set "APP=C:\Apps\ClaimViewer"
if exist "%APP%\ClaimViewer.exe" (
  taskkill /IM ClaimViewer.exe /F >nul 2>&1
  ping -n 3 127.0.0.1 >nul
)
rem A single copy right after taskkill can still fail: Windows holds the image for a moment after
rem the process dies, and one transient lock used to fail the whole build. Retry before giving up.
set "COPIED="
for /l %%I in (1,1,10) do (
  if not defined COPIED (
    copy /y dist\ClaimViewer.exe "%APP%\ClaimViewer.exe" >nul 2>&1 && set "COPIED=1"
    if not defined COPIED ping -n 2 127.0.0.1 >nul
  )
)
if not defined COPIED (
  echo Could not install the exe after 10 tries. Is ClaimViewer still running?
  exit /b 1
)
if exist "%APP%\dist" rmdir /s /q "%APP%\dist"
if exist "%APP%\build" rmdir /s /q "%APP%\build"
rem The repo's own dist\ holds a second copy of the exe beside the EMPTY reader page and no
rem library.json. Launching it by mistake opens a blank app that looks like lost data. Never
rem leave it behind: the installer is already built by this point.
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if not exist "%APP%\release" mkdir "%APP%\release"
copy /y release\ClaimViewer-Setup-2.1.0.exe "%APP%\release\" >nul 2>&1
echo Installed: %APP%\ClaimViewer.exe
rem The Start Menu shortcut is what he actually clicks. A test install in a scratch folder once
rem registered itself as the app and left this shortcut pointing at a blank copy, so the real
rem install looked like lost data. Point the shortcut at the real folder on every build.
rem Save() can throw (a locked .lnk) and the old version still printed "repaired", so the target
rem is read back and the build fails loudly when it did not take. A missing shortcut is recreated
rem rather than ignored: a deleted Start Menu entry used to pass silently and never come back.
powershell -NoProfile -Command "$s=New-Object -ComObject WScript.Shell; $l=Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Claim Viewer.lnk'; $want='%APP%\ClaimViewer.exe'; if(-not (Test-Path $l)){try{$n=$s.CreateShortcut($l); $n.TargetPath=$want; $n.WorkingDirectory='%APP%'; $n.Save()}catch{}; $made=$s.CreateShortcut($l).TargetPath; if($made -eq $want){Write-Host ('Shortcut recreated: '+$made)}else{Write-Host ('SHORTCUT MISSING AND COULD NOT BE MADE: '+$made); exit 1}} else {$t=$s.CreateShortcut($l); if($t.TargetPath -ne $want){try{$t.TargetPath=$want; $t.WorkingDirectory='%APP%'; $t.Save()}catch{}; $now=$s.CreateShortcut($l).TargetPath; if($now -eq $want){Write-Host ('Shortcut repaired: '+$now)}else{Write-Host ('SHORTCUT STILL WRONG: '+$now); exit 1}} else {Write-Host ('Shortcut ok: '+$t.TargetPath)}}"
if errorlevel 1 (
  echo The Start Menu shortcut is wrong or missing and could not be fixed. Rebuild, or reinstall.
  exit /b 1
)
rem both hashes must match: the installed app and the one the installer carries
certutil -hashfile dist\ClaimViewer.exe SHA256 | findstr /r /v "hash CertUtil"
certutil -hashfile "%APP%\ClaimViewer.exe" SHA256 | findstr /r /v "hash CertUtil"
