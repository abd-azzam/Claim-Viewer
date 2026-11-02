using System;
using System.Runtime.InteropServices;
using System.Reflection;
using Office = Microsoft.Office.Core;
[assembly: AssemblyVersion("2.4.0.0")]
[assembly: ComVisible(true)]
namespace ClaimViewerWord {
 [ComVisible(true), Guid("908A5489-769B-4BB8-855A-7BB05A1E2158"), ProgId("ClaimViewer.Citations"), ClassInterface(ClassInterfaceType.AutoDispatch)]
 public class Connect : Extensibility.IDTExtensibility2, Office.IRibbonExtensibility, Office.ICustomTaskPaneConsumer {
  public static object Application;
  Office.ICTPFactory factory;
  readonly System.Collections.Generic.Dictionary<int,Office.CustomTaskPane> panes=new System.Collections.Generic.Dictionary<int,Office.CustomTaskPane>();
  public void CTPFactoryAvailable(Office.ICTPFactory value) { factory=value; }
  public void OnConnection(object app, Extensibility.ext_ConnectMode mode, object addin, ref Array custom) { Application=app; ((dynamic)addin).Object=this; }
  public void OnDisconnection(Extensibility.ext_DisconnectMode reason, ref Array custom) {}
  public void OnAddInsUpdate(ref Array custom) {}
  public void OnStartupComplete(ref Array custom) {}
  public void OnBeginShutdown(ref Array custom) {}
  public string GetCustomUI(string ribbonId) {
   return "<customUI xmlns='http://schemas.microsoft.com/office/2006/01/customui'><ribbon><tabs><tab id='cvTab' label='Claim Viewer'><group id='cvCitations' label='Citations'><button id='cvOpen' label='Insert citation' size='large' onAction='OpenPanel' imageMso='CitationInsert'/><button id='cvBib' label='Add bibliography' size='large' onAction='AddBibliography' imageMso='BibliographyInsert'/><button id='cvUpdate' label='Refresh' size='large' onAction='RefreshCitations' imageMso='RefreshAll'/><button id='cvStyle' label='Citation style' size='large' onAction='ChooseStyle' imageMso='BibliographyStyle'/></group></tab></tabs></ribbon></customUI>";
  }
  CitationPane GetPane(){if(factory==null)throw new InvalidOperationException("Restart Word to load the Claim Viewer ribbon.");if(((dynamic)Application).Documents.Count==0)throw new InvalidOperationException("Open a Word document first.");int window=(int)((dynamic)Application).ActiveWindow.Hwnd;Office.CustomTaskPane pane;if(!panes.TryGetValue(window,out pane)){pane=factory.CreateCTP("ClaimViewer.WordPane","Claim Viewer",Type.Missing);pane.Width=620;panes[window]=pane;}pane.Visible=true;return (CitationPane)pane.ContentControl;}
  void RunRibbon(string action){try{GetPane().RibbonAction(action);}catch(Exception e){System.Windows.Forms.MessageBox.Show(e.Message,"Claim Viewer");}}
  public void AddBibliography([MarshalAs(UnmanagedType.IDispatch)] object control){RunRibbon("bibliography");}
  public void RefreshCitations([MarshalAs(UnmanagedType.IDispatch)] object control){RunRibbon("refresh");}
  public void ChooseStyle([MarshalAs(UnmanagedType.IDispatch)] object control){RunRibbon("choose-style");}
  public void OpenPanel([MarshalAs(UnmanagedType.IDispatch)] object control) {
   try {
    GetPane().RefreshLibrary();
   } catch(Exception e){System.Windows.Forms.MessageBox.Show(e.Message,"Claim Viewer");}
  }
 }
}
