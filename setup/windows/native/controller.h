#pragma once
#include "routes.h"
#include <ws2tcpip.h>
#include <iphlpapi.h>
#include <shobjidl.h>
#include <shellapi.h>
#include <algorithm>

inline std::wstring KnownPath(REFKNOWNFOLDERID id) {
    PWSTR value=nullptr; Hr(SHGetKnownFolderPath(id,KF_FLAG_CREATE,nullptr,&value),L"SHORTCUT");
    std::wstring result=value; CoTaskMemFree(value); return result;
}
inline std::wstring ControllerPath() { return KnownPath(FOLDERID_LocalAppData)+L"\\TOLF\\VPN\\2.6.1\\TOLF-VPN.exe"; }
inline void Shortcut(const std::wstring& path,const std::wstring& exe,const wchar_t* args) {
    ComPtr<IShellLinkW> link; Hr(CoCreateInstance(CLSID_ShellLink,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&link)),L"SHORTCUT");
    Hr(link->SetPath(exe.c_str()),L"SHORTCUT"); Hr(link->SetArguments(args),L"SHORTCUT");
    Hr(link->SetDescription(L"TOLF VPN"),L"SHORTCUT"); Hr(link->SetIconLocation(exe.c_str(),0),L"SHORTCUT");
    ComPtr<IPersistFile> file; Hr(link.As(&file),L"SHORTCUT"); Hr(file->Save(path.c_str(),TRUE),L"SHORTCUT");
}
inline void InstallController() {
    auto exe=ControllerPath(); auto folder=exe.substr(0,exe.find_last_of(L'\\'));
    int error=SHCreateDirectoryExW(nullptr,folder.c_str(),nullptr);
    if(error!=ERROR_SUCCESS&&error!=ERROR_ALREADY_EXISTS&&error!=ERROR_FILE_EXISTS)throw Failure{L"SHORTCUT",DWORD(error)};
    wchar_t source[32768]; DWORD n=GetModuleFileNameW(nullptr,source,32768); Win(n&&n<32768,L"SHORTCUT");
    if(_wcsicmp(source,exe.c_str()) && !CopyFileW(source,exe.c_str(),FALSE)) {
        DWORD copyError=GetLastError();
        // Only reuse a locked executable when every byte matches this build.
        HANDLE first=CreateFileW(source,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,nullptr,OPEN_EXISTING,0,nullptr);
        HANDLE second=CreateFileW(exe.c_str(),GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,nullptr,OPEN_EXISTING,0,nullptr);
        bool same=first!=INVALID_HANDLE_VALUE&&second!=INVALID_HANDLE_VALUE;
        BYTE a[4096],b[4096];DWORD na=0,nb=0;
        while(same){if(!ReadFile(first,a,sizeof(a),&na,nullptr)||!ReadFile(second,b,sizeof(b),&nb,nullptr)){same=false;break;}if(na!=nb||memcmp(a,b,na)!=0){same=false;break;}if(!na)break;}
        if(first!=INVALID_HANDLE_VALUE)CloseHandle(first);if(second!=INVALID_HANDLE_VALUE)CloseHandle(second);
        if(!same)throw Failure{L"SHORTCUT",copyError};
    }
    auto programs=KnownPath(FOLDERID_Programs)+L"\\TOLF";
    error=SHCreateDirectoryExW(nullptr,programs.c_str(),nullptr);
    if(error!=ERROR_SUCCESS&&error!=ERROR_ALREADY_EXISTS&&error!=ERROR_FILE_EXISTS)throw Failure{L"SHORTCUT",DWORD(error)};
    auto startup=KnownPath(FOLDERID_Startup)+L"\\TOLF VPN.lnk";
    if(GetFileAttributesW(startup.c_str())!=INVALID_FILE_ATTRIBUTES)Shortcut(startup,exe,L"--tray");
    Shortcut(programs+L"\\TOLF VPN.lnk",exe,L"--manage");
    Shortcut(KnownPath(FOLDERID_Desktop)+L"\\TOLF VPN.lnk",exe,L"--manage");
    Shortcut(programs+L"\\TOLF VPN Widget.lnk",exe,L"--widget");
    Shortcut(KnownPath(FOLDERID_Desktop)+L"\\TOLF VPN Widget.lnk",exe,L"--widget");
}
inline void LaunchController(const wchar_t* args) {
    auto exe=ControllerPath(); auto result=reinterpret_cast<INT_PTR>(ShellExecuteW(nullptr,L"open",exe.c_str(),args,nullptr,SW_SHOWNORMAL));
    if(result<=32)throw Failure{L"SHORTCUT",DWORD(result)};
}
// UI metadata is separate from the RAS name, credentials and route settings.
inline std::wstring ReadLabelValue(const std::wstring& id,const wchar_t* field){
 wchar_t value[512]={};DWORD bytes=sizeof(value);
 if(RegGetValueW(HKEY_CURRENT_USER,RoutesKey(id).c_str(),field,RRF_RT_REG_SZ,nullptr,value,&bytes)!=ERROR_SUCCESS)return L"";
 return value;
}
inline void SaveProfileLabels(const Settings& c){
 if(c.displayName.empty())return; // Older APIs cannot identify the routing mode reliably.
 HKEY key=nullptr;DWORD e=RegCreateKeyExW(HKEY_CURRENT_USER,RoutesKey(c.id).c_str(),0,nullptr,0,KEY_SET_VALUE,nullptr,&key,nullptr);
 if(e)throw Failure{L"SETTINGS",e};
 for(const auto& item:std::vector<std::pair<const wchar_t*,std::wstring>>{{L"DisplayName",c.displayName},{L"RoutingMode",c.routingMode}}){
  e=RegSetValueExW(key,item.first,0,REG_SZ,reinterpret_cast<const BYTE*>(item.second.c_str()),DWORD((item.second.size()+1)*sizeof(wchar_t)));
  if(e){RegCloseKey(key);throw Failure{L"SETTINGS",e};}
 }
 RegCloseKey(key);
}
struct LocalProfile { std::wstring id,name,server,displayName,routingMode; };
inline std::vector<LocalProfile> LocalProfiles() {
    auto pb=Phonebook(); DWORD bytes=sizeof(RASENTRYNAMEW),count=0; std::vector<BYTE> buffer(bytes);
    auto entries=reinterpret_cast<RASENTRYNAMEW*>(buffer.data()); entries[0].dwSize=sizeof(RASENTRYNAMEW);
    DWORD e=RasEnumEntriesW(nullptr,pb.c_str(),entries,&bytes,&count);
    if(e==ERROR_BUFFER_TOO_SMALL){buffer.resize(bytes);entries=reinterpret_cast<RASENTRYNAMEW*>(buffer.data());entries[0].dwSize=sizeof(RASENTRYNAMEW);e=RasEnumEntriesW(nullptr,pb.c_str(),entries,&bytes,&count);}
    if(e==ERROR_CANNOT_OPEN_PHONEBOOK||e==ERROR_FILE_NOT_FOUND)return {};
    if(e)throw Failure{L"VPN_CONFIGURATION",e};
    std::vector<LocalProfile> result;
    for(DWORD i=0;i<count;i++) {
        std::wstring name=entries[i].szEntryName; std::wsmatch match;
        if(!std::regex_match(name,match,std::wregex(L"TOLF - (Riga|Moscow) - ([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")))continue;
        Settings c;c.id=match[2];c.server=match[1]==L"Moscow"?L"ikev2.tolf.is":L"ikev2-riga.tolf.is";
        try{if(Existing(pb,name,c))result.push_back({c.id,name,c.server,ReadLabelValue(c.id,L"DisplayName"),ReadLabelValue(c.id,L"RoutingMode")});}catch(const Failure&){continue;}
    }
    return result;
}
inline HRASCONN ProfileConnection(const std::wstring& name, RASCONNSTATUSW* connectionStatus=nullptr, LUID* luid=nullptr) {
    auto pb=Phonebook(); DWORD bytes=sizeof(RASCONNW),count=0;std::vector<BYTE> buffer(bytes);
    auto entries=reinterpret_cast<RASCONNW*>(buffer.data());entries[0].dwSize=sizeof(RASCONNW);
    DWORD e=RasEnumConnectionsW(entries,&bytes,&count);
    if(e==ERROR_BUFFER_TOO_SMALL){buffer.resize(bytes);entries=reinterpret_cast<RASCONNW*>(buffer.data());entries[0].dwSize=sizeof(RASCONNW);e=RasEnumConnectionsW(entries,&bytes,&count);}
    if(e)throw Failure{L"VPN_CONFIGURATION",e};
    for(DWORD i=0;i<count;i++)if(name==entries[i].szEntryName&&_wcsicmp(pb.c_str(),entries[i].szPhonebook)==0) {
        RASCONNSTATUSW s={};s.dwSize=sizeof(s);
        if(RasGetConnectStatusW(entries[i].hrasconn,&s))continue;
        if(connectionStatus)*connectionStatus=s;if(luid)*luid=entries[i].luid;return entries[i].hrasconn;
    }
    return nullptr;
}
// Save a replacement credential only; never recreate the connection or its routes.
inline void UpdatePassword(const LocalProfile& profile,const Secret& password) {
    if(password.value.empty()||password.value.size()>PWLEN||password.value==std::wstring(16,L'*')||
       std::any_of(password.value.begin(),password.value.end(),[](wchar_t c){return c<32;}))
        throw Failure{L"CREDENTIALS",ERROR_INVALID_PARAMETER};
    Settings c;c.id=profile.id;c.server=profile.server;
    if((c.server!=L"ikev2-riga.tolf.is"&&c.server!=L"ikev2.tolf.is")||profile.name!=ProfileName(c))
        throw Failure{L"CREDENTIALS",ERROR_INVALID_PARAMETER};
    auto pb=Phonebook();
    if(!Existing(pb,profile.name,c))throw Failure{L"CREDENTIALS",ERROR_CANNOT_FIND_PHONEBOOK_ENTRY};
    if(ProfileConnection(profile.name))throw Failure{L"CREDENTIALS",ERROR_BUSY};
    std::wstring user=L"user_";for(auto ch:profile.id)if(ch!=L'-')user+=ch;
    RASCREDENTIALSW credentials={};credentials.dwSize=sizeof(credentials);
    struct Wipe {RASCREDENTIALSW& c;~Wipe(){SecureZeroMemory(&c,sizeof(c));}} wipe{credentials};
    credentials.dwMask=RASCM_UserName|RASCM_Password|RASCM_Domain;
    wcscpy_s(credentials.szUserName,user.c_str());wcscpy_s(credentials.szPassword,password.value.c_str());
    DWORD e=RasSetCredentialsW(pb.c_str(),profile.name.c_str(),&credentials,FALSE);
    if(e)throw Failure{L"CREDENTIALS",e};
}

