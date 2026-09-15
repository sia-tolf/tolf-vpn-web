#pragma once
#include <algorithm>
#include <cstdint>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

// IPv4 intervals use 64 bits so the exclusive end 2^32 is representable.
struct Network4 {
    uint64_t first, end;
    bool operator==(const Network4& b) const { return first == b.first && end == b.end; }
};
inline std::wstring Prefix4(uint64_t address, unsigned bits) {
    return std::to_wstring((address >> 24) & 255) + L"." +
        std::to_wstring((address >> 16) & 255) + L"." +
        std::to_wstring((address >> 8) & 255) + L"." +
        std::to_wstring(address & 255) + L"/" + std::to_wstring(bits);
}
inline std::vector<Network4> ParseNetworks(const std::wstring& text) {
    if (text.size() > 4096) throw std::invalid_argument("networks");
    std::wstring input = text;
    for (auto& c : input) if (c == L',' || c == L';') c = L' ';
    std::wistringstream stream(input); std::wstring token;
    std::vector<Network4> result;
    while (stream >> token) {
        if (result.size() >= 32) throw std::invalid_argument("networks");
        size_t pos = 0;
        auto number = [&](unsigned limit) {
            size_t begin = pos; unsigned value = 0;
            while (pos < token.size() && token[pos] >= L'0' && token[pos] <= L'9') {
                value = value * 10 + unsigned(token[pos++] - L'0');
                if (value > limit) throw std::invalid_argument("networks");
            }
            if (pos == begin || pos - begin > 3 || (pos - begin > 1 && token[begin] == L'0'))
                throw std::invalid_argument("networks");
            return value;
        };
        uint64_t address = 0;
        for (int i = 0; i < 4; ++i) {
            address = (address << 8) | number(255);
            if (i != 3 && (pos == token.size() || token[pos++] != L'.'))
                throw std::invalid_argument("networks");
        }
        if (pos == token.size() || token[pos++] != L'/') throw std::invalid_argument("networks");
        unsigned bits = number(32);
        if (pos != token.size() || bits == 0) throw std::invalid_argument("networks");
        uint64_t size = uint64_t(1) << (32 - bits);
        if (address % size) throw std::invalid_argument("network address required");
        result.push_back({address, address + size});
    }
    std::sort(result.begin(), result.end(), [](auto a, auto b) { return a.first < b.first; });
    std::vector<Network4> merged;
    for (auto n : result) {
        if (!merged.empty() && n.first <= merged.back().end) merged.back().end = std::max(n.end, merged.back().end);
        else merged.push_back(n);
    }
    if (merged.size() == 1 && merged[0].first == 0 && merged[0].end == (uint64_t(1) << 32))
        throw std::invalid_argument("cannot exclude all IPv4");
    return merged;
}
inline void RangePrefixes(uint64_t first, uint64_t end, std::vector<std::wstring>& out) {
    while (first < end) {
        unsigned host = 0;
        while (host < 32 && first % (uint64_t(1) << (host + 1)) == 0 &&
               (uint64_t(1) << (host + 1)) <= end - first) ++host;
        out.push_back(Prefix4(first, 32 - host));
        first += uint64_t(1) << host;
    }
}
inline std::wstring NetworkText(const std::vector<Network4>& nets) {
    std::vector<std::wstring> prefixes;
    for (auto n : nets) RangePrefixes(n.first, n.end, prefixes);
    std::wstring out;
    for (const auto& p : prefixes) { if (!out.empty()) out += L"\r\n"; out += p; }
    return out;
}
inline std::vector<std::wstring> TunnelPrefixes(const std::vector<Network4>& excluded) {
    if (excluded.empty()) return {}; // Original Windows full-tunnel profile.
    std::vector<std::wstring> result;
    uint64_t cursor = 0;
    for (auto n : excluded) { RangePrefixes(cursor, n.first, result); cursor = n.end; }
    RangePrefixes(cursor, uint64_t(1) << 32, result);
    if (result.size() > 512) throw std::invalid_argument("too many routes");
    return result;
}

