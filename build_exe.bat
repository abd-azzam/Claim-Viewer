@echo off
rem Builds dist\ClaimViewer.exe, stages the empty reader page and the pdf.js libs, then release\ClaimViewer-Setup-<version>.exe
rem Needs Inno Setup 6: winget install JRSoftware.InnoSetup
set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" echo Inno Setup 6 not found. Run: winget install JRSoftware.InnoSetup && exit /b 1
pip install pywebview pyinstaller || exit /b 1
python app\make_reader.py || exit /b 1
python -m PyInstaller --noconfirm --onefile --noconsole --collect-all webview --name ClaimViewer --distpath dist --workpath build --specpath build app\launch.py || exit /b 1
rem the installer ships the EMPTY reader page: a page holding a user's claims must never be packaged
copy /y reader\index.html dist\index.html >nul || exit /b 1
copy /y reader\sources.js dist\sources.js >nul || exit /b 1
xcopy /y /i reader\lib dist\lib >nul || exit /b 1
rem the empty page is about 200 KB; a page with claims is about 6 MB, so refuse to pack it
for %%A in (dist\index.html) do if %%~zA GTR 1000000 (
  echo dist\index.html is too big to be the empty reader page. Refusing to package it.
  exit /b 1
)
"%ISCC%" ClaimViewer.iss || exit /b 1
