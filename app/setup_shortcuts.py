import os, subprocess, sys
import tkinter as tk
from tkinter import messagebox
here = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
app = os.path.join(here, "ClaimViewer.exe")
if not os.path.exists(app):  # no console in this exe, so errors go in a message box
    tk.Tk().withdraw(); messagebox.showerror("Claim Viewer Setup", "Put Setup next to ClaimViewer.exe and run it again."); sys.exit(1)
p = here.replace("/", "\\").split("\\")
tail = p[-3:-1] if p[-1].lower().replace(" ", "") == "claimviewer" else p[-2:]
name = "Claim Viewer - " + " ".join(tail).replace(":", "")
for ch in r'<>:"/\|?*': name = name.replace(ch, "")
ps = ("$s=New-Object -ComObject WScript.Shell;"
      "foreach($d in @([Environment]::GetFolderPath('Desktop'),[Environment]::GetFolderPath('Programs'))){"
      "$l=$s.CreateShortcut((Join-Path $d ($env:CV_NAME+'.lnk')));$l.TargetPath=$env:CV_APP;$l.WorkingDirectory=$env:CV_HERE;$l.Save()}")
env = dict(os.environ, CV_NAME=name, CV_APP=app, CV_HERE=here)  # values travel as env vars, so quotes in a path cannot break the script
def install():
    try: subprocess.check_call(["powershell", "-NoProfile", "-Command", ps], env=env, creationflags=0x08000000)  # no console window
    except Exception as e: return messagebox.showerror("Claim Viewer Setup", f"Setup failed: {e}")
    messagebox.showinfo("Claim Viewer Setup", f"Done. '{name}' is now on the Desktop and in the Start menu.")
    w.destroy()
w = tk.Tk(); w.title("Claim Viewer Setup"); w.geometry("460x210"); w.resizable(False, False)
tk.Label(w, text="Claim Viewer Setup", font=("Segoe UI", 14, "bold")).pack(pady=(18, 4))
tk.Label(w, text="This adds a Desktop and Start menu shortcut for:\n" + here, justify="left", wraplength=420).pack(pady=4)
b = tk.Frame(w); b.pack(side="bottom", pady=16)
tk.Button(b, text="Install", width=12, command=install).pack(side="left", padx=6)
tk.Button(b, text="Cancel", width=12, command=w.destroy).pack(side="left", padx=6)
w.mainloop()
