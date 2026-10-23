"""Apply protocol-qualified iOS labels without changing VPN identities or settings."""
from pathlib import Path

OLD = '''        display_name = (
            (profile_options.get("profileName") or "").strip()
            or f"TOLF {city}{' ' + local_id if local_id else ''}"
        )'''
PREVIOUS = r'''        default_name = f"TOLF {city} IKEv2{' ' + local_id if local_id else ''}"
        requested_name = (profile_options.get("profileName") or "").strip()
        legacy_names = {f"TOLF {city}", f"TOLF {city}{' ' + local_id if local_id else ''}"}
        display_name = default_name if not requested_name or requested_name in legacy_names else requested_name
        if not re.search(r"\bIKEv2\b", display_name, re.IGNORECASE):
            display_name += " IKEv2"'''
NEW = r'''        route_name = (local_id or "auto").upper()
        default_name = f"TOLF {city} IKEv2 {route_name}"
        requested_name = (profile_options.get("profileName") or "").strip()
        legacy_names = {f"TOLF {city}", f"TOLF {city}{' ' + local_id if local_id else ''}"}
        display_name = default_name if not requested_name or requested_name in legacy_names else requested_name
        display_name = re.sub(r"\s+(?:AUTO|SR|LV|RU|YT)$", "", display_name, flags=re.IGNORECASE)
        if not re.search(r"\bIKEv2\b", display_name, re.IGNORECASE):
            display_name += " IKEv2"
        display_name += " " + route_name'''

def transform(source):
    if OLD not in source and PREVIOUS not in source and NEW not in source:
        raise ValueError("Unexpected IKEv2 profile-name block")
    source = source.replace(OLD, NEW).replace(PREVIOUS, NEW)
    source = source.replace('"Download Mobile Config": "Скачать Mobile Config"', '"Install profile": "Установить профиль"')
    source = source.replace('"Download Mobile Config": "Lejupielādēt Mobile Config"', '"Install profile": "Instalēt profilu"')
    source = source.replace('else "Download Mobile Config"', 'else "Install profile"')
    return source

if __name__ == "__main__":
    import sys
    path = Path(sys.argv[1])
    updated = transform(path.read_text())
    compile(updated, str(path), "exec")
    path.write_text(updated)
