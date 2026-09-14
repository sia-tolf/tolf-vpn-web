#include "routes.h"
#include <thread>
#include <memory>
static HWND window,linkEdit,networkEdit,loadButton,saveButton,connectButton,status;
static bool busy=false;
static HFONT font,titleFont;
static int lang=0;
static UINT dpi=96;
static const UINT Done=WM_APP+1;
static std::unique_ptr<Settings> settings;
static const wchar_t* L(const wchar_t*en,const wchar_t*ru,const wchar_t*lv){return lang==1?ru:lang==2?lv:en;}
static int px(int n){return MulDiv(n,dpi,96);}
static std::wstring Error(const Failure&f){
 std::wstring message;
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
 else message=L(L"Setup could not be completed.",L"Не удалось завершить настройку.",L"Neizdevās pabeigt iestatīšanu.");
 if(f.stage!=L"LINK")message+=L"\r\n"+f.stage+L": "+std::to_wstring(f.code);
 return message;
}

static std::wstring Text(HWND h){std::vector<wchar_t> value(GetWindowTextLengthW(h)+1);GetWindowTextW(h,value.data(),int(value.size()));return value.data();}
static void Controls(){EnableWindow(linkEdit,!busy);EnableWindow(loadButton,!busy);for(HWND h:{networkEdit,saveButton,connectButton})EnableWindow(h,!busy&&bool(settings));}
struct Result {std::unique_ptr<Settings> loaded;std::wstring name,networks,error;bool connect=false;};
static void Start(bool load,bool connect=false){
 if(busy||(!load&&!settings))return;
 std::wstring token;std::vector<Network4> excluded;
 try{if(load){auto link=Text(linkEdit);auto a=link.find_first_not_of(L" \r\n\t"),b=link.find_last_not_of(L" \r\n\t");token=Token(a==std::wstring::npos?L"":link.substr(a,b-a+1));settings.reset();}else excluded=CheckedNetworks(Text(networkEdit));}
 catch(const Failure&f){SetWindowTextW(status,Error(f).c_str());return;}
 busy=true;Controls();SetWindowTextW(status,L(L"Checking settings…",L"Проверяем настройки…",L"Pārbauda iestatījumus…"));
 try{std::thread([load,connect,token,excluded]{auto r=std::make_unique<Result>();r->connect=connect;
  try{Com com;Wmi w;Preflight(w);if(load){r->loaded=std::make_unique<Settings>();Fetch(token,*r->loaded);r->networks=NetworkText(CheckedNetworks(SavedNetworks(r->loaded->id)));}
   else{r->name=L"TOLF - Riga - "+settings->id;ConfigureRoutes(w,*settings,r->name,excluded);r->networks=NetworkText(excluded);}}
  catch(const Failure&f){r->loaded.reset();r->error=Error(f);}catch(...){r->loaded.reset();r->error=Error({L"SETUP",ERROR_GEN_FAILURE});}
  PostMessageW(window,Done,0,reinterpret_cast<LPARAM>(r.release()));
 }).detach();}catch(...){busy=false;Controls();SetWindowTextW(status,Error({L"SETUP",ERROR_GEN_FAILURE}).c_str());}
}
static LRESULT CALLBACK Proc(HWND h,UINT m,WPARAM w,LPARAM l){switch(m){
 case WM_CREATE:{window=h;dpi=GetDpiForWindow(h);
 font=CreateFontW(-px(15),0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"Segoe UI");
 titleFont=CreateFontW(-px(24),0,0,0,FW_SEMIBOLD,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"Segoe UI");
 auto control=[h](const wchar_t*cls,const wchar_t*text,DWORD style,int x,int y,int width,int height,int id){HWND c=CreateWindowExW(0,cls,text,WS_CHILD|WS_VISIBLE|style,px(x),px(y),px(width),px(height),h,(HMENU)(INT_PTR)id,GetModuleHandleW(nullptr),nullptr);SendMessageW(c,WM_SETFONT,(WPARAM)font,TRUE);return c;};
 auto title=control(L"STATIC",L(L"Set up TOLF VPN · 2.1",L"Настройка TOLF VPN · 2.1",L"TOLF VPN iestatīšana · 2.1"),0,24,18,560,36,0);SendMessageW(title,WM_SETFONT,(WPARAM)titleFont,TRUE);
 control(L"STATIC",L(L"Your personal setup link",L"Персональная ссылка настройки",L"Personīgā iestatīšanas saite"),0,24,64,560,25,0);
 linkEdit=control(L"EDIT",L"",WS_BORDER|WS_TABSTOP|ES_AUTOHSCROLL,24,89,560,30,101);SendMessageW(linkEdit,EM_SETLIMITTEXT,2047,0);
 loadButton=control(L"BUTTON",L(L"Load settings",L"Загрузить настройки",L"Ielādēt iestatījumus"),WS_TABSTOP|BS_DEFPUSHBUTTON,24,129,560,40,102);
 control(L"STATIC",L(L"Networks outside VPN (IPv4, optional)",L"Сети вне VPN (IPv4, необязательно)",L"Tīkli ārpus VPN (IPv4, neobligāti)"),0,24,185,560,25,0);
 networkEdit=control(L"EDIT",L"",WS_BORDER|WS_TABSTOP|WS_VSCROLL|ES_MULTILINE|ES_AUTOVSCROLL|ES_WANTRETURN,24,213,560,82,103);SendMessageW(networkEdit,EM_SETLIMITTEXT,4096,0);
 control(L"STATIC",L(L"One network per line, e.g. 192.168.200.0/24. Leave empty for no exclusions. These destinations use ordinary Windows routing outside this VPN.",L"По одной сети в строке, например 192.168.200.0/24. Пустой список — без исключений. Для этих адресов используется обычная маршрутизация Windows вне этого VPN.",L"Viens tīkls rindā, piemēram, 192.168.200.0/24. Tukšs saraksts — bez izņēmumiem. Šiem adresātiem izmanto parasto Windows maršrutēšanu ārpus šī VPN."),0,24,303,560,62,0);
 control(L"STATIC",L(L"Using Remote Desktop? Save without connecting first. Exclusions alone do not guarantee that your remote session will stay connected.",L"Работаете через RDP? Сначала сохраните без подключения. Сам по себе список исключений не гарантирует сохранение удалённого доступа.",L"Izmantojat attālo darbvirsmu? Vispirms saglabājiet bez savienošanās. Izņēmumi vien negarantē attālās sesijas saglabāšanu."),0,24,373,560,62,0);
 saveButton=control(L"BUTTON",L(L"Save without connecting",L"Сохранить без подключения",L"Saglabāt bez savienošanās"),WS_TABSTOP|BS_MULTILINE,24,447,274,50,104);
 connectButton=control(L"BUTTON",L(L"Save and connect",L"Сохранить и подключиться",L"Saglabāt un savienot"),WS_TABSTOP|BS_MULTILINE,310,447,274,50,105);
 status=control(L"STATIC",L(L"Load settings to review this device's saved exclusions. Uses built-in Windows components.",L"Загрузите настройки, чтобы увидеть сохранённые исключения этого устройства. Используются штатные компоненты Windows.",L"Ielādējiet iestatījumus, lai apskatītu ierīces saglabātos izņēmumus. Izmanto iebūvētos Windows komponentus."),SS_LEFT,24,514,560,95,0);
 wchar_t file[32768];DWORD n=GetModuleFileNameW(nullptr,file,32768);if(n&&n<32768){std::wstring path=file;auto token=FilenameToken(path.substr(path.find_last_of(L"\\/")+1));if(!token.empty())SetWindowTextW(linkEdit,(L"https://api.tolf.is/windows/p/"+token).c_str());}
 Controls();SetFocus(linkEdit);return 0;}
 case WM_COMMAND:
  if(LOWORD(w)==101&&HIWORD(w)==EN_CHANGE&&!busy){settings.reset();if(networkEdit)SetWindowTextW(networkEdit,L"");Controls();}
  if(HIWORD(w)==BN_CLICKED){if(LOWORD(w)==102)Start(true);if(LOWORD(w)==104)Start(false);if(LOWORD(w)==105)Start(false,true);}return 0;
 case Done:{std::unique_ptr<Result>r(reinterpret_cast<Result*>(l));
  if(!r->error.empty())SetWindowTextW(status,r->error.c_str());
  else if(r->loaded){settings=std::move(r->loaded);SetWindowTextW(networkEdit,r->networks.c_str());SetWindowTextW(status,L(L"Settings loaded. Review the network list, then choose how to save. VPN is not connected by this action.",L"Настройки загружены. Проверьте список сетей и выберите способ сохранения. Загрузка настроек не подключает VPN.",L"Iestatījumi ielādēti. Pārbaudiet tīklu sarakstu un izvēlieties saglabāšanu. Ielāde nepievieno VPN."));}
  else{SetWindowTextW(networkEdit,r->networks.c_str());SetWindowTextW(status,L(L"Saved without connecting. Windows will apply these settings whenever this VPN connects.",L"Сохранено без подключения. Windows применит настройки при каждом подключении этого VPN.",L"Saglabāts bez savienošanās. Windows izmantos iestatījumus katrā šī VPN savienojumā."));
   if(r->connect)try{auto pb=Phonebook();RASDIALDLG d={};d.dwSize=sizeof(d);d.hwndOwner=h;BOOL ok=RasDialDlgW(pb.data(),r->name.data(),nullptr,&d);std::wstring message;
    if(ok)message=L(L"Connected. TOLF is available in Windows VPN settings.",L"Подключено. TOLF доступен в настройках VPN Windows.",L"Savienots. TOLF pieejams Windows VPN iestatījumos.");
    else message=std::wstring(L(L"Saved. Connection cancelled or unsuccessful. Windows code: ",L"Сохранено. Подключение отменено или не удалось. Код Windows: ",L"Saglabāts. Savienojums atcelts vai neizdevās. Windows kods: "))+std::to_wstring(d.dwError);
    SetWindowTextW(status,message.c_str());}catch(const Failure&f){SetWindowTextW(status,Error(f).c_str());}}
  busy=false;Controls();return 0;}
 case WM_CLOSE:if(!busy)DestroyWindow(h);return 0;
 case WM_DESTROY:settings.reset();DeleteObject(font);DeleteObject(titleFont);PostQuitMessage(0);return 0;
 }return DefWindowProcW(h,m,w,l);}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE,PWSTR,int show){
 HANDLE mutex=CreateMutexW(nullptr,FALSE,L"Local\\TOLF-Native-Setup");if(!mutex)return 1;if(GetLastError()==ERROR_ALREADY_EXISTS){MessageBoxW(nullptr,L"TOLF setup is already open.",L"TOLF VPN",MB_OK);CloseHandle(mutex);return 0;}
 LANGID id=PRIMARYLANGID(GetUserDefaultUILanguage());lang=id==LANG_RUSSIAN?1:id==LANG_LATVIAN?2:0;
 HRESULT init=CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED);if(FAILED(init)){CloseHandle(mutex);return 1;}
 HRESULT sec=CoInitializeSecurity(nullptr,-1,nullptr,nullptr,RPC_C_AUTHN_LEVEL_DEFAULT,RPC_C_IMP_LEVEL_IMPERSONATE,nullptr,EOAC_NONE,nullptr);if(FAILED(sec)&&sec!=RPC_E_TOO_LATE){CoUninitialize();CloseHandle(mutex);return 1;}
 WNDCLASSW cls={};cls.hInstance=instance;cls.lpfnWndProc=Proc;cls.lpszClassName=L"TolfNativeSetup";cls.hCursor=LoadCursorW(nullptr,IDC_ARROW);cls.hbrBackground=(HBRUSH)(COLOR_WINDOW+1);RegisterClassW(&cls);
 dpi=GetDpiForSystem();RECT rect={0,0,px(608),px(625)};DWORD style=WS_OVERLAPPED|WS_CAPTION|WS_SYSMENU|WS_MINIMIZEBOX;AdjustWindowRectExForDpi(&rect,style,FALSE,0,dpi);HWND h=CreateWindowExW(0,cls.lpszClassName,L"TOLF VPN",style,CW_USEDEFAULT,CW_USEDEFAULT,rect.right-rect.left,rect.bottom-rect.top,nullptr,nullptr,instance,nullptr);if(!h){CoUninitialize();CloseHandle(mutex);return 1;}ShowWindow(h,show);MSG msg;while(GetMessageW(&msg,nullptr,0,0)>0){if(!IsDialogMessageW(h,&msg)){TranslateMessage(&msg);DispatchMessageW(&msg);}}CoUninitialize();CloseHandle(mutex);return 0;
}

