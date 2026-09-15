#pragma once
#include "core.h"
#include <exception>

// Preferences are per Windows user and per VPN device, never keyed by a bearer link.
inline std::wstring RoutesKey(const std::wstring& id) {
    if (!std::regex_match(id, std::wregex(L"[0-9a-f-]{36}"))) throw Failure{L"SETTINGS", ERROR_INVALID_DATA};
    return L"Software\\TOLF\\VPN\\" + id;
}
inline std::wstring SavedNetworks(const std::wstring& id) {
    wchar_t text[4097] = {}; DWORD bytes = sizeof(text);
    auto error = RegGetValueW(HKEY_CURRENT_USER, RoutesKey(id).c_str(), L"ExcludedIPv4",
        RRF_RT_REG_SZ, nullptr, text, &bytes);
    if (error == ERROR_FILE_NOT_FOUND || error == ERROR_PATH_NOT_FOUND) return L"";
    if (error) throw Failure{L"ROUTE_SETTINGS", DWORD(error)};
    return text;
}
inline void SaveNetworks(const std::wstring& id, const std::wstring& value) {
    HKEY key = nullptr;
    auto error = RegCreateKeyExW(HKEY_CURRENT_USER, RoutesKey(id).c_str(), 0, nullptr, 0,
        KEY_SET_VALUE, nullptr, &key, nullptr);
    if (error) throw Failure{L"ROUTE_SETTINGS", DWORD(error)};
    error = RegSetValueExW(key, L"ExcludedIPv4", 0, REG_SZ,
        reinterpret_cast<const BYTE*>(value.c_str()), DWORD((value.size() + 1) * sizeof(wchar_t)));
    RegCloseKey(key);
    if (error) throw Failure{L"ROUTE_SETTINGS", DWORD(error)};
}
inline std::vector<Network4> CheckedNetworks(const std::wstring& text) {
    try { auto result = ParseNetworks(text); TunnelPrefixes(result); return result; }
    catch (const std::invalid_argument&) { throw Failure{L"NETWORK_LIST", ERROR_INVALID_DATA}; }
}

// Change only IPv4 default routing; retain the profile's independent IPv6 options.
inline std::vector<BYTE> RouteEntry(const std::wstring& pb,const std::wstring& name) {
    DWORD size=sizeof(RASENTRYW);std::vector<BYTE> buffer(size);
    auto entry=reinterpret_cast<RASENTRYW*>(buffer.data());entry->dwSize=sizeof(RASENTRYW);
    DWORD error=RasGetEntryPropertiesW(pb.c_str(),name.c_str(),entry,&size,nullptr,nullptr);
    if(error==ERROR_BUFFER_TOO_SMALL){buffer.resize(size);entry=reinterpret_cast<RASENTRYW*>(buffer.data());entry->dwSize=sizeof(RASENTRYW);error=RasGetEntryPropertiesW(pb.c_str(),name.c_str(),entry,&size,nullptr,nullptr);}
    if(error)throw Failure{L"VPN_CONFIGURATION",error};
    return buffer;
}
inline void SplitIPv4(const std::wstring& pb,const std::wstring& name,bool split) {
    auto buffer=RouteEntry(pb,name);auto entry=reinterpret_cast<RASENTRYW*>(buffer.data());
    if(split)entry->dwfOptions &= ~RASEO_RemoteDefaultGateway;
    else entry->dwfOptions |= RASEO_RemoteDefaultGateway;
    DWORD error=RasSetEntryPropertiesW(pb.c_str(),name.c_str(),entry,DWORD(buffer.size()),nullptr,0);
    if(error)throw Failure{L"VPN_CONFIGURATION",error};
}

// Configure only a disconnected profile. Windows owns route activation/deactivation;
// no physical-interface routes or global defaults are written by this installer.
inline void ConfigureRoutes(Wmi& w, const Settings& c, const std::wstring& name,
                            const std::vector<Network4>& excluded, int failAfter = -1, bool routesOnly = false) {
    auto pb = Phonebook();
    if (Connected(pb, name, true)) throw Failure{L"DISCONNECT_FIRST", ERROR_BUSY};
    bool existed = Existing(pb, name, c);
    if (routesOnly && !existed) throw Failure{L"VPN_CONFIGURATION", ERROR_CANNOT_FIND_PHONEBOOK_ENTRY};
    auto previous = existed ? CheckedNetworks(SavedNetworks(c.id)) : std::vector<Network4>{};
    auto oldRoutes = TunnelPrefixes(previous), newRoutes = TunnelPrefixes(excluded);
    std::vector<std::wstring> removed, added;
    // Refuse changing unmanaged split-tunnel profiles: their existing routing is unknown.
    if (existed) {
        auto buffer=RouteEntry(pb,name);auto entry=reinterpret_cast<RASENTRYW*>(buffer.data());
        bool full=(entry->dwfOptions & RASEO_RemoteDefaultGateway)!=0;
        if(full != previous.empty())throw Failure{L"ROUTE_CONFLICT",ERROR_INVALID_DATA};
    }
    bool configured=false, splitAttempted=false;
    auto checkpoint=[&] { if(failAfter==0)throw Failure{L"TEST_ROUTE_ROLLBACK",1};if(failAfter>0)--failAfter; };
    try {
        if (!routesOnly) Configure(w,c,name);
        configured=true;
        for(const auto& route:oldRoutes) if(std::find(newRoutes.begin(),newRoutes.end(),route)==newRoutes.end()) {
            w.route(name,route,false);removed.push_back(route);checkpoint();
        }
        for(const auto& route:newRoutes) if(std::find(oldRoutes.begin(),oldRoutes.end(),route)==oldRoutes.end()) {
            w.route(name,route,true);added.push_back(route);checkpoint();
        }
        splitAttempted=true;SplitIPv4(pb,name,!excluded.empty());checkpoint();
        SaveNetworks(c.id,NetworkText(excluded));
    } catch (...) {
        auto original=std::current_exception();bool restored=true;
        if(!existed && configured) {
            if(RasDeleteEntryW(pb.c_str(),name.c_str()))restored=false;
        } else if(existed && configured) {
            for(auto i=added.rbegin();i!=added.rend();++i)try{w.route(name,*i,false);}catch(...){restored=false;}
            for(const auto& route:removed)try{w.route(name,route,true);}catch(...){restored=false;}
            if(splitAttempted)try{SplitIPv4(pb,name,!previous.empty());}catch(...){restored=false;}
        }
        if(!restored)throw Failure{L"ROUTE_ROLLBACK",ERROR_GEN_FAILURE};
        std::rethrow_exception(original);
    }
}

