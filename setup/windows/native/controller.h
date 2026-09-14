#pragma once
#include "routes.h"
#include <ws2tcpip.h>
#include <iphlpapi.h>
#include <shobjidl.h>

inline std::wstring KnownPath(REFKNOWNFOLDERID id) {
    PWSTR value=nullptr; Hr(SHGetKnownFolderPath(id,0,nullptr,&value),L"SHORTCUT");
    std::wstring result=value; CoTaskMemFree(value); return result;
}
inline std::wstring ControllerPath() { return KnownPath(FOLDERID_LocalAppData)+L"\\TOLF\\VPN\\2.3.0\\TOLF-VPN.exe"; }
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
    if(_wcsicmp(source,exe.c_str())) {
        // A running version cannot be overwritten. Reusing exactly the same version is safe.
        if(!CopyFileW(source,exe.c_str(),FALSE)) {
            DWORD e=GetLastError();
            if(e!=ERROR_SHARING_VIOLATION)throw Failure{L"SHORTCUT",e};
        }
    }
    auto programs=KnownPath(FOLDERID_Programs)+L"\\TOLF";
    error=SHCreateDirectoryExW(nullptr,programs.c_str(),nullptr);
    if(error!=ERROR_SUCCESS&&error!=ERROR_ALREADY_EXISTS&&error!=ERROR_FILE_EXISTS)throw Failure{L"SHORTCUT",DWORD(error)};
    Shortcut(programs+L"\\TOLF VPN.lnk",exe,L"--manage");
    Shortcut(KnownPath(FOLDERID_Desktop)+L"\\TOLF VPN.lnk",exe,L"--manage");
    Shortcut(programs+L"\\TOLF VPN Widget.lnk",exe,L"--widget");
    Shortcut(KnownPath(FOLDERID_Desktop)+L"\\TOLF VPN Widget.lnk",exe,L"--widget");
}
inline void LaunchController(const wchar_t* args) {
    auto exe=ControllerPath(); auto result=reinterpret_cast<INT_PTR>(ShellExecuteW(nullptr,L"open",exe.c_str(),args,nullptr,SW_SHOWNORMAL));
    if(result<=32)throw Failure{L"SHORTCUT",DWORD(result)};
}
struct LocalProfile { std::wstring id,name,server; };
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
        if(!std::regex_match(name,match,std::wregex(L"TOLF - Riga - ([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")))continue;
        Settings c;c.id=match[1];c.server=L"ikev2-riga.tolf.is";
        try{if(Existing(pb,name,c))result.push_back({c.id,name,c.server});}catch(const Failure&){continue;}
    }
    return result;
}
inline HRASCONN ProfileConnection(const std::wstring& name, RASCONNSTATUSW* status=nullptr, LUID* luid=nullptr) {
    auto pb=Phonebook(); DWORD bytes=sizeof(RASCONNW),count=0;std::vector<BYTE> buffer(bytes);
    auto entries=reinterpret_cast<RASCONNW*>(buffer.data());entries[0].dwSize=sizeof(RASCONNW);
    DWORD e=RasEnumConnectionsW(entries,&bytes,&count);
    if(e==ERROR_BUFFER_TOO_SMALL){buffer.resize(bytes);entries=reinterpret_cast<RASCONNW*>(buffer.data());entries[0].dwSize=sizeof(RASCONNW);e=RasEnumConnectionsW(entries,&bytes,&count);}
    if(e)throw Failure{L"VPN_CONFIGURATION",e};
    for(DWORD i=0;i<count;i++)if(name==entries[i].szEntryName&&_wcsicmp(pb.c_str(),entries[i].szPhonebook)==0) {
        RASCONNSTATUSW s={};s.dwSize=sizeof(s);
        if(RasGetConnectStatusW(entries[i].hrasconn,&s))continue;
        if(status)*status=s;if(luid)*luid=entries[i].luid;return entries[i].hrasconn;
    }
    return nullptr;
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
// Native RAS with saved Windows credentials. No shell, domain prompt or token files.
inline void DialProfile(const std::wstring& name) {
    if(ProfileConnection(name))throw Failure{L"VPN_CONFIGURATION",ERROR_BUSY};
    auto pb=Phonebook();RASDIALPARAMSW params={};params.dwSize=sizeof(params);wcscpy_s(params.szEntryName,name.c_str());
    struct Wipe { RASDIALPARAMSW& p; ~Wipe(){SecureZeroMemory(&p,sizeof(p));} }wipe{params};
    BOOL password=FALSE;DWORD e=RasGetEntryDialParamsW(pb.c_str(),&params,&password);
    if(e)throw Failure{L"CREDENTIALS",e};if(!password)throw Failure{L"CREDENTIALS",ERROR_NO_SUCH_LOGON_SESSION};
    LPRASEAPUSERIDENTITYW identity=nullptr;
    e=RasGetEapUserIdentityW(pb.c_str(),name.c_str(),RASEAPF_NonInteractive,nullptr,&identity);
    struct FreeIdentity{LPRASEAPUSERIDENTITYW& p;~FreeIdentity(){if(p)RasFreeEapUserIdentityW(p);}}free{identity};
    if(e&&e!=ERROR_INVALID_FUNCTION_FOR_ENTRY)throw Failure{L"CREDENTIALS",e};
    RASDIALEXTENSIONS ext={};ext.dwSize=sizeof(ext);
    if(identity){wcscpy_s(params.szUserName,identity->szUserName);ext.RasEapInfo.dwSizeofEapInfo=identity->dwSizeofEapInfo;ext.RasEapInfo.pbEapInfo=identity->pbEapInfo;}
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
