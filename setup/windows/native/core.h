#pragma once
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#define UNICODE
#define _UNICODE
#define _WIN32_WINNT 0x0A00
#include <windows.h>
#include <ras.h>
#include <raserror.h>
#include <rasdlg.h>
#include <winhttp.h>
#include <wbemidl.h>
#include <wrl/client.h>
#include <shlobj.h>
#include <string>
#include <map>
#include <vector>
#include <regex>
#include <stdexcept>
#include <utility>
using Microsoft::WRL::ComPtr;
struct Failure { std::wstring stage; DWORD code; };
inline void Hr(HRESULT h, const wchar_t* s) { if(FAILED(h)) throw Failure{s,(DWORD)h}; }
inline void Win(bool ok, const wchar_t* s) { if(!ok) throw Failure{s,GetLastError()}; }
struct Bstr { BSTR p; explicit Bstr(const wchar_t* s):p(SysAllocString(s)){if(!p)throw std::bad_alloc();} ~Bstr(){SysFreeString(p);} operator BSTR() const{return p;} };
struct Var:VARIANT { Var(){VariantInit(this);} ~Var(){VariantClear(this);} Var(const Var&)=delete; };
struct Com { Com(){Hr(CoInitializeEx(nullptr,COINIT_MULTITHREADED),L"WINDOWS_COMPONENTS");} ~Com(){CoUninitialize();} };
struct Secret { std::wstring value; ~Secret(){ if(!value.empty())SecureZeroMemory(value.data(),value.size()*sizeof(wchar_t));} };
struct Settings {std::wstring id,server,user; Secret password;};
// The settings contract is a small flat JSON object of strings. Reject duplicates,
// nested values, trailing data and control characters rather than guessing.
class Json {
 const std::wstring& s; size_t p=0;
 void ws(){while(p<s.size()&&(s[p]==L' '||s[p]==L'\r'||s[p]==L'\n'||s[p]==L'\t'))++p;}
 void bad(){throw Failure{L"SETTINGS",ERROR_INVALID_DATA};}
 wchar_t take(){if(p==s.size())bad();return s[p++];}
 std::wstring str(){if(take()!=L'"')bad(); std::wstring o; for(;;){wchar_t c=take();if(c==L'"')return o;if(c<32)bad();if(c==L'\\'){c=take();switch(c){case L'"':case L'\\':case L'/':break;case L'b':c=8;break;case L'f':c=12;break;case L'n':c=10;break;case L'r':c=13;break;case L't':c=9;break;case L'u':{unsigned n=0;for(int i=0;i<4;i++){wchar_t h=take();n*=16;if(h>=L'0'&&h<=L'9')n+=h-L'0';else if(h>=L'a'&&h<=L'f')n+=h-L'a'+10;else if(h>=L'A'&&h<=L'F')n+=h-L'A'+10;else bad();}c=(wchar_t)n;break;}default:bad();}}o+=c;}}
public:
 explicit Json(const std::wstring& text):s(text){}
 std::map<std::wstring,std::wstring> parse(){std::map<std::wstring,std::wstring> m;ws();if(take()!=L'{')bad();ws();if(p<s.size()&&s[p]==L'}'){++p;}else for(;;){ws();auto k=str();ws();if(take()!=L':')bad();ws();auto v=str();if(!m.emplace(k,v).second)bad();ws();auto c=take();if(c==L'}')break;if(c!=L',')bad();}ws();if(p!=s.size())bad();return m;}
};
inline std::wstring Token(const std::wstring& text){std::wsmatch m;if(!std::regex_match(text,m,std::wregex(L"https://api\\.tolf\\.is/windows/p/([A-Za-z0-9_-]{32})/?")))throw Failure{L"LINK",0};return m[1];}
inline std::wstring FilenameToken(const std::wstring& file){std::wsmatch m;if(std::regex_match(file,m,std::wregex(L"TOLF-Setup-([A-Za-z0-9_-]{32})(?:[ ]*\\([0-9]+\\))?\\.exe",std::regex::icase)))return m[1];return L"";}
inline void ParseSettings(const std::wstring& text, Settings& c){
 auto m=Json(text).parse();
 struct Wipe{std::map<std::wstring,std::wstring>&m;~Wipe(){for(auto&kv:m)if(!kv.second.empty())SecureZeroMemory(kv.second.data(),kv.second.size()*2);}}wipe{m};
 if(m.size()!=4||!m.count(L"deviceId")||!m.count(L"server")||!m.count(L"username")||!m.count(L"password"))throw Failure{L"SETTINGS",1};
 c.id=m[L"deviceId"];c.server=m[L"server"];c.user=m[L"username"];c.password.value=m[L"password"];
 if(!std::regex_match(c.id,std::wregex(L"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"))||c.server!=L"ikev2-riga.tolf.is")throw Failure{L"SETTINGS",2};
 std::wstring plain;for(auto ch:c.id)if(ch!=L'-')plain+=ch;
 if(c.user!=L"user_"+plain||c.password.value.empty()||c.password.value.size()>256)throw Failure{L"SETTINGS",3};
 for(wchar_t ch:c.password.value)if(ch<32||ch==127)throw Failure{L"SETTINGS",4};
}
struct Http {HINTERNET h;explicit Http(HINTERNET v):h(v){Win(h!=nullptr,L"NETWORK");}~Http(){WinHttpCloseHandle(h);}operator HINTERNET()const{return h;}};
inline void Fetch(const std::wstring& token,Settings& c){
 Http session(WinHttpOpen(L"TOLF-Setup/2.0",WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY,WINHTTP_NO_PROXY_NAME,WINHTTP_NO_PROXY_BYPASS,0));
 Win(WinHttpSetTimeouts(session,15000,15000,15000,15000),L"NETWORK");
 DWORD tls=WINHTTP_FLAG_SECURE_PROTOCOL_TLS1_2;Win(WinHttpSetOption(session,WINHTTP_OPTION_SECURE_PROTOCOLS,&tls,sizeof(tls)),L"NETWORK");
 Http host(WinHttpConnect(session,L"api.tolf.is",INTERNET_DEFAULT_HTTPS_PORT,0));
 std::wstring path=L"/windows/p/"+token+L"/settings";
 Http req(WinHttpOpenRequest(host,L"POST",path.c_str(),nullptr,WINHTTP_NO_REFERER,WINHTTP_DEFAULT_ACCEPT_TYPES,WINHTTP_FLAG_SECURE));
 DWORD redirect=WINHTTP_OPTION_REDIRECT_POLICY_NEVER;Win(WinHttpSetOption(req,WINHTTP_OPTION_REDIRECT_POLICY,&redirect,sizeof(redirect)),L"NETWORK");
 DWORD disabled=WINHTTP_DISABLE_COOKIES|WINHTTP_DISABLE_AUTHENTICATION;Win(WinHttpSetOption(req,WINHTTP_OPTION_DISABLE_FEATURE,&disabled,sizeof(disabled)),L"NETWORK");
 Win(WinHttpSendRequest(req,WINHTTP_NO_ADDITIONAL_HEADERS,0,WINHTTP_NO_REQUEST_DATA,0,0,0),L"NETWORK");Win(WinHttpReceiveResponse(req,nullptr),L"NETWORK");
 DWORD status=0,len=sizeof(status);Win(WinHttpQueryHeaders(req,WINHTTP_QUERY_STATUS_CODE|WINHTTP_QUERY_FLAG_NUMBER,WINHTTP_HEADER_NAME_BY_INDEX,&status,&len,WINHTTP_NO_HEADER_INDEX),L"NETWORK");
 if(status!=200)throw Failure{L"NETWORK",status};
 char data[8193]={};struct W{char*p;size_t n;~W(){SecureZeroMemory(p,n);}}wipe{data,sizeof(data)};DWORD total=0,n=0;auto deadline=GetTickCount64()+30000;
 do{if(GetTickCount64()>deadline)throw Failure{L"NETWORK",ERROR_TIMEOUT};Win(WinHttpReadData(req,data+total,(DWORD)sizeof(data)-total,&n),L"NETWORK");total+=n;if(total>=sizeof(data))throw Failure{L"SETTINGS",5};}while(n);
 int chars=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,data,total,nullptr,0);if(chars<=0)throw Failure{L"SETTINGS",6};Secret text;text.value.resize(chars);MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,data,total,text.value.data(),chars);ParseSettings(text.value,c);
}
class Wmi {
 ComPtr<IWbemServices> svc;
public:
 Wmi(){ComPtr<IWbemLocator>loc;Hr(CoCreateInstance(CLSID_WbemLocator,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&loc)),L"WINDOWS_COMPONENTS");Hr(loc->ConnectServer(Bstr(L"ROOT\\Microsoft\\Windows\\RemoteAccess\\Client"),nullptr,nullptr,nullptr,WBEM_FLAG_CONNECT_USE_MAX_WAIT,nullptr,nullptr,&svc),L"WINDOWS_COMPONENTS");Hr(CoSetProxyBlanket(svc.Get(),RPC_C_AUTHN_WINNT,RPC_C_AUTHZ_NONE,nullptr,RPC_C_AUTHN_LEVEL_CALL,RPC_C_IMP_LEVEL_IMPERSONATE,nullptr,EOAC_NONE),L"WINDOWS_COMPONENTS");}
 ComPtr<IWbemClassObject> input(const wchar_t*cls,const wchar_t*method){ComPtr<IWbemClassObject>obj,signature,in;Hr(svc->GetObject(Bstr(cls),WBEM_FLAG_USE_AMENDED_QUALIFIERS,nullptr,&obj,nullptr),L"WINDOWS_COMPONENTS");Hr(obj->GetMethod(method,0,&signature,nullptr),L"WINDOWS_COMPONENTS");Hr(signature->SpawnInstance(0,&in),L"WINDOWS_COMPONENTS");return in;}
 static void text(IWbemClassObject*o,const wchar_t*k,const wchar_t*v){Var x;x.vt=VT_BSTR;x.bstrVal=SysAllocString(v);Hr(o->Put(k,0,&x,0),L"VPN_CONFIGURATION");}
 static void boolean(IWbemClassObject*o,const wchar_t*k,bool b){Var x;x.vt=VT_BOOL;x.boolVal=b?VARIANT_TRUE:VARIANT_FALSE;Hr(o->Put(k,0,&x,0),L"VPN_CONFIGURATION");}
 static void number(IWbemClassObject*o,const wchar_t*k,DWORD n){Var x;x.vt=VT_I4;x.lVal=(LONG)n;Hr(o->Put(k,0,&x,0),L"VPN_CONFIGURATION");}
 static void strings(IWbemClassObject*o,const wchar_t*k,const wchar_t*v){Var x;x.vt=VT_ARRAY|VT_BSTR;x.parray=SafeArrayCreateVector(VT_BSTR,0,1);if(!x.parray)throw std::bad_alloc();LONG ix=0;Bstr b(v);Hr(SafeArrayPutElement(x.parray,&ix,b.p),L"VPN_CONFIGURATION");Hr(o->Put(k,0,&x,0),L"VPN_CONFIGURATION");}
 void call(const wchar_t*cls,const wchar_t*method,IWbemClassObject*in){
  ComPtr<IWbemClassObject>out;
  Hr(svc->ExecMethod(Bstr(cls),Bstr(method),0,nullptr,in,&out,nullptr),method);
  if(!out)throw Failure{method,ERROR_INVALID_DATA};
  Var result;Hr(out->Get(L"ReturnValue",0,&result,nullptr,nullptr),method);
  if((result.vt!=VT_I4&&result.vt!=VT_UI4)||result.ulVal!=0)throw Failure{method,result.ulVal};
 }

 // Numeric provider enums verified against Windows VpnClient CDXML in CI.
 void policy(const std::wstring&name,bool apply){auto in=input(L"PS_VpnConnectionIPsecConfiguration",L"SetByCustomPolicy");text(in.Get(),L"ConnectionName",name.c_str());boolean(in.Get(),L"AllUserConnection",false);boolean(in.Get(),L"Force",true);boolean(in.Get(),L"PassThru",true);number(in.Get(),L"AuthenticationTransformConstants",2);number(in.Get(),L"CipherTransformConstants",5);number(in.Get(),L"EncryptionMethod",4);number(in.Get(),L"IntegrityCheckMethod",2);number(in.Get(),L"DHGroup",3);number(in.Get(),L"PfsGroup",0);if(apply)call(L"PS_VpnConnectionIPsecConfiguration",L"SetByCustomPolicy",in.Get());}
 void add(const std::wstring&name,const Settings&c){auto in=input(L"PS_VpnConnection",L"Add");text(in.Get(),L"Name",name.c_str());text(in.Get(),L"ServerAddress",c.server.c_str());text(in.Get(),L"TunnelType",L"Ikev2");text(in.Get(),L"EncryptionLevel",L"Required");strings(in.Get(),L"AuthenticationMethod",L"Eap");boolean(in.Get(),L"AllUserConnection",false);boolean(in.Get(),L"RememberCredential",true);boolean(in.Get(),L"SplitTunneling",false);boolean(in.Get(),L"UseWinlogonCredential",false);boolean(in.Get(),L"Force",true);boolean(in.Get(),L"PassThru",true);
 text(in.Get(),L"EapConfigXmlStream",LR"(<EapHostConfig xmlns="http://www.microsoft.com/provisioning/EapHostConfig"><EapMethod><Type xmlns="http://www.microsoft.com/provisioning/EapCommon">26</Type><VendorId xmlns="http://www.microsoft.com/provisioning/EapCommon">0</VendorId><VendorType xmlns="http://www.microsoft.com/provisioning/EapCommon">0</VendorType><AuthorId xmlns="http://www.microsoft.com/provisioning/EapCommon">0</AuthorId></EapMethod><Config xmlns="http://www.microsoft.com/provisioning/EapHostConfig"><Eap xmlns="http://www.microsoft.com/provisioning/BaseEapConnectionPropertiesV1"><Type>26</Type><EapType xmlns="http://www.microsoft.com/provisioning/MsChapV2ConnectionPropertiesV1"><UseWinLogonCredentials>false</UseWinLogonCredentials></EapType></Eap></Config></EapHostConfig>)");call(L"PS_VpnConnection",L"Add",in.Get());}
};
inline std::wstring Phonebook(){PWSTR path=nullptr;Hr(SHGetKnownFolderPath(FOLDERID_RoamingAppData,0,nullptr,&path),L"WINDOWS_COMPONENTS");std::wstring pb=path;CoTaskMemFree(path);return pb+L"\\Microsoft\\Network\\Connections\\Pbk\\rasphone.pbk";}
inline void Services(){SC_HANDLE scm=OpenSCManagerW(nullptr,nullptr,SC_MANAGER_CONNECT);Win(scm!=nullptr,L"VPN_SERVICE");for(auto name:{L"RasMan",L"IKEEXT",L"PolicyAgent",L"Winmgmt"}){SC_HANDLE s=OpenServiceW(scm,name,SERVICE_QUERY_CONFIG);if(!s){DWORD e=GetLastError();CloseServiceHandle(scm);throw Failure{L"VPN_SERVICE",e};}DWORD n=0;QueryServiceConfigW(s,nullptr,0,&n);std::vector<BYTE>b(n);BOOL ok=QueryServiceConfigW(s,reinterpret_cast<QUERY_SERVICE_CONFIGW*>(b.data()),n,&n);DWORD e=ok?0:GetLastError();if(ok&&reinterpret_cast<QUERY_SERVICE_CONFIGW*>(b.data())->dwStartType==SERVICE_DISABLED)e=ERROR_SERVICE_DISABLED;CloseServiceHandle(s);if(e){CloseServiceHandle(scm);throw Failure{L"VPN_SERVICE",e};}}CloseServiceHandle(scm);}
inline void Preflight(Wmi&w){Services();w.input(L"PS_VpnConnection",L"Add");w.policy(L"TOLF prerequisite check",false);}
inline bool Existing(const std::wstring&pb,const std::wstring&name,const Settings&c){DWORD n=sizeof(RASENTRYW);std::vector<BYTE>b(n);auto e=reinterpret_cast<RASENTRYW*>(b.data());e->dwSize=sizeof(RASENTRYW);DWORD r=RasGetEntryPropertiesW(pb.c_str(),name.c_str(),e,&n,nullptr,nullptr);if(r==ERROR_BUFFER_TOO_SMALL){b.resize(n);e=reinterpret_cast<RASENTRYW*>(b.data());e->dwSize=sizeof(RASENTRYW);r=RasGetEntryPropertiesW(pb.c_str(),name.c_str(),e,&n,nullptr,nullptr);}if(r==ERROR_CANNOT_FIND_PHONEBOOK_ENTRY||r==ERROR_CANNOT_OPEN_PHONEBOOK||r==ERROR_FILE_NOT_FOUND)return false;if(r)throw Failure{L"VPN_CONFIGURATION",r};if(e->dwType!=RASET_Vpn||e->dwVpnStrategy!=VS_Ikev2Only||c.server!=e->szLocalPhoneNumber||!(e->dwfOptions&RASEO_RequireEAP)||e->dwCustomAuthKey!=26)throw Failure{L"NAME_CONFLICT",0};return true;}
inline bool Connected(const std::wstring&pb,const std::wstring&name){
 DWORD size=sizeof(RASCONNW),count=0;std::vector<BYTE>buffer(size);
 auto list=reinterpret_cast<RASCONNW*>(buffer.data());list[0].dwSize=sizeof(RASCONNW);
 DWORD error=RasEnumConnectionsW(list,&size,&count);
 if(error==ERROR_BUFFER_TOO_SMALL){buffer.resize(size);list=reinterpret_cast<RASCONNW*>(buffer.data());list[0].dwSize=sizeof(RASCONNW);error=RasEnumConnectionsW(list,&size,&count);}
 if(error)throw Failure{L"VPN_CONFIGURATION",error};
 for(DWORD i=0;i<count;i++)if(name==list[i].szEntryName&&_wcsicmp(pb.c_str(),list[i].szPhonebook)==0){RASCONNSTATUSW status={};status.dwSize=sizeof(status);if(RasGetConnectStatusW(list[i].hrasconn,&status)==0&&status.rasconnstate==RASCS_Connected)return true;}
 return false;
}
inline void Configure(Wmi&w,const Settings&c,const std::wstring&name,bool failTest=false){auto pb=Phonebook();bool exists=Existing(pb,name,c),created=false;try{if(!exists){w.add(name,c);created=true;}if(!exists||!Connected(pb,name))w.policy(name,true);if(failTest)throw Failure{L"TEST_ROLLBACK",1};RASCREDENTIALSW cred={};cred.dwSize=sizeof(cred);cred.dwMask=RASCM_UserName|RASCM_Password|RASCM_Domain;wcscpy_s(cred.szUserName,c.user.c_str());wcscpy_s(cred.szPassword,c.password.value.c_str());DWORD e=RasSetCredentialsW(pb.c_str(),name.c_str(),&cred,FALSE);SecureZeroMemory(&cred,sizeof(cred));if(e)throw Failure{L"CREDENTIALS",e};}catch(...){if(created){DWORD e=RasDeleteEntryW(pb.c_str(),name.c_str());if(e)throw Failure{L"ROLLBACK",e};}throw;}}
