@echo off
rem Builds release\ClaimViewer.exe, then release\ClaimViewer-Setup-<version>.exe (needs Inno Setup 6: winget install JRSoftware.InnoSetup)
set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" echo Inno Setup 6 not found. Run: winget install JRSoftware.InnoSetup && exit /b 1
pip install pywebview pyinstaller || exit /b 1
python -m PyInstaller --onefile --noconsole --collect-all webview --name ClaimViewer --distpath release --workpath build --specpath build app\launch.py || exit /b 1
"%ISCC%" ClaimViewer.iss || exit /b 1
