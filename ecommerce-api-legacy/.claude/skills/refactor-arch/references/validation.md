# Protocolo de validação (Fase 3)

Uma refatoração só está concluída quando é possível **provar** que a aplicação continua se
comportando como antes. "Parece certo" não é validação.

## Passo 0 — Baseline (antes de tocar em qualquer arquivo)

Ainda dentro da Fase 3, antes da primeira edição:

1. Instale as dependências em ambiente isolado (`python -m venv .venv && .venv/bin/pip install -r
   requirements.txt`, `npm install`).
2. Suba a aplicação original em uma porta livre.
3. Chame **todos** os endpoints do inventário da Fase 1, incluindo os casos de erro
   (404, 400, 401, 409), e grave status + corpo.
4. Derrube o servidor.

Se a aplicação original não sobe, registre isso no relatório e valide a refatoração por
boot + import estático; nesse caso, diga explicitamente no resumo que não houve comparação de
respostas.

## Harness de comparação (agnóstico de stack)

Descreva os endpoints em um JSON e rode o mesmo arquivo antes e depois. `{var}` no caminho é
substituído por um valor capturado de uma resposta anterior (para IDs criados em tempo de execução).

```json
{
  "base_url": "http://127.0.0.1:5001",
  "steps": [
    {"name": "listar", "path": "/produtos"},
    {"name": "criar",  "method": "POST", "path": "/produtos",
     "body": {"nome": "Teste", "preco": 10.5, "estoque": 7, "categoria": "geral"},
     "capture": {"pid": "dados.id"}},
    {"name": "detalhe", "path": "/produtos/{pid}"},
    {"name": "remover", "method": "DELETE", "path": "/produtos/{pid}"},
    {"name": "remover_404", "method": "DELETE", "path": "/produtos/{pid}"}
  ]
}
```

```python
# tools/smoke.py — sem dependências externas, roda com a stdlib
import json, sys, urllib.request, urllib.error, re

def run(spec_path, out_path):
    spec = json.load(open(spec_path)); base = spec["base_url"]; ctx = {}; results = []
    for step in spec["steps"]:
        url = base + re.sub(r"\{(\w+)\}", lambda m: str(ctx.get(m.group(1), m.group(1))), step["path"])
        data = json.dumps(step["body"]).encode() if step.get("body") is not None else None
        req = urllib.request.Request(url, data=data, method=step.get("method", "GET"))
        if data: req.add_header("Content-Type", "application/json")
        entry = {"name": step["name"], "method": req.get_method(), "path": step["path"]}
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                raw, entry["status"] = r.read().decode("utf-8", "replace"), r.status
        except urllib.error.HTTPError as e:
            raw, entry["status"] = e.read().decode("utf-8", "replace"), e.code
        except Exception as e:
            raw, entry["status"], entry["error"] = "", None, str(e)
        try:
            parsed = json.loads(raw); entry["json"] = parsed
        except Exception:
            parsed = None; entry["text"] = raw[:500]
        for var, path in step.get("capture", {}).items():
            cur = parsed
            for part in path.split("."):
                if cur is None: break
                cur = cur[int(part)] if isinstance(cur, list) else cur.get(part)
            ctx[var] = cur
        results.append(entry)
    json.dump({"context": ctx, "results": results}, open(out_path, "w"), indent=2, ensure_ascii=False, default=str)
    print(f"{sum(1 for r in results if r.get('status') is not None)}/{len(results)} responderam")

if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
```

Espere o servidor ficar pronto antes de disparar (poll no endpoint mais barato) — um `sleep` fixo
produz falso negativo:

```python
# tools/wait_up.py
import sys, time, urllib.request
url, deadline = sys.argv[1], time.time() + float(sys.argv[2] if len(sys.argv) > 2 else 30)
while time.time() < deadline:
    try: urllib.request.urlopen(url, timeout=2); print("UP"); sys.exit(0)
    except Exception: time.sleep(0.4)
print("DOWN"); sys.exit(1)
```

## Passo 1 — Boot

```bash
<comando de start> &          # em porta livre
python tools/wait_up.py http://127.0.0.1:<porta>/<rota mais barata> 40
```

Falha aqui = refatoração incompleta. Leia o traceback, corrija, repita. Não avance com o servidor
caindo.

## Passo 2 — Paridade de endpoints

Rode o mesmo spec contra a versão refatorada e compare:

```python
# tools/compare.py
import json, sys
antes  = {r["name"]: r for r in json.load(open(sys.argv[1]))["results"]}
depois = {r["name"]: r for r in json.load(open(sys.argv[2]))["results"]}
falhas = []
for nome, a in antes.items():
    d = depois.get(nome)
    if d is None:                      falhas.append(f"{nome}: ausente depois")
    elif a["status"] != d["status"]:   falhas.append(f"{nome}: {a['status']} → {d['status']}")
print("PARIDADE OK" if not falhas else "DIVERGÊNCIAS:\n" + "\n".join(falhas))
sys.exit(1 if falhas else 0)
```

Critério: **todo endpoint responde com o mesmo status**. Divergência de status é falha, salvo se
for uma mudança de contrato aprovada (endpoint perigoso removido, autenticação adicionada) — e
então ela aparece nomeada no resumo, não escondida.

Diferença de corpo merece inspeção manual: campo sensível que sumiu (senha fora do payload) é
melhoria esperada; campo de negócio que sumiu é regressão.

## Passo 3 — Varredura de regressão de anti-patterns

```bash
grep -rn "execute(\|query(" src/controllers src/views     # SQL fora do model
grep -rniE "(secret|password|api_key)\s*[:=]\s*['\"]" src/ | grep -v config
grep -rn "global \|check_same_thread" src/
grep -rnE "\+ *str\(|f\"SELECT|\" *\+ *[a-z_]+ *\+" src/  # concatenação em SQL
```

Nenhum CRITICAL/HIGH pode sobreviver, e nenhum novo pode ter sido introduzido.

## Passo 4 — Testes do projeto

Se existir suíte (`pytest`, `npm test`, `go test`), rode. Testes que já falhavam antes continuam
falhando (registre); testes que passavam e passaram a falhar são regressão e bloqueiam a entrega.

## Passo 5 — Relatar

Só marque `✓` no que você realmente executou e viu passar. O que falhou vira `✗` com a explicação.
Reportar sucesso não verificado é o pior resultado possível desta skill — pior que a refatoração
não ter sido feita.

```
Validation
  ✓ Application boots without errors        (python src/app.py → UP em 1.2s)
  ✓ 30/30 endpoints respond with baseline parity
  ✓ Zero CRITICAL/HIGH anti-patterns remaining  (varredura do catálogo)
  ✗ Suíte de testes: projeto não possui testes automatizados
```
