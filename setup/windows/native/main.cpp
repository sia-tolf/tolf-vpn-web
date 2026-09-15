#include "routes.h"
#include <thread>
#include <memory>
#include <initializer_list>
static HWND window,linkLabel,linkEdit,loadButton,stepLabel,pageTitle,introText,networkLabel,networkEdit,networkHelp,rdpHelp,saveButton,connectButton,status,footer;
static bool busy=false,hasFileToken=false;
static HFONT font,smallFont,titleFont,brandFont;
static HBRUSH whiteBrush;
static int lang=0;
static UINT dpi=96;
static const UINT Done=WM_APP+1;
static std::unique_ptr<Settings> settings;
static const wchar_t* L(const wchar_t*en,const wchar_t*ru,const wchar_t*lv){return lang==1?ru:lang==2?lv:en;}
static int px(int n){return MulDiv(n,dpi,96);}
static std::wstring Error(const Failure&f){
 std::wstring message;
 if(f.stage==L"CONNECT"&&f.code==ERROR_CANCELLED)return L(L"Connection cancelled. Settings are saved.",L"Подключение отменено. Настройки сохранены.",L"Savienojums atcelts. Iestatījumi saglabāti.");
 if(f.stage==L"LINK")message=L(L"Paste the personal setup link from TOLF.",L"Вставьте персональную ссылку настройки с сайта TOLF.",L"Ielīmējiet personīgo iestatīšanas saiti no TOLF.");
 else if(f.stage==L"NETWORK")message=L(L"Could not retrieve settings. Check the Internet connection or create a new setup link.",L"Не удалось получить настройки. Проверьте интернет или создайте новую ссылку настройки.",L"Neizdevās saņemt iestatījumus. Pārbaudiet internetu vai izveidojiet jaunu iestatīšanas saiti.");
 else if(f.stage==L"VPN_SERVICE"||f.stage==L"WINDOWS_COMPONENTS")message=L(L"A required Windows VPN component is unavailable or disabled. Ask your administrator to restore it.",L"Нужный системный компонент Windows недоступен или отключён. Обратитесь к администратору для его восстановления.",L"Nepieciešamais Windows komponents nav pieejams vai ir atspējots. Sazinieties ar administratoru.");
 else if(f.stage==L"NAME_CONFLICT")message=L(L"A different VPN connection already has this name. It was not changed.",L"Под этим именем уже существует другое VPN-подключение. Оно не изменено.",L"Ar šo nosaukumu jau ir cits VPN savienojums. Tas nav mainīts.");
 else if(f.stage==L"ROLLBACK")message=L(L"Setup failed and the new connection could not be removed. Check TOLF in Windows VPN settings.",L"Настройка не завершена, удалить новое подключение не удалось. Проверьте TOLF в настройках VPN Windows.",L"Iestatīšana neizdevās, un jauno savienojumu nevarēja noņemt. Pārbaudiet TOLF Windows VPN iestatījumos.");
 else if(f.stage==L"NETWORK_LIST")message=L(L"Enter IPv4 networks, one per line, e.g. 192.168.200.0/24. Use network addresses with prefixes /1 to /32; at most 32 networks.",L"Введите сети IPv4, по одной в строке, например 192.168.200.0/24. Нужен адрес сети с маской /1–/32; не более 32 сетей.",L"Ievadiet IPv4 tīklus, pa vienam rindā, piemēram, 192.168.200.0/24. Prefiksi /1–/32; ne vairāk par 32 tīkliem.");
 else if(f.stage==L"DISCONNECT_FIRST")message=L(L"Disconnect this VPN before changing its settings.",L"Перед изменением настроек отключите это VPN-соединение.",L"Pirms iestatījumu maiņas atvienojiet šo VPN.");
 else if(f.stage==L"ROUTE_CONFLICT")message=L(L"This profile has routing settings not managed by TOLF. Its routes were not changed.",L"В профиле есть настройки маршрутизации, заданные вне TOLF. Маршруты не изменены.",L"Profilā ir ārpus TOLF mainīti maršrutēšanas iestatījumi. Maršruti nav mainīti.");
 else if(f.stage==L"ROUTE_SETTINGS")message=L(L"Could not read or save this device's network preferences.",L"Не удалось прочитать или сохранить список сетей этого устройства.",L"Neizdevās nolasīt vai saglabāt ierīces tīklu iestatījumus.");
 else if(f.stage==L"ROUTE_ROLLBACK")message=L(L"Could not restore the previous VPN routes. Do not connect until the profile has been checked.",L"Не удалось восстановить прежние маршруты VPN. Перед подключением необходимо проверить профиль.",L"Neizdevās atjaunot iepriekšējos VPN maršrutus. Pirms savienošanās pārbaudiet profilu.");
 else if(f.stage==L"SHORTCUT")message=L(L"VPN settings were saved, but the TOLF shortcuts could not be installed. Close the old TOLF widget and try saving again.",L"Настройки VPN сохранены, но не удалось установить ярлыки TOLF. Закройте прежний виджет TOLF и повторите сохранение.",L"VPN iestatījumi saglabāti, bet TOLF saīsnes neizdevās instalēt. Aizveriet iepriekšējo logrīku un mēģiniet vēlreiz.");
 else if(f.stage==L"CREDENTIALS")message=L(L"Windows could not read or save VPN credentials.",L"Windows не удалось прочитать или сохранить учётные данные VPN.",L"Windows nevarēja nolasīt vai saglabāt VPN akreditācijas datus.");
 else if(f.stage==L"CONNECT")message=L(L"VPN settings saved. Connection failed.",L"Настройки VPN сохранены. Подключиться не удалось.",L"VPN iestatījumi saglabāti. Savienojums neizdevās.");
 else message=L(L"Setup could not be completed.",L"Не удалось завершить настройку.",L"Neizdevās pabeigt iestatīšanu.");
 if(f.stage!=L"LINK")message+=L"\r\n"+f.stage+L": "+std::to_wstring(f.code);
 return message;
}


