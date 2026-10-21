"""Build the installer with a throwaway AppId, install it to a temp folder, check the packaging, remove it.

    python test_installer.py

Why a throwaway AppId: Inno keys shortcuts and the uninstall entry on AppId. Installing a test
copy under the real AppId and then uninstalling it deletes the real app's Start-menu shortcut.
This script never touches the live app.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ISCC = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe"
if not ISCC.exists():
    ISCC = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe"
if not ISCC.exists():
    sys.exit("ISCC.exe not found. winget install JRSoftware.InnoSetup")

for need in ("dist/ClaimViewer.exe", "dist/index.html", "dist/sources.js", "dist/lib"):
    if not (HERE / need).exists():
        sys.exit("missing %s: run build_exe.bat first" % need)

def app_running():
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq ClaimViewer.exe", "/NH"],
                       capture_output=True, text=True, errors="replace")
    return "ClaimViewer.exe" in (r.stdout or "")

def find_app():
    for d in (Path(r"C:\Apps\ClaimViewer"),
              Path(os.environ.get("USERPROFILE", "")) / "Documents" / "Claim Viewer"):
        exe = d / "ClaimViewer.exe"
        if exe.exists():
            return exe
    return None

# a silent install aborts with code 5 while the app holds its files, so park it and put it back
was_running = app_running()
app_exe = find_app() if was_running else None
if was_running:
    subprocess.run(["taskkill", "/IM", "ClaimViewer.exe"], capture_output=True)
    for _ in range(20):
        if not app_running():
            break
        time.sleep(0.5)
    if app_running():
        subprocess.run(["taskkill", "/F", "/IM", "ClaimViewer.exe"], capture_output=True)
        time.sleep(1)
    print("closed the running app for the test")

work = Path(tempfile.mkdtemp(prefix="cvtest-"))
iss = HERE / "_test_installer.iss"
src = (HERE / "ClaimViewer.iss").read_text(encoding="utf-8")
# a name of its own too: the uninstaller removes shortcuts by name, whatever the AppId
src = re.sub(r'#define AppName "[^"]*"', '#define AppName "Claim Viewer (test)"', src, count=1)
src = re.sub(r"AppId=\{\{[^}]+\}", "AppId={{11111111-2222-3333-4444-%012d}" % (uuid.uuid4().int % 10**12), src, count=1)
src = re.sub(r"^OutputDir=.*$", lambda m: "OutputDir=" + str(work), src, count=1, flags=re.M)
src = re.sub(r"^OutputBaseFilename=.*$", "OutputBaseFilename=claimviewer-test", src, count=1, flags=re.M)
iss.write_text(src, encoding="utf-8")

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

try:
    r = run([str(ISCC), str(iss)])
    setup = work / "claimviewer-test.exe"
    if r.returncode or not setup.exists():
        print((r.stdout or "")[-1500:])
        sys.exit("ISCC failed")

    appdir = work / "app"
    r = run([str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/NOICONS", "/DIR=" + str(appdir)])
    if r.returncode:
        sys.exit("installer failed: %s" % (r.stderr or r.stdout))

    problems = []
    for f in ("ClaimViewer.exe", "index.html", "sources.js", "lib/pdf.min.js", "lib/pdf.worker.min.js", "lib/pdf-lib.min.js"):
        if not (appdir / f).exists():
            problems.append("missing " + f)
    page = appdir / "index.html"
    if page.exists():
        if page.stat().st_size > 1_048_576:
            problems.append("index.html is bigger than the empty reader page")
        text = page.read_text(encoding="utf-8")
        m = re.search(r"const DATA=(\{.*?\});", text, re.S)
        if not m:
            problems.append("index.html has no DATA block")
        else:
            n = len(json.loads(m.group(1)).get("sources", []))
            if n:
                problems.append("index.html carries %d readings: it is somebody's page" % n)

    live = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Claim Viewer.lnk"
    had_live = live.exists()

    unins = appdir / "unins000.exe"
    if unins.exists():
        run([str(unins), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"])
    if had_live and not live.exists():
        problems.append("the test install removed the real Start-menu shortcut")
    print("PASS" if not problems else "FAIL: " + "; ".join(problems))
    code = 0 if not problems else 1
    sys.exit(code)
finally:
    if was_running and app_exe and app_exe.exists():
        subprocess.Popen([str(app_exe)], cwd=str(app_exe.parent))
        print("restarted the app")
    iss.unlink(missing_ok=True)
    for _ in range(10):  # the uninstaller keeps user files and can hold the folder briefly
        shutil.rmtree(work, ignore_errors=True)
        if not work.exists():
            break
        time.sleep(0.5)
