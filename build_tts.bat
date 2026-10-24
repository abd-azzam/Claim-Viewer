@echo off
set "PATH=C:\Users\HP\AppData\Local\hermes\hermes-agent\venv\Scripts;%PATH%"
cd /d "C:\Users\HP\Documents\UIII\claim-viewer-github"
python --version
pip install pywebview pyinstaller edge-tts
python app\make_reader.py
if exist dist rmdir /s /q dist
python -m PyInstaller --noconfirm --onefile --noconsole --collect-all webview --collect-all edge_tts --name ClaimViewer --distpath dist --workpath build --specpath build app\launch.py
if errorlevel 1 echo PYINSTALLER_FAILED & exit /b 1
copy /y reader\index.html dist\index.html >nul
copy /y reader\sources.js dist\sources.js >nul
xcopy /y /i reader\lib dist\lib >nul
echo BUILD_DONE
dir dist\ClaimViewer.exe
