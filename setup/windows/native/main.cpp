#include "core.h"
#include <thread>
#include <memory>
static HWND window,edit,button,status;
static bool busy=false;
static HFONT font,titleFont;
static int lang=0;
static UINT dpi=96;
static const UINT Done=WM_APP+1;
static const wchar_t* L(const wchar_t*en,const wchar_t*ru,const wchar_t*lv){return lang==1?ru:lang==2?lv:en;}
static int px(int n){return MulDiv(n,dpi,96);}
static std::wstring Error(const Failure&f){
 std::wstring message;
 if(f.stage==L"LINK")message=L(L"Paste the personal setup link from TOLF.",L"Вставьте персональную ссылку настройки с сайта TOLF.",L"Ielīmējiet personīgo iestatīšanas saiti no TOLF.");
 else if(f.stage==L"NETWORK")message=L(L"Could not retrieve settings. Check the Internet connection or create a new setup link.",L"Не удалось получить настройки. Проверьте интернет или создайте новую ссылку настройки.",L"Neizdevās saņemt iestatījumus. Pārbaudiet internetu vai izveidojiet jaunu iestatīšanas saiti.");
 else if(f.stage==L"VPN_SERVICE"||f.stage==L"WINDOWS_COMPONENTS")message=L(L"A required Windows VPN component is unavailable or disabled. Ask your administrator to restore it.",L"Нужный системный компонент Windows недоступен или отключён. Обратитесь к администратору для его восстановления.",L"Nepieciešamais Windows komponents nav pieejams vai ir atspējots. Sazinieties ar administratoru.");
 else if(f.stage==L"NAME_CONFLICT")message=L(L"A different VPN connection already has this name. It was not changed.",L"Под этим именем уже существует другое VPN-подключение. Оно не изменено.",L"Ar šo nosaukumu jau ir cits VPN savienojums. Tas nav mainīts.");
 else if(f.stage==L"ROLLBACK")message=L(L"Setup failed and the new connection could not be removed. Check TOLF in Windows VPN settings.",L"Настройка не завершена, удалить новое подключение не удалось. Проверьте TOLF в настройках VPN Windows.",L"Iestatīšana neizdevās, un jauno savienojumu nevarēja noņemt. Pārbaudiet TOLF Windows VPN iestatījumos.");
 else message=L(L"Setup could not be completed.",L"Не удалось завершить настройку.",L"Neizdevās pabeigt iestatīšanu.");
 if(f.stage!=L"LINK")message+=L"\r\n"+f.stage+L": "+std::to_wstring(f.code);
 return message;
}
struct Result {std::wstring name,error;};
static void Ready(){busy=false;EnableWindow(edit,TRUE);EnableWindow(button,TRUE);}
static void Start(){if(busy)return;wchar_t value[2048];GetWindowTextW(edit,value,2048);std::wstring token;try{std::wstring link=value;auto a=link.find_first_not_of(L" \r\n\t"),b=link.find_last_not_of(L" \r\n\t");token=Token(a==std::wstring::npos?L"":link.substr(a,b-a+1));}catch(const Failure&f){SetWindowTextW(status,Error(f).c_str());return;}busy=true;EnableWindow(edit,FALSE);EnableWindow(button,FALSE);SetWindowTextW(status,L(L"Checking Windows and setting up VPN…",L"Проверяем Windows и настраиваем VPN…",L"Pārbauda Windows un iestata VPN…"));
 try{std::thread([token]{auto result=std::make_unique<Result>();try{Com com;Wmi w;Preflight(w);Settings c;Fetch(token,c);result->name=L"TOLF - Riga - "+c.id;Configure(w,c,result->name);}catch(const Failure&f){result->error=Error(f);}catch(...){result->error=Error({L"SETUP",ERROR_GEN_FAILURE});}PostMessageW(window,Done,0,reinterpret_cast<LPARAM>(result.release()));}).detach();}catch(...){SetWindowTextW(status,L(L"Could not start setup.",L"Не удалось запустить настройку.",L"Neizdevās sākt iestatīšanu."));Ready();}}
