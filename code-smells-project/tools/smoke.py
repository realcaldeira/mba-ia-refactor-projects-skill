"""Harness genérico de smoke test HTTP. Uso: python smoke.py <spec.json> <out.json>"""
import json, sys, urllib.request, urllib.error, re

def run(spec_path, out_path):
    spec = json.load(open(spec_path))
    base = spec["base_url"]
    ctx = {}
    results = []
    for step in spec["steps"]:
        url = base + re.sub(r"\{(\w+)\}", lambda m: str(ctx.get(m.group(1), m.group(1))), step["path"])
        body = step.get("body")
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=step.get("method", "GET"))
        if data:
            req.add_header("Content-Type", "application/json")
        entry = {"name": step["name"], "method": req.get_method(), "path": step["path"]}
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                raw = r.read().decode("utf-8", "replace")
                entry["status"] = r.status
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            entry["status"] = e.code
        except Exception as e:
            entry["status"] = None
            entry["error"] = str(e)
            raw = ""
        try:
            parsed = json.loads(raw)
            entry["json"] = parsed
        except Exception:
            entry["text"] = raw[:500]
            parsed = None
        if "capture" in step and parsed is not None:
            for var, path in step["capture"].items():
                cur = parsed
                for part in path.split("."):
                    if cur is None: break
                    cur = cur[int(part)] if isinstance(cur, list) else cur.get(part)
                ctx[var] = cur
        results.append(entry)
    json.dump({"context": ctx, "results": results}, open(out_path, "w"), indent=2, ensure_ascii=False, default=str)
    ok = sum(1 for r in results if r.get("status") is not None)
    print(f"{ok}/{len(results)} requisições responderam")
    for r in results:
        print(f"  {r['status']!s:>5}  {r['method']:<6} {r['path']}")

if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
