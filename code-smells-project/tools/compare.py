import json, sys
antes = {r['name']: r for r in json.load(open(sys.argv[1]))['results']}
depois = {r['name']: r for r in json.load(open(sys.argv[2]))['results']}
falhas = []
for nome, a in antes.items():
    d = depois.get(nome)
    if d is None:
        falhas.append(f'{nome}: ausente depois')
    elif a['status'] != d['status']:
        falhas.append(f"{nome}: {a['status']} -> {d['status']}")
print(f'{len(antes)} endpoints comparados')
print('PARIDADE OK' if not falhas else 'DIVERGENCIAS:\n  ' + '\n  '.join(falhas))
sys.exit(1 if falhas else 0)
