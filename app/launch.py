import ctypes, hashlib, http.server, os, socketserver, sys, threading
root = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
os.chdir(root)
def stop(msg):  # the exe has no console, so errors go in a message box
    ctypes.windll.user32.MessageBoxW(0, msg, "Claim Viewer", 0x10); sys.exit(1)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def end_headers(self):  # WebView2 caches pages; without this a rebuilt index.html can show old code
        self.send_header("Cache-Control", "no-cache"); super().end_headers()
socketserver.TCPServer.allow_reuse_address = True
h = hashlib.md5(root.lower().encode()).hexdigest()
port = 8765 + int(h[:4], 16) % 2000  # one fixed port per folder: localStorage is per origin, so saved claims stay put
try: srv = socketserver.ThreadingTCPServer(("127.0.0.1", port), Q)
except OSError: stop(f"Port {port} is busy. This folder may already be open in another window.")
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{port}/index.html"
# own native window (WebView2 inside ClaimViewer.exe, no browser); own storage per folder keeps saved edits
import webview
webview.settings["ALLOW_DOWNLOADS"] = True
store = os.path.join(os.environ.get("LOCALAPPDATA") or root, "ClaimViewer", "p-" + h[:8])
class Api:
    def save_pdf(self, name, b64):  # PDF-only save dialog; returns the saved path, or "" if cancelled
        import base64
        r = webview.windows[0].create_file_dialog(webview.FileDialog.SAVE, save_filename=name, file_types=("PDF files (*.pdf)",))
        if not r: return ""
        f = r if isinstance(r, str) else r[0]
        if not f.lower().endswith(".pdf"): f += ".pdf"
        open(f, "wb").write(base64.b64decode(b64)); return f
webview.create_window("Claim Viewer", url, js_api=Api(), width=1400, height=880, min_size=(900, 600), text_select=True)  # pywebview blocks text selection by default
webview.start(storage_path=store, private_mode=False)
os._exit(0)
