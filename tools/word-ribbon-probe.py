import pythoncom
import win32com.client
import winreg
pythoncom.CoInitialize()
app=win32com.client.DispatchEx('Word.Application')
try:
    app.COMAddIns.Update()
    print('Word',app.Version,app.Path,'addins',app.COMAddIns.Count)
    for i in range(1,app.COMAddIns.Count+1):
        a=app.COMAddIns.Item(i)
        print(a.ProgId,a.Connect)
    for name in ('Word','Word.Application'):
        try:
            k=winreg.OpenKey(winreg.HKEY_CURRENT_USER,rf'Software\Microsoft\Office\{name}\Addins\ClaimViewer.Word')
            print('registry',name,winreg.QueryValueEx(k,'LoadBehavior')[0])
        except OSError as e:
            print('registry',name,type(e).__name__)
finally:
    app.Quit()
    pythoncom.CoUninitialize()