inline std::wstring ConnectionDns(const std::wstring& name) {
    LUID luid={};if(!ProfileConnection(name,nullptr,&luid))return L"";
    ULONG bytes=16384;std::vector<BYTE> buffer(bytes);ULONG e=GetAdaptersAddresses(AF_UNSPEC,GAA_FLAG_SKIP_ANYCAST|GAA_FLAG_SKIP_MULTICAST,nullptr,reinterpret_cast<IP_ADAPTER_ADDRESSES*>(buffer.data()),&bytes);
    if(e==ERROR_BUFFER_OVERFLOW){buffer.resize(bytes);e=GetAdaptersAddresses(AF_UNSPEC,GAA_FLAG_SKIP_ANYCAST|GAA_FLAG_SKIP_MULTICAST,nullptr,reinterpret_cast<IP_ADAPTER_ADDRESSES*>(buffer.data()),&bytes);}
    if(e)return L"";
    ULONGLONG wanted=(ULONGLONG(DWORD(luid.HighPart))<<32)|luid.LowPart;
    std::wstring result;
    for(auto a=reinterpret_cast<IP_ADAPTER_ADDRESSES*>(buffer.data());a;a=a->Next)if(a->Luid.Value==wanted) {
        for(auto d=a->FirstDnsServerAddress;d;d=d->Next) {
            wchar_t host[NI_MAXHOST]={};
            if(GetNameInfoW(d->Address.lpSockaddr,d->Address.iSockaddrLength,host,NI_MAXHOST,nullptr,0,NI_NUMERICHOST)==0){if(!result.empty())result+=L", ";result+=host;}
        }
    }
    return result;
}
// EAP can require Windows UI even when ordinary RAS credentials are saved.
struct SavedEapIdentity {
    LPRASEAPUSERIDENTITYW value=nullptr;
    bool needsInteraction=false;
    SavedEapIdentity(const std::wstring& pb,const std::wstring& name) {
        DWORD e=RasGetEapUserIdentityW(pb.c_str(),name.c_str(),RASEAPF_NonInteractive,nullptr,&value);
        needsInteraction=e==ERROR_INTERACTIVE_MODE;
        if(e&&e!=ERROR_INVALID_FUNCTION_FOR_ENTRY&&!needsInteraction){
            if(value){RasFreeEapUserIdentityW(value);value=nullptr;}
            throw Failure{L"EAP_IDENTITY",e};
        }
    }
    ~SavedEapIdentity(){if(value)RasFreeEapUserIdentityW(value);}
    SavedEapIdentity(const SavedEapIdentity&)=delete;
};
inline void DialWithWindows(std::wstring pb,std::wstring name,HWND owner) {
    RASDIALDLG dialog={};dialog.dwSize=sizeof(dialog);dialog.hwndOwner=owner;
    if(!RasDialDlgW(pb.data(),name.data(),nullptr,&dialog))
        throw Failure{L"CONNECT",dialog.dwError?dialog.dwError:ERROR_CANCELLED};
    if(!Connected(pb,name))throw Failure{L"CONNECT",ERROR_NOT_CONNECTED};
}
inline void DialProfile(const std::wstring& name,HWND owner=nullptr) {
    if(ProfileConnection(name))throw Failure{L"VPN_CONFIGURATION",ERROR_BUSY};
    auto pb=Phonebook();RASDIALPARAMSW params={};params.dwSize=sizeof(params);wcscpy_s(params.szEntryName,name.c_str());
    struct Wipe { RASDIALPARAMSW& p; ~Wipe(){SecureZeroMemory(&p,sizeof(p));} }wipe{params};
    BOOL password=FALSE;DWORD e=RasGetEntryDialParamsW(pb.c_str(),&params,&password);
    if(e)throw Failure{L"CREDENTIALS",e};
    SavedEapIdentity identity(pb,name);
    if(identity.needsInteraction||!password){DialWithWindows(pb,name,owner);return;}
    RASDIALEXTENSIONS ext={};ext.dwSize=sizeof(ext);
    if(identity.value){wcscpy_s(params.szUserName,identity.value->szUserName);ext.RasEapInfo.dwSizeofEapInfo=identity.value->dwSizeofEapInfo;ext.RasEapInfo.pbEapInfo=identity.value->pbEapInfo;}
    HRASCONN handle=nullptr;e=RasDialW(&ext,pb.c_str(),&params,0,nullptr,&handle);
    RASCONNSTATUSW state={};state.dwSize=sizeof(state);
    if(!e)e=RasGetConnectStatusW(handle,&state);
    if(!e&&state.rasconnstate!=RASCS_Connected)e=ERROR_NOT_CONNECTED;
    if(e){if(handle)RasHangUpW(handle);throw Failure{L"CONNECT",e};}
    // Leave successful connections owned by Windows after this application exits.
}
inline void DisconnectProfile(const std::wstring& name) {
    HRASCONN handle=ProfileConnection(name);if(!handle)return;
    DWORD e=RasHangUpW(handle);if(e&&e!=ERROR_INVALID_HANDLE)throw Failure{L"DISCONNECT",e};
    for(int i=0;i<100;i++){RASCONNSTATUSW s={};s.dwSize=sizeof(s);if(RasGetConnectStatusW(handle,&s)==ERROR_INVALID_HANDLE)return;Sleep(100);}
    throw Failure{L"DISCONNECT",ERROR_TIMEOUT};
}

