#include "../../setup/windows/native/networks.h"
#include <cassert>
#include <iostream>
static void partition(const std::wstring& input){
 auto excluded=ParseNetworks(input);auto routes=TunnelPrefixes(excluded);
 if(excluded.empty()){assert(routes.empty());return;}
 std::vector<Network4> all=excluded;
 for(const auto& prefix:routes){auto network=ParseNetworks(prefix);assert(network.size()==1);all.push_back(network[0]);}
 std::sort(all.begin(),all.end(),[](auto a,auto b){return a.first<b.first;});
 uint64_t cursor=0;for(auto n:all){assert(n.first==cursor);assert(n.end>n.first);cursor=n.end;}assert(cursor==(uint64_t(1)<<32));
 assert(ParseNetworks(NetworkText(excluded))==excluded);
}
inline void NetworkTests(){
 for(auto s:{L"",L" \r\n",L"192.168.200.0/24",L"0.0.0.0/32",L"255.255.255.255/32",L"0.0.0.0/1",L"128.0.0.0/1",L"10.0.0.0/8;192.168.200.0/24,172.16.0.0/12",L"10.0.0.0/8\r\n10.1.0.0/16\n10.0.0.0/8",L"10.0.0.0/9 10.128.0.0/9"})partition(s);
 for(auto s:{L"192.168.200",L"192.168.200.1/24",L"192.168.200.0/33",L"0.0.0.0/0",L"256.0.0.0/8",L"10.00.0.0/8",L"10.0.0.0/08",L"10.0.0.0/8/x",L"::/0",L"192.168.0.0/-1",L"0.0.0.0/1 128.0.0.0/1",L"10.0.0.0/99999999999999999999"}){bool bad=false;try{ParseNetworks(s);}catch(const std::invalid_argument&){bad=true;}assert(bad);}
 std::wstring many;for(int i=0;i<33;i++)many+=L"10.0.0.0/8\n";bool bad=false;try{ParseNetworks(many);}catch(const std::invalid_argument&){bad=true;}assert(bad);
 for(unsigned i=0;i<128;i++){uint64_t ip=(uint64_t(i)*2654435761u)&0xffffffffu;partition(Prefix4(ip,32));}
 std::cout<<"PASS IPv4 validation, normalization and complete nonoverlapping route partitions\n";
}
#ifndef TOLF_EMBED_TESTS
int main(){NetworkTests();}
#endif