static std::wstring Text(HWND h){std::vector<wchar_t> value(GetWindowTextLengthW(h)+1);GetWindowTextW(h,value.data(),int(value.size()));return value.data();}
#include "manager.h"
static void Visible(HWND h,bool show){ShowWindow(h,show?SW_SHOW:SW_HIDE);}
static void ResizeClient(int width,int height){RECT r={0,0,px(width),px(height)};DWORD style=DWORD(GetWindowLongPtrW(window,GWL_STYLE));AdjustWindowRectExForDpi(&r,style,FALSE,0,dpi);SetWindowPos(window,nullptr,0,0,r.right-r.left,r.bottom-r.top,SWP_NOMOVE|SWP_NOZORDER);}
static void Render(){
 bool loaded=bool(settings);
 for(HWND h:{networkLabel,networkEdit,networkHelp,rdpHelp,saveButton,connectButton})Visible(h,loaded);
 Visible(loadButton,!loaded);Visible(introText,!loaded&&hasFileToken);Visible(linkLabel,!loaded&&!hasFileToken);Visible(linkEdit,!loaded&&!hasFileToken);
 SetWindowTextW(stepLabel,loaded?L(L"SETTINGS",L"ПАРАМЕТРЫ",L"IESTATĪJUMI"):L(L"WINDOWS SETUP",L"НАСТРОЙКА WINDOWS",L"WINDOWS IESTATĪŠANA"));
 auto title=loaded?L"TOLF VPN · "+std::wstring(Manager::NodeLabel(settings->server)):std::wstring(L"TOLF VPN");SetWindowTextW(pageTitle,title.c_str());
 MoveWindow(status,px(36),px(loaded?458:218),px(488),px(54),TRUE);
 MoveWindow(footer,px(36),px(loaded?526:276),px(488),px(22),TRUE);
 ResizeClient(560,loaded?570:330);
 EnableWindow(loadButton,!busy);EnableWindow(linkEdit,!busy);EnableWindow(networkEdit,!busy);EnableWindow(saveButton,!busy);EnableWindow(connectButton,!busy);
}
struct Result {std::unique_ptr<Settings> loaded;std::wstring name,networks,error;bool connect=false;};
static void Start(bool load,bool connect=false){
 if(busy||(!load&&!settings))return;std::wstring token;std::vector<Network4> excluded;
 try{if(load){auto link=Text(linkEdit);auto a=link.find_first_not_of(L" \r\n\t"),b=link.find_last_not_of(L" \r\n\t");token=Token(a==std::wstring::npos?L"":link.substr(a,b-a+1));settings.reset();}else excluded=CheckedNetworks(Text(networkEdit));}
 catch(const Failure&f){SetWindowTextW(status,Error(f).c_str());return;}
 busy=true;Render();SetWindowTextW(status,load?L(L"Loading settings…",L"Загрузка настроек…",L"Iestatījumu ielāde…"):L(L"Saving settings…",L"Сохранение настроек…",L"Iestatījumu saglabāšana…"));
 try{std::thread([load,connect,token,excluded]{auto r=std::make_unique<Result>();r->connect=connect;try{Com com;Wmi w;Preflight(w);if(load){r->loaded=std::make_unique<Settings>();Fetch(token,*r->loaded);r->networks=NetworkText(CheckedNetworks(SavedNetworks(r->loaded->id)));}else{r->name=ProfileName(*settings);ConfigureRoutes(w,*settings,r->name,excluded);SaveProfileLabels(*settings);InstallController();r->networks=NetworkText(excluded);if(connect)DialProfile(r->name,window);}}catch(const Failure&f){r->loaded.reset();r->error=Error(f);}catch(...){r->loaded.reset();r->error=Error({L"SETUP",ERROR_GEN_FAILURE});}PostMessageW(window,Done,0,reinterpret_cast<LPARAM>(r.release()));}).detach();}
 catch(...){busy=false;Render();SetWindowTextW(status,Error({L"SETUP",ERROR_GEN_FAILURE}).c_str());}
}
static LRESULT CALLBACK Proc(HWND h,UINT m,WPARAM w,LPARAM l){switch(m){
 case WM_CREATE:{window=h;dpi=GetDpiForWindow(h);whiteBrush=CreateSolidBrush(RGB(250,250,250));
 font=CreateFontW(-px(16),0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"Segoe UI");smallFont=CreateFontW(-px(13),0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"Segoe UI");titleFont=CreateFontW(-px(25),0,0,0,FW_SEMIBOLD,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"Segoe UI");brandFont=CreateFontW(-px(12),0,0,0,FW_SEMIBOLD,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"Segoe UI");
 auto control=[h](const wchar_t*cls,const wchar_t*text,DWORD style,int x,int y,int width,int height,int id,HFONT use=nullptr){HWND c=CreateWindowExW(0,cls,text,WS_CHILD|WS_VISIBLE|style,px(x),px(y),px(width),px(height),h,(HMENU)(INT_PTR)id,GetModuleHandleW(nullptr),nullptr);SendMessageW(c,WM_SETFONT,(WPARAM)(use?use:font),TRUE);return c;};
 stepLabel=control(L"STATIC",L"",0,36,26,488,18,0,brandFont);pageTitle=control(L"STATIC",L"TOLF VPN",0,36,54,488,40,0,titleFont);
 introText=control(L"STATIC",L(L"Load this computer’s personal settings. The VPN will not connect during this step.",L"Загрузите персональные настройки этого компьютера. VPN на этом этапе не подключается.",L"Ielādējiet šī datora personīgos iestatījumus. Šajā solī VPN netiks savienots."),0,36,106,488,50,0);
 linkLabel=control(L"STATIC",L(L"Personal setup link",L"Персональная ссылка настройки",L"Personīgā iestatīšanas saite"),0,36,105,488,22,0,smallFont);
 linkEdit=control(L"EDIT",L"",WS_BORDER|WS_TABSTOP|ES_AUTOHSCROLL,36,132,488,34,101);SendMessageW(linkEdit,EM_SETLIMITTEXT,2047,0);
 loadButton=control(L"BUTTON",L(L"Load settings",L"Загрузить настройки",L"Ielādēt iestatījumus"),WS_TABSTOP|BS_DEFPUSHBUTTON,36,170,488,44,102);
 networkLabel=control(L"STATIC",L(L"Networks outside VPN",L"Сети вне VPN",L"Tīkli ārpus VPN"),0,36,108,488,25,0);
 networkEdit=control(L"EDIT",L"",WS_BORDER|WS_TABSTOP|WS_VSCROLL|ES_MULTILINE|ES_AUTOVSCROLL|ES_WANTRETURN,36,140,488,94,103);SendMessageW(networkEdit,EM_SETLIMITTEXT,4096,0);
 networkHelp=control(L"STATIC",L(L"Optional. One IPv4 network per line, for example 192.168.200.0/24. Leave empty to route all traffic through VPN.",L"Необязательно. По одной сети IPv4 в строке, например 192.168.200.0/24. Оставьте пустым, чтобы направлять весь трафик через VPN.",L"Neobligāti. Viens IPv4 tīkls rindā, piemēram, 192.168.200.0/24. Atstājiet tukšu, lai visu datplūsmu virzītu caur VPN."),0,36,246,488,58,0,smallFont);
 rdpHelp=control(L"STATIC",L(L"Remote Desktop: save without connecting first.",L"Удалённый рабочий стол: сначала сохраните без подключения.",L"Attālā darbvirsma: vispirms saglabājiet bez savienošanās."),0,36,320,488,28,0,smallFont);
 saveButton=control(L"BUTTON",L(L"Save without connecting",L"Сохранить без подключения",L"Saglabāt bez savienošanās"),WS_TABSTOP|BS_MULTILINE,36,366,236,48,104);
 connectButton=control(L"BUTTON",L(L"Save and connect",L"Сохранить и подключиться",L"Saglabāt un savienot"),WS_TABSTOP|BS_DEFPUSHBUTTON|BS_MULTILINE,288,366,236,48,105);
 status=control(L"STATIC",L"",0,36,218,488,54,0,smallFont);footer=control(L"STATIC",L(L"Built into Windows  •  TOLF VPN 2.6.1",L"Средствами Windows  •  TOLF VPN 2.6.1",L"Windows līdzekļi  •  TOLF VPN 2.6.1"),SS_CENTER,36,276,488,22,0,smallFont);
 wchar_t file[32768];DWORD n=GetModuleFileNameW(nullptr,file,32768);if(n&&n<32768){std::wstring path=file;auto token=FilenameToken(path.substr(path.find_last_of(L"\\/")+1));if(!token.empty()){hasFileToken=true;SetWindowTextW(linkEdit,(L"https://api.tolf.is/windows/p/"+token).c_str());}}
 if(!hasFileToken){SetWindowTextW(introText,L(L"The setup link could not be read from the filename. Paste it below.",L"Не удалось определить ссылку по имени файла. Вставьте её ниже.",L"Iestatīšanas saiti nevarēja nolasīt no faila nosaukuma. Ielīmējiet to zemāk."));}
 Render();SetFocus(hasFileToken?loadButton:linkEdit);return 0;}
 case WM_CTLCOLORSTATIC:{HDC dc=(HDC)w;SetBkMode(dc,TRANSPARENT);HWND c=(HWND)l;if(c==stepLabel){SetTextColor(dc,RGB(70,98,82));}else if(c==networkHelp||c==rdpHelp||c==footer||c==status){SetTextColor(dc,RGB(95,99,104));}else SetTextColor(dc,RGB(28,30,33));return (LRESULT)whiteBrush;}
 case WM_ERASEBKGND:{RECT r;GetClientRect(h,&r);FillRect((HDC)w,&r,whiteBrush);return 1;}
 case WM_COMMAND:if(HIWORD(w)==BN_CLICKED){if(LOWORD(w)==102)Start(true);if(LOWORD(w)==104)Start(false);if(LOWORD(w)==105)Start(false,true);}return 0;
 case Done:{std::unique_ptr<Result>r(reinterpret_cast<Result*>(l));if(!r->error.empty())SetWindowTextW(status,r->error.c_str());else if(r->loaded){settings=std::move(r->loaded);SetWindowTextW(networkEdit,r->networks.c_str());SetWindowTextW(status,L(L"Settings loaded. Review the exclusions and save.",L"Настройки загружены. Проверьте исключения и сохраните.",L"Iestatījumi ielādēti. Pārbaudiet izņēmumus un saglabājiet."));}else{SetWindowTextW(networkEdit,r->networks.c_str());SetWindowTextW(status,L(L"Settings saved. Windows will use them on every connection.",L"Настройки сохранены. Windows будет использовать их при каждом подключении.",L"Iestatījumi saglabāti. Windows tos izmantos katrā savienojumā."));try{LaunchController(r->connect?L"--tray":L"--manage");if(r->connect&&Connected(Phonebook(),r->name)){busy=false;DestroyWindow(h);return 0;}}catch(const Failure&f){SetWindowTextW(status,Error(f).c_str());}}busy=false;Render();return 0;}
 case WM_CLOSE:if(!busy)DestroyWindow(h);return 0;
 case WM_DESTROY:settings.reset();DeleteObject(font);DeleteObject(smallFont);DeleteObject(titleFont);DeleteObject(brandFont);DeleteObject(whiteBrush);PostQuitMessage(0);return 0;
 }return DefWindowProcW(h,m,w,l);}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE,PWSTR,int show){
 LANGID language=PRIMARYLANGID(GetUserDefaultUILanguage());lang=language==LANG_RUSSIAN?1:language==LANG_LATVIAN?2:0;
 int count=0;LPWSTR* args=CommandLineToArgvW(GetCommandLineW(),&count);
 std::wstring action=(args&&count==2)?args[1]:L"";if(args)LocalFree(args);
 if(action==L"--manage"||action==L"--widget"||action==L"--tray")return Manager::Run(instance,action!=L"--manage",action==L"--tray");
 HANDLE mutex=CreateMutexW(nullptr,FALSE,L"Local\\TOLF-Native-Setup");if(!mutex)return 1;if(GetLastError()==ERROR_ALREADY_EXISTS){MessageBoxW(nullptr,L"TOLF setup is already open.",L"TOLF VPN",MB_OK);CloseHandle(mutex);return 0;}
 LANGID id=PRIMARYLANGID(GetUserDefaultUILanguage());lang=id==LANG_RUSSIAN?1:id==LANG_LATVIAN?2:0;
 HRESULT init=CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED);if(FAILED(init)){CloseHandle(mutex);return 1;}
 HRESULT sec=CoInitializeSecurity(nullptr,-1,nullptr,nullptr,RPC_C_AUTHN_LEVEL_DEFAULT,RPC_C_IMP_LEVEL_IMPERSONATE,nullptr,EOAC_NONE,nullptr);if(FAILED(sec)&&sec!=RPC_E_TOO_LATE){CoUninitialize();CloseHandle(mutex);return 1;}
 WNDCLASSW cls={};cls.hInstance=instance;cls.lpfnWndProc=Proc;cls.lpszClassName=L"TolfNativeSetup";cls.hIcon=LoadIconW(instance,MAKEINTRESOURCEW(101));cls.hCursor=LoadCursorW(nullptr,IDC_ARROW);cls.hbrBackground=(HBRUSH)(COLOR_WINDOW+1);RegisterClassW(&cls);
 dpi=GetDpiForSystem();RECT rect={0,0,px(560),px(330)};DWORD style=WS_OVERLAPPED|WS_CAPTION|WS_SYSMENU|WS_MINIMIZEBOX;AdjustWindowRectExForDpi(&rect,style,FALSE,0,dpi);HWND h=CreateWindowExW(0,cls.lpszClassName,L"TOLF VPN",style,CW_USEDEFAULT,CW_USEDEFAULT,rect.right-rect.left,rect.bottom-rect.top,nullptr,nullptr,instance,nullptr);if(!h){CoUninitialize();CloseHandle(mutex);return 1;}ShowWindow(h,show);MSG msg;while(GetMessageW(&msg,nullptr,0,0)>0){if(!IsDialogMessageW(h,&msg)){TranslateMessage(&msg);DispatchMessageW(&msg);}}CoUninitialize();CloseHandle(mutex);return 0;
}