static LRESULT CALLBACK Proc(HWND h,UINT m,WPARAM w,LPARAM l){switch(m){
 case WM_CREATE:{window=h;dpi=GetDpiForWindow(h);font=CreateFontW(-px(15),0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"Segoe UI");titleFont=CreateFontW(-px(24),0,0,0,FW_SEMIBOLD,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"Segoe UI");auto control=[h](const wchar_t*cls,const wchar_t*text,DWORD style,int x,int y,int width,int height,int id){HWND c=CreateWindowExW(0,cls,text,WS_CHILD|WS_VISIBLE|style,px(x),px(y),px(width),px(height),h,(HMENU)(INT_PTR)id,GetModuleHandleW(nullptr),nullptr);SendMessageW(c,WM_SETFONT,(WPARAM)font,TRUE);return c;};HWND title=control(L"STATIC",L(L"Set up TOLF VPN",L"Настройка TOLF VPN",L"TOLF VPN iestatīšana"),0,24,22,500,40,0);SendMessageW(title,WM_SETFONT,(WPARAM)titleFont,TRUE);
 control(L"STATIC",L(L"Your personal setup link",L"Персональная ссылка настройки",L"Personīgā iestatīšanas saite"),0,24,78,500,25,0);
 edit=control(L"EDIT",L"",WS_BORDER|WS_TABSTOP|ES_AUTOHSCROLL,24,106,500,30,101);SendMessageW(edit,EM_SETLIMITTEXT,2047,0);
 wchar_t file[32768];DWORD n=GetModuleFileNameW(nullptr,file,32768);if(n&&n<32768){std::wstring path=file;auto token=FilenameToken(path.substr(path.find_last_of(L"\\/")+1));if(!token.empty())SetWindowTextW(edit,(L"https://api.tolf.is/windows/p/"+token).c_str());}
 button=control(L"BUTTON",L(L"Set up and connect",L"Настроить и подключиться",L"Iestatīt un savienot"),WS_TABSTOP|BS_DEFPUSHBUTTON,24,154,500,46,102);
 status=control(L"STATIC",L(L"Uses built-in Windows components. No additional software to install.",L"Используются штатные компоненты Windows. Устанавливать дополнительное ПО не требуется.",L"Izmanto iebūvētos Windows komponentus. Papildu programmatūra nav jāinstalē."),SS_LEFT,24,220,500,125,0);SetFocus(edit);return 0;}
 case WM_COMMAND:if(LOWORD(w)==102&&HIWORD(w)==BN_CLICKED)Start();return 0;
 case Done:{std::unique_ptr<Result>r(reinterpret_cast<Result*>(l));if(!r->error.empty()){SetWindowTextW(status,r->error.c_str());Ready();return 0;}SetWindowTextW(status,L(L"Connecting…",L"Подключаемся…",L"Savienojas…"));try{auto pb=Phonebook();RASDIALDLG d={};d.dwSize=sizeof(d);d.hwndOwner=h;BOOL ok=Connected(pb,r->name)||RasDialDlgW(pb.data(),r->name.data(),nullptr,&d);if(ok)SetWindowTextW(status,L(L"Connected. TOLF is available in Windows Settings → Network & Internet → VPN.",L"Подключено. TOLF доступен в Параметрах Windows → Сеть и Интернет → VPN.",L"Savienots. TOLF pieejams Windows iestatījumos → Tīkls un internets → VPN."));else{std::wstring s=L(L"VPN is configured. Connection cancelled or unsuccessful. Windows code: ",L"VPN настроен. Подключение отменено или не удалось. Код Windows: ",L"VPN iestatīts. Savienojums atcelts vai neizdevās. Windows kods: ");s+=std::to_wstring(d.dwError);SetWindowTextW(status,s.c_str());}}catch(const Failure&f){SetWindowTextW(status,Error(f).c_str());}Ready();return 0;}
 case WM_CLOSE:if(!busy)DestroyWindow(h);return 0;
 case WM_DESTROY:DeleteObject(font);DeleteObject(titleFont);PostQuitMessage(0);return 0;
 }return DefWindowProcW(h,m,w,l);}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE,PWSTR,int show){
 HANDLE mutex=CreateMutexW(nullptr,FALSE,L"Local\\TOLF-Native-Setup");if(!mutex)return 1;if(GetLastError()==ERROR_ALREADY_EXISTS){MessageBoxW(nullptr,L"TOLF setup is already open.",L"TOLF VPN",MB_OK);CloseHandle(mutex);return 0;}
 LANGID id=PRIMARYLANGID(GetUserDefaultUILanguage());lang=id==LANG_RUSSIAN?1:id==LANG_LATVIAN?2:0;
 HRESULT init=CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED);if(FAILED(init)){CloseHandle(mutex);return 1;}
 HRESULT sec=CoInitializeSecurity(nullptr,-1,nullptr,nullptr,RPC_C_AUTHN_LEVEL_DEFAULT,RPC_C_IMP_LEVEL_IMPERSONATE,nullptr,EOAC_NONE,nullptr);if(FAILED(sec)&&sec!=RPC_E_TOO_LATE){CoUninitialize();CloseHandle(mutex);return 1;}
 WNDCLASSW cls={};cls.hInstance=instance;cls.lpfnWndProc=Proc;cls.lpszClassName=L"TolfNativeSetup";cls.hCursor=LoadCursorW(nullptr,IDC_ARROW);cls.hbrBackground=(HBRUSH)(COLOR_WINDOW+1);RegisterClassW(&cls);
 dpi=GetDpiForSystem();RECT rect={0,0,px(548),px(370)};DWORD style=WS_OVERLAPPED|WS_CAPTION|WS_SYSMENU|WS_MINIMIZEBOX;AdjustWindowRectExForDpi(&rect,style,FALSE,0,dpi);HWND h=CreateWindowExW(0,cls.lpszClassName,L"TOLF VPN",style,CW_USEDEFAULT,CW_USEDEFAULT,rect.right-rect.left,rect.bottom-rect.top,nullptr,nullptr,instance,nullptr);if(!h){CoUninitialize();CloseHandle(mutex);return 1;}ShowWindow(h,show);MSG msg;while(GetMessageW(&msg,nullptr,0,0)>0){if(msg.message==WM_KEYDOWN&&msg.wParam==VK_RETURN){Start();continue;}if(!IsDialogMessageW(h,&msg)){TranslateMessage(&msg);DispatchMessageW(&msg);}}CoUninitialize();CloseHandle(mutex);return 0;
}
