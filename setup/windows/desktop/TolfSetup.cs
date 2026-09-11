using System;
using System.Drawing;
using System.IO;
using System.Net;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Diagnostics;
using System.Web.Script.Serialization;
using System.Collections.Generic;
using System.Reflection;
[assembly: AssemblyTitle("TOLF VPN Setup")]
[assembly: AssemblyCompany("TOLF")]
[assembly: AssemblyVersion("1.1.0.0")]
class TolfSetup : Form {
    TextBox link = new TextBox();
    Label status = new Label();
    Button install = new Button();
    bool busy;
    string token;
    string language;
    string L(string en, string ru, string lv) { return language == "ru" ? ru : language == "lv" ? lv : en; }
    [STAThread] static void Main() {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new TolfSetup());
    }
    public TolfSetup() {
        language = System.Globalization.CultureInfo.CurrentUICulture.TwoLetterISOLanguageName;
        Text = "TOLF VPN"; ClientSize = new Size(540,310); MinimumSize = Size;
        StartPosition = FormStartPosition.CenterScreen;
        Font = new Font("Segoe UI", 10); BackColor = Color.White;
        AutoScaleMode = AutoScaleMode.Dpi;
        var title = new Label {Text=L("Set up TOLF VPN", "Настройка TOLF VPN", "TOLF VPN iestatīšana"), Font=new Font("Segoe UI",18,FontStyle.Bold), AutoSize=true, Location=new Point(24,22)};
        Controls.Add(title);
        var help = new Label {Text=L("Your personal setup link", "Персональная ссылка настройки", "Personīgā iestatīšanas saite"), AutoSize=true, Location=new Point(24,76)};
        Controls.Add(help);
        link.SetBounds(24,104,492,32); link.Anchor = AnchorStyles.Top|AnchorStyles.Left|AnchorStyles.Right;
        var match = Regex.Match(Path.GetFileName(Application.ExecutablePath), @"^TOLF-Setup-([A-Za-z0-9_-]{32})(?:\s*\(\d+\))?\.exe$", RegexOptions.IgnoreCase);
        if (match.Success) link.Text = "https://api.tolf.is/windows/p/"+match.Groups[1].Value;
        Controls.Add(link);
        install.Text = L("Set up and connect", "Настроить и подключиться", "Iestatīt un savienot");
        install.SetBounds(24,153,492,44); install.Anchor=AnchorStyles.Top|AnchorStyles.Left|AnchorStyles.Right;
        install.Click += async (s,e) => await Setup(); Controls.Add(install);
        status.SetBounds(24,211,492,80); status.Anchor=AnchorStyles.Top|AnchorStyles.Left|AnchorStyles.Right; Controls.Add(status);
        AcceptButton = install;
        FormClosing += (s,e) => { if(busy) e.Cancel=true; };
    }
    async Task Setup() {
        Uri url;
        if(!Uri.TryCreate(link.Text.Trim(), UriKind.Absolute, out url) || url.Scheme!="https" || url.Host!="api.tolf.is" || !url.IsDefaultPort || url.UserInfo!="" || url.Query!="" || url.Fragment!="") { InvalidLink(); return; }
        var match = Regex.Match(url.AbsolutePath,@"^/windows/p/([A-Za-z0-9_-]{32})/?$");
        if(!match.Success) { InvalidLink(); return; }
        token=match.Groups[1].Value;
        busy=true; install.Enabled=false; link.Enabled=false;
        status.Text=L("Setting up the connection…", "Настраиваем соединение…", "Savienojuma iestatīšana…");
        try {
            string name = await Task.Run(() => Configure());
            status.Text=L("Connecting…", "Подключаемся…", "Savienojas…");
            int code=await Task.Run(() => RunDial(name));
            if(code!=0) {
                status.Text=L("VPN is configured. Connection failed. Windows code: ","VPN настроен. Подключиться не удалось. Код Windows: ","VPN iestatīts. Savienojums neizdevās. Windows kods: ")+code;
            } else {
                status.Text=L("Connected. Your VPN is available in Windows Settings → Network & Internet → VPN.","Подключено. VPN доступен в Параметрах Windows → Сеть и Интернет → VPN.","Savienots. VPN pieejams Windows iestatījumos → Tīkls un internets → VPN.");
            }
        } catch(WebException) {
            status.Text=L("Could not retrieve settings. Check your Internet connection or create a new setup link on the TOLF website.","Не удалось получить настройки. Проверьте интернет или создайте новую ссылку на сайте TOLF.","Neizdevās saņemt iestatījumus. Pārbaudiet internetu vai izveidojiet jaunu saiti TOLF vietnē.");
        } catch(Exception ex) {
            // No server payloads, credentials or personal links in error messages.
            status.Text=L("Setup failed. Error: ","Настройка не завершена. Ошибка: ","Iestatīšana neizdevās. Kļūda: ")+(ex is SetupException ? ex.Message : ex.GetType().Name);
        } finally { busy=false; install.Enabled=true; link.Enabled=true; }
    }
    void InvalidLink(){status.Text=L("Paste the personal link from the TOLF website.","Вставьте персональную ссылку с сайта TOLF.","Ielīmējiet personīgo saiti no TOLF vietnes.");}
    string Configure() {
        ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
        var request=(HttpWebRequest)WebRequest.Create("https://api.tolf.is/windows/p/"+token+"/settings");
        request.Method="POST"; request.ContentLength=0; request.Timeout=30000; request.ReadWriteTimeout=30000; request.AllowAutoRedirect=false;
        string json;
        using(var response=(HttpWebResponse)request.GetResponse())
        using(var reader=new StreamReader(response.GetResponseStream(),Encoding.UTF8)) {
            if(response.StatusCode!=HttpStatusCode.OK) throw new WebException();
            char[] buffer=new char[8193]; int count=0,n;
            while(count<buffer.Length && (n=reader.Read(buffer,count,buffer.Length-count))>0) count+=n;
            if(count>8192) throw new SetupException("Invalid settings");
            json=new string(buffer,0,count);
        }
        var config = new JavaScriptSerializer().Deserialize<Dictionary<string,string>>(json);
        Guid id;
        if(!config.ContainsKey("deviceId") || !Guid.TryParse(config["deviceId"],out id) || !config.ContainsKey("server") || config["server"]!="ikev2-riga.tolf.is" || !config.ContainsKey("username") || config["username"]!="user_"+id.ToString("N") || !config.ContainsKey("password") || config["password"].Length==0 || config["password"].Length>256) throw new SetupException("Invalid settings");
        string script;
        using(var reader=new StreamReader(Assembly.GetExecutingAssembly().GetManifestResourceStream("Configure.ps1"))) script=reader.ReadToEnd();
        var start=new ProcessStartInfo(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System),@"WindowsPowerShell\v1.0\powershell.exe"), "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand "+Convert.ToBase64String(Encoding.Unicode.GetBytes(script)));
        start.UseShellExecute=false; start.CreateNoWindow=true; start.RedirectStandardInput=true; start.RedirectStandardOutput=true; start.RedirectStandardError=true;
        using(var process=Process.Start(start)) {
            var output=process.StandardOutput.ReadToEndAsync(); var error=process.StandardError.ReadToEndAsync();
            // Only an anonymous pipe carries credentials; never argv or disk.
            process.StandardInput.Write(Convert.ToBase64String(Encoding.UTF8.GetBytes(json))); process.StandardInput.Close();
            json=null; config["password"]=null;
            if(!process.WaitForExit(120000)) {process.Kill(); throw new SetupException("Setup timeout");}
            Task.WaitAll(output,error);
            if(process.ExitCode!=0) {
                var result=Regex.Match(output.Result,@"TOLF_ERROR:([A-Z0-9_]+)");
                throw new SetupException(result.Success ? result.Groups[1].Value : "WINDOWS_CONFIGURATION");
            }
        }
        return "TOLF - Riga - "+id.ToString();
    }
    int RunDial(string name) {
        var start=new ProcessStartInfo(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System),"rasdial.exe"),"\""+name+"\"");
        start.UseShellExecute=false; start.CreateNoWindow=true; start.RedirectStandardOutput=true; start.RedirectStandardError=true;
        using(var process=Process.Start(start)) {
            var a=process.StandardOutput.ReadToEndAsync(); var b=process.StandardError.ReadToEndAsync();
            if(!process.WaitForExit(90000)) {process.Kill(); return 1460;}
            Task.WaitAll(a,b); return process.ExitCode;
        }
    }
    class SetupException:Exception { public SetupException(string message):base(message){} }
}
