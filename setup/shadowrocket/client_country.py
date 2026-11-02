"""Optional country hint from the existing RIPE registry; never changes routing."""
from bisect import bisect_right
from ipaddress import ip_address, ip_network
from pathlib import Path
from threading import Lock

from fastapi import Request
from fastapi.responses import JSONResponse


REGISTRY_FILE = Path('/var/lib/tolf-api/delegated-ripencc-latest')
COUNTRIES = ('RU', 'LV')
HEADERS = {'Cache-Control': 'private, no-store, max-age=0'}


def merge_ranges(values):
    merged = []
    for start, end in sorted(values):
        if merged and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return tuple(row[0] for row in merged), tuple(row[1] for row in merged)


class CountryRanges:
    def __init__(self, path=REGISTRY_FILE):
        self.path = Path(path)
        self.lock = Lock()
        self.stamp = None
        self.ranges = None

    def read(self):
        values = {(country, family): [] for country in COUNTRIES for family in (4, 6)}
        with self.path.open(encoding='ascii') as stream:
            for line in stream:
                fields = line.rstrip('\n').split('|')
                if len(fields) < 7:
                    continue
                registry, country, kind, address, size, _, status = fields[:7]
                if registry != 'ripencc' or country not in COUNTRIES or status.lower() not in ('allocated', 'assigned', 'legacy'):
                    continue
                try:
                    if kind == 'ipv4':
                        start = int(ip_address(address))
                        count = int(size)
                        if ':' in address or count <= 0 or start + count > 1 << 32:
                            continue
                        values[(country, 4)].append((start, start + count - 1))
                    elif kind == 'ipv6':
                        network = ip_network(address + '/' + size, strict=False)
                        if network.version == 6:
                            values[(country, 6)].append((int(network.network_address), int(network.broadcast_address)))
                except ValueError:
                    continue
        if not any(values.values()):
            raise ValueError('No supported country allocations')
        return {key: merge_ranges(rows) for key, rows in values.items()}

    def country_code(self, value):
        try:
            address = ip_address(value)
            if not address.is_global:
                return None
            stat = self.path.stat()
            stamp = (stat.st_mtime_ns, stat.st_size, stat.st_ino)
            with self.lock:
                if stamp != self.stamp:
                    ranges = self.read()
                    self.ranges, self.stamp = ranges, stamp
                ranges = self.ranges
        except (OSError, ValueError, TypeError, UnicodeError):
            return None
        number = int(address)
        for country in COUNTRIES:
            starts, ends = ranges[(country, address.version)]
            index = bisect_right(starts, number) - 1
            if index >= 0 and number <= ends[index]:
                return country
        return None


def register(app, registry=None):
    registry = registry if registry is not None else CountryRanges()

    @app.get('/client-country')
    def client_country(request: Request):
        # Uvicorn already receives the client address from the trusted local
        # reverse proxy. Do not accept country claims or parse proxy headers here.
        country = registry.country_code(request.client.host if request.client else None)
        return JSONResponse({'countryCode': country}, headers=HEADERS)
