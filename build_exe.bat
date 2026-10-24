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
copy /y dist\ClaimViewer.exe "%APP%\ClaimViewer.exe" >nul || (
  echo Could not install the exe. Is ClaimViewer still running?
  exit /b 1
)
if exist "%APP%\dist" rmdir /s /q "%APP%\dist"
if exist "%APP%\build" rmdir /s /q "%APP%\build"
if not exist "%APP%\release" mkdir "%APP%\release"
copy /y release\ClaimViewer-Setup-2.1.0.exe "%APP%\release\" >nul 2>&1
echo Installed: %APP%\ClaimViewer.exe
rem both hashes must match: the installed app and the one the installer carries
certutil -hashfile dist\ClaimViewer.exe SHA256 | findstr /r /v "hash CertUtil"
certutil -hashfile "%APP%\ClaimViewer.exe" SHA256 | findstr /r /v "hash CertUtil"
