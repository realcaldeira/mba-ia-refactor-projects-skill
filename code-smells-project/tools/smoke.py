import hashlib
import json, sys, urllib.request, urllib.error, re, os

def seed_password():
    env = os.getenv('SEED_PASSWORD')
    if env and env.strip():
        return env.strip()
    return hashlib.sha256(b'desafio-skills-local-seed').hexdigest()[:16]

def inject_seed(value, credencial):
    if isinstance(value, dict):
        return {k: inject_seed(v, credencial) for k, v in value.items()}
    if isinstance(value, list):
        return [inject_seed(v, credencial) for v in value]
    if value == '__SEED__':
        return credencial
    if value == '__SEED_WRONG__':
        return credencial + '-invalid'
    if value == '__SEED_SHORT__':
        return 'x'
    return value

def run(spec_path, out_path):
    credencial = seed_password()
    spec = json.load(open(spec_path))
    spec = inject_seed(spec, credencial)
    base = spec['base_url']
    ctx = {}
    results = []
    for step in spec['steps']:
        url = base + re.sub('\\{(\\w+)\\}', lambda m: str(ctx.get(m.group(1), m.group(1))), step['path'])
        body = step.get('body')
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=step.get('method', 'GET'))
        if data:
            req.add_header('Content-Type', 'application/json')
        entry = {'name': step['name'], 'method': req.get_method(), 'path': step['path']}
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                raw = r.read().decode('utf-8', 'replace')
                entry['status'] = r.status
        except urllib.error.HTTPError as e:
            raw = e.read().decode('utf-8', 'replace')
            entry['status'] = e.code
        except Exception as e:
            entry['status'] = None
            entry['error'] = str(e)
            raw = ''
        try:
            parsed = json.loads(raw)
            entry['json'] = parsed
        except Exception:
            entry['text'] = raw[:500]
            parsed = None
        if 'capture' in step and parsed is not None:
            for var, path in step['capture'].items():
                cur = parsed
                for part in path.split('.'):
                    if cur is None:
                        break
                    cur = cur[int(part)] if isinstance(cur, list) else cur.get(part)
                ctx[var] = cur
        results.append(entry)
    json.dump({'context': ctx, 'results': results}, open(out_path, 'w'), indent=2, ensure_ascii=False, default=str)
    ok = sum((1 for r in results if r.get('status') is not None))
    print(f'{ok}/{len(results)} requisições responderam')
    for r in results:
        print(f"  {r['status']!s:>5}  {r['method']:<6} {r['path']}")
if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2])
