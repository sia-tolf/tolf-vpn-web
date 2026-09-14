#include "../../setup/windows/native/controller.h"
#include <cstdio>
#define TOLF_EMBED_TESTS
#include "networks.cpp"
static void Check(bool x){if(!x)throw Failure{L"TEST_ASSERT",1};}
int wmain(){std::wstring name,moscowName;bool owned=false,moscowOwned=false;try{
 NetworkTests();
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
 Settings mc;ParseSettings(LR"({"deviceId":"12345678-1234-1234-1234-123456789abc","server":"ikev2.tolf.is","username":"user_12345678123412341234123456789abc","password":"dummy!"})",mc);
 moscowName=ProfileName(mc);Check(moscowName==L"TOLF - Moscow - "+mc.id);Check(!Existing(pb,moscowName,mc));
 Configure(w,mc,moscowName);moscowOwned=true;Check(Existing(pb,moscowName,mc));
 bool discovered=false;for(const auto& p:LocalProfiles())if(p.name==moscowName){Check(p.server==L"ikev2.tolf.is");Check(p.id==mc.id);discovered=true;}Check(discovered);
 // Updating a password keeps the existing profile, IPsec flags and exclusions.
 auto passwordRoutes=CheckedNetworks(L"192.168.201.0/24");ConfigureRoutes(w,mc,moscowName,passwordRoutes);
 auto beforePassword=RouteEntry(pb,moscowName);auto flagsBefore=reinterpret_cast<RASENTRYW*>(beforePassword.data())->dwfOptions2;
 LocalProfile localMoscow{mc.id,moscowName,mc.server};Secret replacement;replacement.value=L"ci-replacement-secret";
 UpdatePassword(localMoscow,replacement);Check(Existing(pb,moscowName,mc));Check(SavedNetworks(mc.id)==NetworkText(passwordRoutes));
 auto afterPassword=RouteEntry(pb,moscowName);Check(reinterpret_cast<RASENTRYW*>(afterPassword.data())->dwfOptions2==flagsBefore);
 RASCREDENTIALSW saved={};saved.dwSize=sizeof(saved);saved.dwMask=RASCM_UserName|RASCM_Password;
 Check(RasGetCredentialsW(pb.c_str(),moscowName.c_str(),&saved)==0);Check(std::wstring(saved.szUserName)==mc.user);Check((saved.dwMask&RASCM_Password)!=0);SecureZeroMemory(&saved,sizeof(saved));
 for(auto invalid:{L"",L"****************",L"bad\npassword"}){Secret bad;bad.value=invalid;bool rejected=false;try{UpdatePassword(localMoscow,bad);}catch(const Failure&){rejected=true;}Check(rejected);}
 RegDeleteTreeW(HKEY_CURRENT_USER,RoutesKey(mc.id).c_str());
 std::puts("PASS password update preserves profile, location and routes; invalid secrets rejected");
 Check(RasDeleteEntryW(pb.c_str(),moscowName.c_str())==0);moscowOwned=false;
 bool passwordMissing=false;try{UpdatePassword(localMoscow,replacement);}catch(const Failure& f){passwordMissing=f.code==ERROR_CANNOT_FIND_PHONEBOOK_ENTRY;}Check(passwordMissing);Check(!Existing(pb,moscowName,mc));
 std::puts("PASS Moscow settings, native profile server and controller discovery");

 {SavedEapIdentity identity(pb,name);Check(identity.needsInteraction||identity.value!=nullptr);
 std::puts(identity.needsInteraction?"PASS fresh EAP credentials require Windows UI without failing with 703":"PASS cached EAP identity available");}

 auto entryBefore=RouteEntry(pb,name);DWORD options2=reinterpret_cast<RASENTRYW*>(entryBefore.data())->dwfOptions2;
 auto checkFlags=[&](bool full){auto buffer=RouteEntry(pb,name);auto entry=reinterpret_cast<RASENTRYW*>(buffer.data());Check(bool(entry->dwfOptions & RASEO_RemoteDefaultGateway)==full);Check(entry->dwfOptions2==options2);};
 auto exclusions=CheckedNetworks(L"192.168.200.0/24\r\n10.90.0.0/16");
 ConfigureRoutes(w,c,name,exclusions);checkFlags(false);Check(SavedNetworks(c.id)==NetworkText(exclusions));
 ConfigureRoutes(w,c,name,exclusions);std::puts("PASS saved per-user exclusions and repeat configuration");
 bool routeRollback=false;try{ConfigureRoutes(w,c,name,CheckedNetworks(L"172.20.0.0/16"),0);}catch(const Failure&f){routeRollback=f.stage==L"TEST_ROUTE_ROLLBACK";}Check(routeRollback);checkFlags(false);Check(SavedNetworks(c.id)==NetworkText(exclusions));
 ConfigureRoutes(w,c,name,{});checkFlags(true);Check(SavedNetworks(c.id).empty());
 ConfigureRoutes(w,c,name,{});std::puts("PASS route rollback and return to full tunnel");
 RASCREDENTIALSW before={};before.dwSize=sizeof(before);before.dwMask=RASCM_UserName|RASCM_Password;
 Check(RasGetCredentialsW(pb.c_str(),name.c_str(),&before)==0);
 Settings local;local.id=c.id;local.server=c.server;local.user=L"must-not-be-written";
 ConfigureRoutes(w,local,name,exclusions,-1,true);checkFlags(false);
 RASCREDENTIALSW after={};after.dwSize=sizeof(after);after.dwMask=RASCM_UserName|RASCM_Password;
 Check(RasGetCredentialsW(pb.c_str(),name.c_str(),&after)==0);
 Check(std::wstring(before.szUserName)==after.szUserName);Check((before.dwMask & RASCM_Password)==(after.dwMask & RASCM_Password));
 SecureZeroMemory(&before,sizeof(before));SecureZeroMemory(&after,sizeof(after));
 ConfigureRoutes(w,local,name,{},-1,true);checkFlags(true);
 std::puts("PASS settings-only edit preserves Windows credentials");

 RegDeleteTreeW(HKEY_CURRENT_USER,RoutesKey(c.id).c_str());
 Settings wrong;wrong.server=L"unexpected.example";bool conflict=false;try{Existing(pb,name,wrong);}catch(const Failure&f){conflict=f.stage==L"NAME_CONFLICT";}Check(conflict);std::puts("PASS conflicting entry rejection");
 DWORD r=RasDeleteEntryW(pb.c_str(),name.c_str());if(r)throw Failure{L"TEST_DELETE",r};owned=false;
 bool rollback=false;try{Configure(w,c,name,true);}catch(const Failure&f){rollback=f.stage==L"TEST_ROLLBACK";}Check(rollback);Check(!Existing(pb,name,c));std::puts("PASS rollback of newly created connection");
 rollback=false;try{ConfigureRoutes(w,c,name,exclusions,0);}catch(const Failure&f){rollback=f.stage==L"TEST_ROUTE_ROLLBACK";}Check(rollback);Check(!Existing(pb,name,c));Check(SavedNetworks(c.id).empty());std::puts("PASS rollback of new profile with route failure");
 bool absent=false;try{ConfigureRoutes(w,c,name,{},-1,true);}catch(const Failure& f){absent=f.code==ERROR_CANNOT_FIND_PHONEBOOK_ENTRY;}Check(absent);Check(!Existing(pb,name,c));
 std::puts("PASS settings cannot recreate a removed profile");return 0;
 }catch(const Failure&f){std::fwprintf(stderr,L"FAIL %ls: %lu (0x%08lx)\n",f.stage.c_str(),f.code,f.code);if(moscowOwned)RasDeleteEntryW(Phonebook().c_str(),moscowName.c_str());if(owned)RasDeleteEntryW(Phonebook().c_str(),name.c_str());return 1;}catch(...){std::puts("FAIL unexpected exception");return 1;}}

