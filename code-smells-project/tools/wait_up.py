import sys, time, urllib.request
url, timeout = sys.argv[1], float(sys.argv[2] if len(sys.argv) > 2 else 30)
deadline = time.time() + timeout
while time.time() < deadline:
    try:
        urllib.request.urlopen(url, timeout=2); print("UP"); sys.exit(0)
    except Exception:
        time.sleep(0.4)
print("DOWN"); sys.exit(1)
