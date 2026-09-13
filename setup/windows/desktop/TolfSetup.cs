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
[assembly: AssemblyVersion("1.2.0.0")]
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
        Text = "TOLF VPN"; ClientSize = new Size(540,380); MinimumSize = Size;
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
        status.SetBounds(24,211,492,145); status.Anchor=AnchorStyles.Top|AnchorStyles.Left|AnchorStyles.Right; Controls.Add(status);
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
            status.Text=L("Checking Windows components…", "Проверяем компоненты Windows…", "Pārbauda Windows komponentus…");
            await Task.Run(() => Preflight());
            status.Text=L("Setting up the connection…", "Настраиваем соединение…", "Savienojuma iestatīšana…");
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
            status.Text=FailureMessage(ex is SetupException ? ex.Message : "WINDOWS_CONFIGURATION");
        } finally { busy=false; install.Enabled=true; link.Enabled=true; }
    }
    void InvalidLink(){status.Text=L("Paste the personal link from the TOLF website.","Вставьте персональную ссылку с сайта TOLF.","Ielīmējiet personīgo saiti no TOLF vietnes.");}
    string FailureMessage(string code) {
        switch(code) {
        case "POWERSHELL_VERSION": return L("Windows PowerShell 5.1 is required. Restore Windows components and try again.","Нужен Windows PowerShell 5.1. Восстановите компоненты Windows и повторите настройку.","Nepieciešams Windows PowerShell 5.1. Atjaunojiet Windows komponentus un mēģiniet vēlreiz.");
        case "FRAMEWORK": return L("Install .NET Framework 4.8 or later from Microsoft.","Установите .NET Framework 4.8 или новее с сайта Microsoft.","Instalējiet .NET Framework 4.8 vai jaunāku versiju no Microsoft.");
        case "WINDOWS_VERSION": return L("This installer requires Windows 10 or Windows 11.","Этот установщик рассчитан на Windows 10 и Windows 11.","Šim instalētājam nepieciešama Windows 10 vai Windows 11.");
        case "VPN_MODULE": return L("The Windows VpnClient module is unavailable. Restore the Windows VPN components.","Недоступен модуль Windows VpnClient. Восстановите системные компоненты VPN.","Windows VpnClient modulis nav pieejams. Atjaunojiet Windows VPN komponentus.");
        case "VPN_SERVICE": return L("A required VPN service is missing or disabled (RasMan, IKEEXT or PolicyAgent). Ask the Windows administrator to restore it.","Нужная служба VPN отсутствует или отключена (RasMan, IKEEXT или PolicyAgent). Обратитесь к администратору Windows для её восстановления.","Nepieciešamais VPN pakalpojums nav pieejams vai ir atspējots (RasMan, IKEEXT vai PolicyAgent). Sazinieties ar Windows administratoru.");
        case "SYSTEM_FILES": return L("Windows VPN system files are missing. Restore Windows components.","Отсутствуют системные файлы VPN. Восстановите компоненты Windows.","Trūkst Windows VPN sistēmas failu. Atjaunojiet Windows komponentus.");
        case "POLICY": return L("Windows policy restricts script execution. Ask your administrator to allow TOLF setup.","Политика Windows ограничивает выполнение сценариев. Попросите администратора разрешить установку TOLF.","Windows politika ierobežo skriptu izpildi. Lūdziet administratoram atļaut TOLF iestatīšanu.");
        case "PREFLIGHT_ACCESS": return L("Windows component checks failed. Ask your administrator to check access to PowerShell, VpnClient and CIM. VPN settings were not changed.","Не удалось проверить компоненты Windows. Администратору нужно проверить доступ к PowerShell, VpnClient и CIM. Настройки VPN не изменены.","Neizdevās pārbaudīt Windows komponentus. Administratoram jāpārbauda piekļuve PowerShell, VpnClient un CIM. VPN iestatījumi nav mainīti.");
        default: return L("Setup failed. Diagnostic code: ","Настройка не завершена. Диагностический код: ","Iestatīšana neizdevās. Diagnostikas kods: ")+code;
        }
    }
    void Preflight() {
        using (var key=Microsoft.Win32.Registry.LocalMachine.OpenSubKey(@"SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full")) {
            if(key==null || Convert.ToInt32(key.GetValue("Release",0))<528040) throw new SetupException("FRAMEWORK");
        }
        string system=Environment.GetFolderPath(Environment.SpecialFolder.System);
        string powershell=Path.Combine(system,@"WindowsPowerShell\v1.0\powershell.exe");
        if(!File.Exists(powershell)) throw new SetupException("POWERSHELL_VERSION");
        foreach(string file in new[]{"rasdial.exe","rasapi32.dll"})
            if(!File.Exists(Path.Combine(system,file))) throw new SetupException("SYSTEM_FILES");
        string script;
        using(var reader=new StreamReader(Assembly.GetExecutingAssembly().GetManifestResourceStream("Preflight.ps1"))) script=reader.ReadToEnd();
        var start=new ProcessStartInfo(powershell,"-NoLogo -NoProfile -NonInteractive -EncodedCommand "+Convert.ToBase64String(Encoding.Unicode.GetBytes(script)));
        start.UseShellExecute=false; start.CreateNoWindow=true; start.RedirectStandardOutput=true; start.RedirectStandardError=true;
        try {
            using(var process=Process.Start(start)) {
                var output=process.StandardOutput.ReadToEndAsync(); var error=process.StandardError.ReadToEndAsync();
                if(!process.WaitForExit(30000)) { process.Kill(); throw new SetupException("PREFLIGHT_ACCESS"); }
                Task.WaitAll(output,error);
                var match=Regex.Match(output.Result,@"TOLF_ERROR:([A-Z0-9_]+)");
                if(match.Success) throw new SetupException(match.Groups[1].Value);
                if(process.ExitCode!=0 || !output.Result.Contains("TOLF_PREFLIGHT_OK")) throw new SetupException("PREFLIGHT_ACCESS");
            }
        } catch(System.ComponentModel.Win32Exception) { throw new SetupException("PREFLIGHT_ACCESS"); }
    }
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
