#pragma once
#include "controller.h"
namespace Manager {
static HWND wnd,select,stateText,details,netLabel,netEdit,help,save,toggle,mode,autostart,pin,message,technical,divider,location;
static HFONT normal,heading;static HBRUSH background;
static std::vector<LocalProfile> profiles;
static bool compact=false,working=false,dirty=false,trayPresent=false,showDetails=false;
static UINT scale=96,taskbarCreated=0;static const UINT Finished=WM_APP+20,Tray=WM_APP+21,Activate=WM_APP+22;
static HICON icon;static int cached=-2;static bool lastConnected=false,lastActive=false;
struct Result {std::wstring error;bool saved=false;};
static int Px(int x){return MulDiv(x,scale,96);}
static int Selection(){auto i=SendMessageW(select,CB_GETCURSEL,0,0);return i>=0&&size_t(i)<profiles.size()?int(i):-1;}
static void ErrorText(const Failure& f) {
    auto text=Error(f);if(f.stage==L"CONNECT"||f.stage==L"DISCONNECT"){
        wchar_t system[1024]={};RasGetErrorStringW(f.code,system,1024);
        text=L(L"Connection error: ",L"Ошибка подключения: ",L"Savienojuma kļūda: ")+std::to_wstring(f.code)+L"\r\n"+system;
    }
    SetWindowTextW(message,text.c_str());
}
static void TrayIcon(bool add=false) {
    NOTIFYICONDATAW data={};data.cbSize=sizeof(data);data.hWnd=wnd;data.uID=1;
    data.uFlags=NIF_MESSAGE|NIF_ICON|NIF_TIP;data.uCallbackMessage=Tray;data.hIcon=icon;
    std::wstring tip=L"TOLF VPN — "+std::wstring(working?L(L"Working…",L"Выполняется…",L"Notiek…"):lastConnected?L(L"Connected",L"Подключено",L"Savienots"):L(L"Disconnected",L"Отключено",L"Atvienots"));
    wcsncpy_s(data.szTip,tip.c_str(),_TRUNCATE);
    trayPresent=Shell_NotifyIconW(add?NIM_ADD:NIM_MODIFY,&data)!=FALSE;
}
static void Layout() {
    for(HWND c:{netLabel,netEdit,help,autostart,technical,divider})ShowWindow(c,compact?SW_HIDE:SW_SHOW);
    ShowWindow(details,!compact&&showDetails?SW_SHOW:SW_HIDE);
    ShowWindow(save,!compact&&dirty?SW_SHOW:SW_HIDE);
    ShowWindow(pin,compact?SW_SHOW:SW_HIDE);
    ShowWindow(select,profiles.size()==1?SW_HIDE:SW_SHOW);
    ShowWindow(location,profiles.size()==1?SW_SHOW:SW_HIDE);
    int width=compact?340:480;
    int footer=dirty?382:334;
    int height=compact?244:footer+130+(showDetails?112:0);
    MoveWindow(select,Px(24),Px(24),Px(compact?292:272),Px(220),TRUE);
    MoveWindow(location,Px(24),Px(28),Px(compact?292:272),Px(26),TRUE);
    MoveWindow(stateText,Px(24),Px(76),Px(compact?292:276),Px(36),TRUE);
    MoveWindow(toggle,Px(compact?24:316),Px(compact?126:72),Px(compact?292:140),Px(42),TRUE);
    MoveWindow(mode,Px(compact?24:316),Px(compact?190:22),Px(compact?128:140),Px(32),TRUE);
    MoveWindow(pin,Px(170),Px(194),Px(146),Px(24),TRUE);
    MoveWindow(divider,Px(24),Px(140),Px(432),Px(1),TRUE);
    MoveWindow(netLabel,Px(24),Px(163),Px(432),Px(24),TRUE);
    MoveWindow(netEdit,Px(24),Px(196),Px(432),Px(76),TRUE);
    MoveWindow(help,Px(24),Px(282),Px(432),Px(42),TRUE);
    MoveWindow(save,Px(280),Px(330),Px(176),Px(34),TRUE);
    MoveWindow(autostart,Px(24),Px(footer),Px(432),Px(24),TRUE);
    MoveWindow(technical,Px(24),Px(footer+38),Px(228),Px(32),TRUE);
    MoveWindow(details,Px(24),Px(footer+82),Px(432),Px(100),TRUE);
    MoveWindow(message,Px(24),Px(compact?224:footer+78+(showDetails?112:0)),Px(width-48),Px(compact?18:48),TRUE);
    SetWindowTextW(mode,compact?L(L"Settings",L"Настройки",L"Iestatījumi"):L(L"Widget",L"Виджет",L"Logrīks"));
    SetWindowTextW(technical,showDetails?L(L"Hide connection details",L"Скрыть сведения",L"Paslēpt informāciju"):L(L"Connection details",L"Сведения о подключении",L"Savienojuma informācija"));
    RECT r={0,0,Px(width),Px(height)};AdjustWindowRectExForDpi(&r,DWORD(GetWindowLongPtrW(wnd,GWL_STYLE)),FALSE,0,scale);
    SetWindowPos(wnd,nullptr,0,0,r.right-r.left,r.bottom-r.top,SWP_NOMOVE|SWP_NOZORDER);
    RedrawWindow(wnd,nullptr,nullptr,RDW_INVALIDATE|RDW_ERASE|RDW_ALLCHILDREN|RDW_UPDATENOW);
}
static void Refresh(bool fields=false) {
    int i=Selection();bool active=false,connected=false;
    try{
        if(i>=0){RASCONNSTATUSW s={};active=ProfileConnection(profiles[i].name,&s)!=nullptr;connected=active&&s.rasconnstate==RASCS_Connected;}
        if(fields&&i>=0){SetWindowTextW(netEdit,SavedNetworks(profiles[i].id).c_str());dirty=false;}
        if(fields||cached!=i||connected!=lastConnected) {
            std::wstring info;
            if(i>=0){
                info=L(L"Server: ",L"Сервер: ",L"Serveris: ")+profiles[i].server+L"\r\n";
                info+=L(L"Protocol: IKEv2",L"Протокол: IKEv2",L"Protokols: IKEv2");
                auto dns=connected?ConnectionDns(profiles[i].name):L"";
                info+=L"\r\nDNS: "+(dns.empty()?std::wstring(L(L"Assigned by VPN server",L"Назначается VPN-сервером",L"Piešķir VPN serveris")):dns);
                info+=L"\r\n"+std::wstring(L(L"Account: current Windows user",L"Учётная запись: текущий пользователь Windows",L"Konts: pašreizējais Windows lietotājs"));
            }
            SetWindowTextW(details,info.c_str());cached=i;
        }
        lastConnected=connected;lastActive=active;
        SetWindowTextW(stateText,i<0?L(L"No TOLF connections",L"Нет подключений TOLF",L"Nav TOLF savienojumu"):working?L(L"Working…",L"Выполняется…",L"Notiek…"):connected?L(L"Connected",L"Подключено",L"Savienots"):active?L(L"Connecting…",L"Подключение…",L"Savienojas…"):L(L"Disconnected",L"Отключено",L"Atvienots"));
        SetWindowTextW(toggle,active?L(L"Disconnect",L"Отключить",L"Atvienot"):L(L"Connect",L"Подключить",L"Savienot"));
        EnableWindow(toggle,i>=0&&!working&&!dirty);EnableWindow(select,!working&&!dirty);
        EnableWindow(netEdit,i>=0&&!active&&!working);EnableWindow(save,i>=0&&!active&&!working&&dirty);
        SetWindowTextW(help,active?L(L"Disconnect to change networks outside VPN.",L"Для изменения сетей вне VPN отключите подключение.",L"Atvienojiet, lai mainītu tīklus ārpus VPN."):L(L"One IPv4 network per line. Empty means all traffic through VPN.",L"По одной сети IPv4 в строке. Пусто — весь трафик через VPN.",L"Viens IPv4 tīkls rindā. Tukšs — visa datplūsma caur VPN."));
        TrayIcon(!trayPresent);
    }catch(const Failure& f){EnableWindow(toggle,FALSE);EnableWindow(save,FALSE);ErrorText(f);}
}
static void Start(bool saving) {
    int i=Selection();if(i<0||working)return;
    auto profile=profiles[i];std::vector<Network4> exclusions;
    try{if(saving)exclusions=CheckedNetworks(Text(netEdit));}catch(const Failure& f){ErrorText(f);return;}
    bool disconnect=lastActive;working=true;SetWindowTextW(message,L"");Refresh();
    try{std::thread([profile,exclusions,saving,disconnect]{auto r=std::make_unique<Result>();
        try{Com com;if(saving){Wmi w;Settings c;c.id=profile.id;c.server=profile.server;ConfigureRoutes(w,c,profile.name,exclusions,-1,true);r->saved=true;}
            else if(disconnect)DisconnectProfile(profile.name);else DialProfile(profile.name,wnd);
        }catch(const Failure& f){wchar_t system[1024]={};RasGetErrorStringW(f.code,system,1024);r->error=Error(f);if(f.stage==L"CONNECT"||f.stage==L"DISCONNECT")r->error=std::to_wstring(f.code)+L": "+system;}
        catch(...){r->error=L(L"Operation failed.",L"Операция не выполнена.",L"Darbība neizdevās.");}
        if(!PostMessageW(wnd,Finished,0,reinterpret_cast<LPARAM>(r.get())))return;r.release();
    }).detach();}catch(...){working=false;Refresh();SetWindowTextW(message,L(L"Could not start operation.",L"Не удалось начать операцию.",L"Neizdevās sākt darbību."));}
}
static void ActivateWindow(bool widget) {compact=widget;Layout();ShowWindow(wnd,SW_RESTORE);SetForegroundWindow(wnd);Refresh();}
static void ReloadProfiles() {
    if(working||dirty)return;auto old=Selection();std::wstring name=old>=0?profiles[old].name:L"";
    profiles=LocalProfiles();SendMessageW(select,CB_RESETCONTENT,0,0);int chosen=0;
    for(size_t i=0;i<profiles.size();i++){auto label=profiles.size()==1?std::wstring(L(L"Riga",L"Рига",L"Rīga")):L"Riga · "+profiles[i].id.substr(0,8);SendMessageW(select,CB_ADDSTRING,0,reinterpret_cast<LPARAM>(label.c_str()));if(profiles[i].name==name)chosen=int(i);}
    SendMessageW(select,CB_SETCURSEL,chosen,0);cached=-2;Refresh(true);
}
static LRESULT CALLBACK Proc(HWND h,UINT msg,WPARAM w,LPARAM l) {
    if(taskbarCreated&&msg==taskbarCreated){trayPresent=false;TrayIcon(true);return 0;}
    switch(msg){
    case WM_CREATE:{wnd=h;scale=GetDpiForWindow(h);background=CreateSolidBrush(RGB(255,255,255));
        normal=CreateFontW(-Px(14),0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"Segoe UI");
        heading=CreateFontW(-Px(24),0,0,0,FW_SEMIBOLD,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"Segoe UI");
        auto control=[h](const wchar_t* cls,const wchar_t* text,DWORD style,int x,int y,int width,int height,int id){HWND c=CreateWindowExW(0,cls,text,WS_CHILD|WS_VISIBLE|style,Px(x),Px(y),Px(width),Px(height),h,(HMENU)(INT_PTR)id,GetModuleHandleW(nullptr),nullptr);SendMessageW(c,WM_SETFONT,(WPARAM)normal,TRUE);return c;};
        select=control(L"COMBOBOX",L"",CBS_DROPDOWNLIST|WS_VSCROLL|WS_TABSTOP,24,22,492,220,201);
        stateText=control(L"STATIC",L"",0,24,68,492,35,0);SendMessageW(stateText,WM_SETFONT,(WPARAM)heading,TRUE);
        details=control(L"STATIC",L"",0,24,119,492,100,0);
        netLabel=control(L"STATIC",L(L"Networks outside VPN",L"Сети вне VPN",L"Tīkli ārpus VPN"),0,24,230,492,24,0);
        netEdit=control(L"EDIT",L"",WS_BORDER|WS_VSCROLL|WS_TABSTOP|ES_MULTILINE|ES_AUTOVSCROLL|ES_WANTRETURN,24,263,492,94,202);SendMessageW(netEdit,EM_SETLIMITTEXT,4096,0);
        help=control(L"STATIC",L"",0,24,366,492,44,0);
        save=control(L"BUTTON",L(L"Save changes",L"Сохранить",L"Saglabāt iestatījumus"),WS_TABSTOP|BS_OWNERDRAW,24,419,492,38,203);
        toggle=control(L"BUTTON",L"",WS_TABSTOP|BS_OWNERDRAW,24,472,238,44,204);
        mode=control(L"BUTTON",L"",WS_TABSTOP|BS_OWNERDRAW,278,472,238,36,205);
        autostart=control(L"BUTTON",L(L"Start when I sign in to Windows",L"Запускать при входе в Windows",L"Rādīt ikonu, piesakoties Windows"),WS_TABSTOP|BS_AUTOCHECKBOX,24,530,492,24,206);
        pin=control(L"BUTTON",L(L"Always on top",L"Поверх окон",L"Virs citiem logiem"),WS_TABSTOP|BS_AUTOCHECKBOX,24,214,312,24,207);
        message=control(L"STATIC",L"",0,24,567,492,60,0);
        technical=control(L"BUTTON",L"",WS_TABSTOP|BS_OWNERDRAW,24,372,228,32,208);
        location=control(L"STATIC",L(L"Riga",L"Рига",L"Rīga"),0,24,28,272,26,210);
        divider=control(L"STATIC",L"",SS_ETCHEDHORZ,24,140,432,1,209);
        icon=LoadIconW(GetModuleHandleW(nullptr),MAKEINTRESOURCEW(101));SendMessageW(h,WM_SETICON,ICON_SMALL,(LPARAM)icon);SendMessageW(h,WM_SETICON,ICON_BIG,(LPARAM)icon);
        auto startup=KnownPath(FOLDERID_Startup)+L"\\TOLF VPN.lnk";SendMessageW(autostart,BM_SETCHECK,GetFileAttributesW(startup.c_str())!=INVALID_FILE_ATTRIBUTES?BST_CHECKED:BST_UNCHECKED,0);
        taskbarCreated=RegisterWindowMessageW(L"TaskbarCreated");ReloadProfiles();Layout();SetTimer(h,1,1000,nullptr);return 0;}
    case WM_TIMER:Refresh();return 0;
    case WM_COMMAND:
        if(LOWORD(w)==202&&HIWORD(w)==EN_CHANGE){bool wasDirty=dirty;dirty=true;Refresh();if(!wasDirty)Layout();return 0;}
        if(LOWORD(w)==201&&HIWORD(w)==CBN_SELCHANGE){Refresh(true);Layout();return 0;}
        if(HIWORD(w)==BN_CLICKED){switch(LOWORD(w)){
            case 208:showDetails=!showDetails;Layout();break;
            case 203:Start(true);break;
            case 204:Start(false);break;
            case 205:compact=!compact;Layout();break;
            case 206:{try{auto path=KnownPath(FOLDERID_Startup)+L"\\TOLF VPN.lnk";if(SendMessageW(autostart,BM_GETCHECK,0,0)==BST_CHECKED)Shortcut(path,ControllerPath(),L"--tray");else if(!DeleteFileW(path.c_str())&&GetLastError()!=ERROR_FILE_NOT_FOUND)throw Failure{L"SHORTCUT",GetLastError()};}catch(const Failure& f){ErrorText(f);SendMessageW(autostart,BM_SETCHECK,BST_UNCHECKED,0);}break;}
            case 207:SetWindowPos(h,SendMessageW(pin,BM_GETCHECK,0,0)==BST_CHECKED?HWND_TOPMOST:HWND_NOTOPMOST,0,0,0,0,SWP_NOMOVE|SWP_NOSIZE);break;
        }}return 0;
    case Finished:{std::unique_ptr<Result> r(reinterpret_cast<Result*>(l));working=false;if(r->saved)dirty=false;Refresh(r->saved);Layout();
        if(!r->error.empty()){if(compact){compact=false;Layout();}ShowWindow(h,SW_SHOW);SetWindowTextW(message,r->error.c_str());}
        else if(r->saved)SetWindowTextW(message,L(L"Settings saved.",L"Настройки сохранены.",L"Iestatījumi saglabāti."));return 0;}
    case Activate:try{ReloadProfiles();ActivateWindow(w!=0);}catch(const Failure& f){ErrorText(f);}return 0;
    case Tray:
        if(l==WM_LBUTTONUP){ActivateWindow(true);return 0;}
        if(l==WM_RBUTTONUP){HMENU menu=CreatePopupMenu();AppendMenuW(menu,MF_STRING,301,L(L"Show widget",L"Показать виджет",L"Rādīt logrīku"));AppendMenuW(menu,MF_STRING,302,L(L"Settings",L"Настройки",L"Iestatījumi"));AppendMenuW(menu,MF_STRING|((working||dirty||Selection()<0)?MF_GRAYED:0),303,lastActive?L(L"Disconnect",L"Отключить",L"Atvienot"):L(L"Connect",L"Подключить",L"Savienot"));AppendMenuW(menu,MF_SEPARATOR,0,nullptr);AppendMenuW(menu,MF_STRING|(working?MF_GRAYED:0),304,L(L"Exit widget (keep VPN)",L"Закрыть виджет (VPN остаётся)",L"Aizvērt logrīku (VPN paliek)"));POINT p;GetCursorPos(&p);SetForegroundWindow(h);int id=TrackPopupMenu(menu,TPM_RETURNCMD|TPM_RIGHTBUTTON,p.x,p.y,0,h,nullptr);DestroyMenu(menu);PostMessageW(h,WM_NULL,0,0);if(id==301)ActivateWindow(true);if(id==302)ActivateWindow(false);if(id==303)Start(false);if(id==304&&!working){if(dirty&&MessageBoxW(h,L(L"Discard unsaved changes?",L"Отменить несохранённые изменения?",L"Atmest nesaglabātās izmaiņas?"),L"TOLF VPN",MB_YESNO|MB_ICONQUESTION)!=IDYES)return 0;DestroyWindow(h);}return 0;}break;
    case WM_CLOSE:if(trayPresent)ShowWindow(h,SW_HIDE);else if(!working)DestroyWindow(h);return 0;
    case WM_DRAWITEM:{
        auto d=reinterpret_cast<DRAWITEMSTRUCT*>(l);
        if(d->CtlType!=ODT_BUTTON)return FALSE;
        bool disabled=(d->itemState&ODS_DISABLED)!=0,pressed=(d->itemState&ODS_SELECTED)!=0;
        bool primary=d->hwndItem==toggle||d->hwndItem==save;
        COLORREF fill=disabled?RGB(246,247,248):primary?(pressed?RGB(58,64,70):RGB(35,40,45)):(pressed?RGB(242,244,246):RGB(255,255,255));
        COLORREF border=primary?fill:RGB(216,220,224);
        HBRUSH brush=CreateSolidBrush(fill);HPEN pen=CreatePen(PS_SOLID,1,border);
        auto oldBrush=SelectObject(d->hDC,brush);auto oldPen=SelectObject(d->hDC,pen);auto oldFont=SelectObject(d->hDC,normal);
        FillRect(d->hDC,&d->rcItem,background);
        RoundRect(d->hDC,d->rcItem.left,d->rcItem.top,d->rcItem.right,d->rcItem.bottom,Px(10),Px(10));
        SetBkMode(d->hDC,TRANSPARENT);SetTextColor(d->hDC,disabled?RGB(145,150,155):primary?RGB(255,255,255):RGB(48,54,60));
        auto text=Text(d->hwndItem);RECT r=d->rcItem;InflateRect(&r,-Px(8),0);
        DrawTextW(d->hDC,text.c_str(),-1,&r,DT_CENTER|DT_VCENTER|DT_SINGLELINE);
        if(d->itemState&ODS_FOCUS){r=d->rcItem;InflateRect(&r,-Px(4),-Px(4));DrawFocusRect(d->hDC,&r);}
        SelectObject(d->hDC,oldFont);SelectObject(d->hDC,oldPen);SelectObject(d->hDC,oldBrush);DeleteObject(pen);DeleteObject(brush);return TRUE;
    }
    case WM_CTLCOLORBTN:
    case WM_CTLCOLORSTATIC:{SetBkMode((HDC)w,TRANSPARENT);SetTextColor((HDC)w,(HWND)l==stateText?RGB(30,34,38):RGB(92,98,105));return (LRESULT)background;}
    case WM_ERASEBKGND:{RECT r;GetClientRect(h,&r);FillRect((HDC)w,&r,background);return 1;}
    case WM_DESTROY:{KillTimer(h,1);NOTIFYICONDATAW data={};data.cbSize=sizeof(data);data.hWnd=h;data.uID=1;Shell_NotifyIconW(NIM_DELETE,&data);DeleteObject(normal);DeleteObject(heading);DeleteObject(background);PostQuitMessage(0);return 0;}
    }return DefWindowProcW(h,msg,w,l);
}
inline int Run(HINSTANCE instance,bool widget,bool hidden) {
    HANDLE mutex=CreateMutexW(nullptr,FALSE,L"Local\\TOLF-VPN-Control-2.4.1");if(!mutex)return 1;
    if(GetLastError()==ERROR_ALREADY_EXISTS){HWND old=FindWindowW(L"TolfVpnController",nullptr);if(old){if(!hidden){AllowSetForegroundWindow(ASFW_ANY);PostMessageW(old,Activate,widget?1:0,0);}else PostMessageW(old,WM_TIMER,1,0);}CloseHandle(mutex);return 0;}
    compact=widget;HRESULT init=CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED);if(FAILED(init)){CloseHandle(mutex);return 1;}
    WSADATA ws={};int wsa=WSAStartup(MAKEWORD(2,2),&ws);if(wsa){CoUninitialize();CloseHandle(mutex);return 1;}
    HRESULT sec=CoInitializeSecurity(nullptr,-1,nullptr,nullptr,RPC_C_AUTHN_LEVEL_DEFAULT,RPC_C_IMP_LEVEL_IMPERSONATE,nullptr,EOAC_NONE,nullptr);
    if(FAILED(sec)&&sec!=RPC_E_TOO_LATE){WSACleanup();CoUninitialize();CloseHandle(mutex);return 1;}
    WNDCLASSW cls={};cls.hInstance=instance;cls.lpfnWndProc=Proc;cls.lpszClassName=L"TolfVpnController";cls.hCursor=LoadCursorW(nullptr,IDC_ARROW);RegisterClassW(&cls);
    HWND h=nullptr;try{h=CreateWindowExW(0,cls.lpszClassName,L"TOLF VPN 2.4.1",WS_OVERLAPPED|WS_CAPTION|WS_SYSMENU|WS_MINIMIZEBOX,CW_USEDEFAULT,CW_USEDEFAULT,540,640,nullptr,nullptr,instance,nullptr);}catch(const Failure& f){MessageBoxW(nullptr,Error(f).c_str(),L"TOLF VPN",MB_OK|MB_ICONERROR);}catch(...){MessageBoxW(nullptr,L(L"Could not open TOLF settings.",L"Не удалось открыть настройки TOLF.",L"Neizdevās atvērt TOLF iestatījumus."),L"TOLF VPN",MB_OK|MB_ICONERROR);}
    if(h){if(!hidden||!trayPresent)ShowWindow(h,SW_SHOW);MSG msg;while(GetMessageW(&msg,nullptr,0,0)>0){if(!IsDialogMessageW(h,&msg)){TranslateMessage(&msg);DispatchMessageW(&msg);}}}
    WSACleanup();CoUninitialize();CloseHandle(mutex);return h?0:1;
}
}
