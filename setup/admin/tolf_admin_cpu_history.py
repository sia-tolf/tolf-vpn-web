"""CPU history collected on London from read-only VPN node counters."""
import fcntl
import json
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

STORE = Path("/var/lib/tolf-api/admin-cpu-history.json")
LOCK = Path("/var/lib/tolf-api/admin-cpu-history.lock")
NODES = ("riga", "moscow")


def read_history():
    if not STORE.exists():
        return {node: [] for node in NODES}
    data = json.loads(STORE.read_text())
    if not isinstance(data, dict):
        raise ValueError("Invalid CPU history")
    return {node: data.get(node, []) for node in NODES}


def record(readings):
    now = time.time()
    with LOCK.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = read_history()
        for node, reading in zip(NODES, readings):
            if reading.get("status") != "ok":
                continue
            at = datetime.fromisoformat(reading["observedAt"]).timestamp()
            if abs(now - at) > 120:
                continue
            total = reading["cpuTotalTicks"]
            idle = reading["cpuIdleTicks"]
            samples = [s for s in data[node] if now - s["at"] <= 1200]
            if samples and (total < samples[-1]["total"] or idle < samples[-1]["idle"]):
                samples = []  # The node restarted; begin a new interval.
            if not samples or at > samples[-1]["at"]:
                samples.append({"at": at, "total": total, "idle": idle})
            data[node] = samples

        fd, name = tempfile.mkstemp(prefix=".admin-cpu-", dir=STORE.parent)
        try:
            with os.fdopen(fd, "w") as output:
                json.dump(data, output, separators=(",", ":"))
                output.flush()
                os.fsync(output.fileno())
            os.replace(name, STORE)
        finally:
            if os.path.exists(name):
                os.unlink(name)
    return {node: len(data[node]) for node in NODES}


def average(node):
    """Return percent over approximately 15 minutes, or None while collecting."""
    try:
        samples = read_history()[node]
        latest = samples[-1]
        if abs(time.time() - latest["at"]) > 120:
            return None
        target = latest["at"] - 900
        first = min(samples, key=lambda s: abs(s["at"] - target))
        seconds = latest["at"] - first["at"]
        total = latest["total"] - first["total"]
        idle = latest["idle"] - first["idle"]
        if not 870 <= seconds <= 960 or total <= 0 or not 0 <= idle <= total:
            return None
        return round(100 * (total - idle) / total)
    except (OSError, ValueError, KeyError, IndexError, TypeError, ZeroDivisionError):
        return None


def collect():
    import tolf_admin
    import tolf_nodes
    tolf_admin.CTX = {
        "RIGA_HOST": tolf_nodes.RIGA_PUBLIC_HOST,
        "RIGA_USER": "tolfprov",
        "RIGA_KEY": "/opt/tolf-api/provision_ed25519",
        "RIGA_KNOWN_HOSTS": "/opt/tolf-api/.ssh/known_hosts",
    }
    with ThreadPoolExecutor(max_workers=2) as pool:
        readings = list(pool.map(tolf_admin.query_metrics, NODES))
    print(json.dumps({"status": [r["status"] for r in readings],
                      "samples": record(readings)}))


if __name__ == "__main__":
    collect()
