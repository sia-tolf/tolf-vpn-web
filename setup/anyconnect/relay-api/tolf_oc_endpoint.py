"""Select the New York relay only for Russian source IPs after activation."""
import json
from pathlib import Path
import tolf_location

CONFIG = Path("/var/lib/tolf-api/ny-moscow-relay.json")
DIRECT = "oc-us.tolf.is:4443"
RELAY = "oc-us-moscow.tolf.is:4443"

def request_catalog(catalog, request):
    result = {key: dict(value) for key, value in catalog.items()}
    if "us" not in result:
        return result
    # Unknown IP/country retains direct access; never trust client country headers.
    try:
        active = json.loads(CONFIG.read_text()).get("enabled") is True
    except (OSError, ValueError, AttributeError):
        active = False
    host = getattr(getattr(request, "client", None), "host", None)
    if active and tolf_location.recommendation(host) == "moscow":
        result["us"]["host"] = RELAY
        result["us"]["via"] = "moscow"
    return result
