using System;
using System.Drawing;
using System.IO;
using System.Net.Http;
using System.Runtime.InteropServices;
using System.Security.Authentication;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using System.Collections.Generic;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;
namespace ClaimViewerWord {
 [ComVisible(true), Guid("FF33A1A7-BFE3-4CA3-9809-13717A51FDF8"), ProgId("ClaimViewer.WordPane"), ClassInterface(ClassInterfaceType.AutoDispatch)]
 public class CitationPane : UserControl {
  readonly WebView2 view=new WebView2{Dock=DockStyle.Fill,DefaultBackgroundColor=Color.FromArgb(20,23,28)};
  readonly JavaScriptSerializer json=new JavaScriptSerializer();
  Task initialization;
  string trustedSource;
  public CitationPane(){Dock=DockStyle.Fill;Controls.Add(view);}
  string Root(){var configured=Microsoft.Win32.Registry.GetValue(@"HKEY_CURRENT_USER\Software\ClaimViewer","WordRoot",null) as string;if(!String.IsNullOrEmpty(configured))return configured;var path=Directory.GetParent(typeof(CitationPane).Assembly.Location).Parent.FullName;var pointer=Path.Combine(path,"data-root.txt");return File.Exists(pointer)?File.ReadAllText(pointer).Trim():path;}
  Task Ready(){return initialization??(initialization=Initialize());}
  static void UiContext(){if(!(SynchronizationContext.Current is WindowsFormsSynchronizationContext))SynchronizationContext.SetSynchronizationContext(new WindowsFormsSynchronizationContext());}
  async Task Initialize(){
   UiContext();
   var assembly=Path.GetDirectoryName(typeof(CitationPane).Assembly.Location);
   CoreWebView2Environment.SetLoaderDllFolderPath(Path.Combine(assembly,"runtimes",IntPtr.Size==8?"win-x64":"win-x86","native"));
   var profile=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"ClaimViewer","WordWebView");
   var environment=await CoreWebView2Environment.CreateAsync(null,profile);
   await view.EnsureCoreWebView2Async(environment);
   view.CoreWebView2.Settings.AreDevToolsEnabled=false;view.CoreWebView2.Settings.AreDefaultContextMenusEnabled=false;
   view.CoreWebView2.NewWindowRequested+=(s,e)=>e.Handled=true;
   view.CoreWebView2.WebMessageReceived+=Message;
   var folder=Path.Combine(Root(),"word");var html=File.ReadAllText(Path.Combine(folder,"addin.html"));
   html=html.Replace("<html ","<html data-native ");
   html=Regex.Replace(html,@"<script\b[^>]*>[\s\S]*?</script>","",RegexOptions.IgnoreCase);
   html=html.Replace("<link rel=\"stylesheet\" href=\"word.css\">","<style>"+File.ReadAllText(Path.Combine(folder,"word.css"))+"</style>");
   html=html.Replace("</body>","<script>"+File.ReadAllText(Path.Combine(folder,"native-bridge.js"))+"</script><script>"+File.ReadAllText(Path.Combine(folder,"word.js"))+"</script></body>");
   var loaded=new TaskCompletionSource<bool>();EventHandler<CoreWebView2NavigationCompletedEventArgs> handler=null;
   handler=(s,e)=>{view.CoreWebView2.NavigationCompleted-=handler;if(e.IsSuccess)loaded.TrySetResult(true);else loaded.TrySetException(new InvalidOperationException("Citation pane could not load: "+e.WebErrorStatus));};
   view.CoreWebView2.NavigationCompleted+=handler;view.NavigateToString(html);await loaded.Task;
   trustedSource=view.CoreWebView2.Source;view.CoreWebView2.NavigationStarting+=(s,e)=>e.Cancel=true;
  }
  string Host(){dynamic app=Connect.Application;if(app==null||app.Documents.Count==0)throw new InvalidOperationException("Open a Word document.");dynamic doc=app.ActiveDocument;if(String.IsNullOrEmpty((string)doc.Path))throw new InvalidOperationException("Save this document, then refresh.");return (string)doc.FullName;}
  async Task<object> Call(string method,object[] args){
   var config=(Dictionary<string,object>)json.DeserializeObject(File.ReadAllText(Path.Combine(Root(),"word","service-config.json")));
   using(var handler=new HttpClientHandler{SslProtocols=SslProtocols.Tls12,UseProxy=false})using(var client=new HttpClient(handler)){
    client.Timeout=TimeSpan.FromSeconds(30);client.DefaultRequestHeaders.Add("Authorization","Bearer "+(string)config["token"]);
    using(var body=new StringContent(json.Serialize(new{method=method,args=args}),Encoding.UTF8,"application/json"))using(var response=await client.PostAsync("https://127.0.0.1:38491/api",body)){
     var reply=(Dictionary<string,object>)json.DeserializeObject(await response.Content.ReadAsStringAsync());object result;if(!reply.TryGetValue("result",out result))throw new InvalidOperationException(Convert.ToString(reply["error"]));return result;
    }
   }
  }
  async void Message(object sender,CoreWebView2WebMessageReceivedEventArgs e){
   UiContext();
   if(e.Source!=trustedSource)return;
   object id=null;object result=null;string error=null;
   try{
    var request=(Dictionary<string,object>)json.DeserializeObject(e.WebMessageAsJson);id=request["id"];var method=(string)request["method"];var args=(object[])request["args"];
    if(method!="word_sources"&&method!="word_action")throw new InvalidOperationException("Unsupported citation action.");
    if(method=="word_action"){
     var payload=args.Length>1?(Dictionary<string,object>)json.DeserializeObject((string)args[1]):new Dictionary<string,object>();
     payload["host_document"]=Host();args=new object[]{args[0],json.Serialize(payload)};
    }
    result=await Call(method,args);
   }catch(Exception exception){error=exception.Message;}
   if(!view.IsDisposed)view.CoreWebView2.PostWebMessageAsJson(json.Serialize(new{id=id,result=result,error=error}));
  }
  public async void RefreshLibrary(){if(IsDisposed)return;if(InvokeRequired){BeginInvoke(new Action(RefreshLibrary));return;}UiContext();try{await Ready();await view.ExecuteScriptAsync("refreshLibrary()");}catch(Exception e){MessageBox.Show(e.Message,"Claim Viewer");}}
  public async void RibbonAction(string action){if(IsDisposed)return;if(InvokeRequired){BeginInvoke(new Action(()=>RibbonAction(action)));return;}UiContext();try{await Ready();await view.ExecuteScriptAsync("cvRibbonAction("+json.Serialize(action)+")");}catch(Exception e){MessageBox.Show(e.Message,"Claim Viewer");}}
 }
}
