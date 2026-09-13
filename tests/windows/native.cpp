#include "../../setup/windows/native/core.h"
#include <cstdio>
static void Check(bool x){if(!x)throw Failure{L"TEST_ASSERT",1};}
int wmain(){std::wstring name;bool owned=false;try{
 Check(Token(L"https://api.tolf.is/windows/p/abcdefghijklmnopqrstuvwxyz123456")==L"abcdefghijklmnopqrstuvwxyz123456");
 for(auto s:{L"https://api.tolf.is.evil/windows/p/abcdefghijklmnopqrstuvwxyz123456",L"http://api.tolf.is/windows/p/abcdefghijklmnopqrstuvwxyz123456",L"https://api.tolf.is/windows/p/abcdefghijklmnopqrstuvwxyz123456?x=1",L"https://evil@api.tolf.is/windows/p/abcdefghijklmnopqrstuvwxyz123456"}){bool bad=false;try{Token(s);}catch(const Failure&){bad=true;}Check(bad);}
 Check(FilenameToken(L"TOLF-Setup-abcdefghijklmnopqrstuvwxyz123456 (2).exe")==L"abcdefghijklmnopqrstuvwxyz123456");
 Settings c;ParseSettings(LR"({"deviceId":"12345678-1234-1234-1234-123456789abc","server":"ikev2-riga.tolf.is","username":"user_12345678123412341234123456789abc","password":"dummy\u0021"})",c);Check(c.password.value==L"dummy!");
 for(auto s:{LR"({"a":"b","a":"c"})",LR"({"a":true})",LR"({"a":"b"} garbage)"}){bool bad=false;try{Json(s).parse();}catch(const Failure&){bad=true;}Check(bad);}
 std::puts("PASS URL, token and strict JSON validation");
 Com com;Hr(CoInitializeSecurity(nullptr,-1,nullptr,nullptr,RPC_C_AUTHN_LEVEL_DEFAULT,RPC_C_IMP_LEVEL_IMPERSONATE,nullptr,EOAC_NONE,nullptr),L"TEST_COM");Wmi w;Preflight(w);std::puts("PASS native provider and service preflight");
 GUID id;Hr(CoCreateGuid(&id),L"TEST_GUID");wchar_t guid[40];StringFromGUID2(id,guid,40);name=L"TOLF CI "+std::wstring(guid);auto pb=Phonebook();Check(!Existing(pb,name,c));
 Configure(w,c,name);owned=true;Check(Existing(pb,name,c));std::puts("PASS native IKEv2 creation, IPsec policy and credential save");
 Configure(w,c,name);std::puts("PASS repeat setup without duplicate entry");
 Settings wrong;wrong.server=L"unexpected.example";bool conflict=false;try{Existing(pb,name,wrong);}catch(const Failure&f){conflict=f.stage==L"NAME_CONFLICT";}Check(conflict);std::puts("PASS conflicting entry rejection");
 DWORD r=RasDeleteEntryW(pb.c_str(),name.c_str());if(r)throw Failure{L"TEST_DELETE",r};owned=false;
 bool rollback=false;try{Configure(w,c,name,true);}catch(const Failure&f){rollback=f.stage==L"TEST_ROLLBACK";}Check(rollback);Check(!Existing(pb,name,c));std::puts("PASS rollback of newly created connection");return 0;
 }catch(const Failure&f){std::fwprintf(stderr,L"FAIL %ls: %lu (0x%08lx)\n",f.stage.c_str(),f.code,f.code);if(owned)RasDeleteEntryW(Phonebook().c_str(),name.c_str());return 1;}catch(...){std::puts("FAIL unexpected exception");return 1;}}
