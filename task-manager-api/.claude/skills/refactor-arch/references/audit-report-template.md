# Template do relatório de auditoria (Fase 2)

O relatório é impresso no terminal e, quando o usuário pedir, salvo em
`reports/audit-<projeto>.md` — **sempre depois da confirmação**, nunca antes.

## Regras de preenchimento

- **Ordem obrigatória**: CRITICAL → HIGH → MEDIUM → LOW. Dentro da mesma severidade, ordene por
  arquivo e depois por linha.
- **Numeração contínua** dos achados (`#1`, `#2`, ...), sem reiniciar a cada severidade.
- **`File:` sempre com linha ou intervalo exato** (`models.py:109-111`). Quando o mesmo padrão
  aparece muitas vezes no mesmo arquivo, use o intervalo e liste as ocorrências no `Description`
  (`ocorrências: 28, 68, 92, 174`).
- **`Evidence:`** é o trecho literal do código, em bloco, no máximo 3 linhas. É o que impede
  achado inventado. Só três marcas podem alterar o texto original, e todas têm de ficar visíveis:
  `...` para elidir o meio de uma linha longa ou de um bloco; um comentário ao final da linha
  (`# ...` / `// ...`) para anotar qual responsabilidade ela representa; e `<redacted>` no lugar de
  um segredo — credencial real **nunca** é copiada para o relatório. Fora essas marcas, cada linha
  é literal e tem de existir em um dos arquivos citados em `File:`.
- **`Description`** diz *o que* está errado; **`Impact`** diz *o que quebra na prática* (seja
  concreto: "um `POST /login` com `' OR '1'='1` autentica como admin"); **`Recommendation`** diz
  *qual transformação aplicar*, citando o padrão do playbook (`R2`).
- Escreva em português. Nomes canônicos de anti-pattern ficam em inglês (`SQL Injection`,
  `God Class`) porque são termos técnicos consagrados.
- Números do sumário têm de bater com a contagem real dos achados listados.

## Formato

```markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <nome do diretório>
Stack:   <linguagem> + <framework versão>
Files:   <N> analyzed | ~<M> lines of code
Date:    <YYYY-MM-DD>

## Summary

CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

| Severidade | Qtd | Principais ocorrências |
|---|---|---|
| CRITICAL | <n> | <anti-patterns, separados por vírgula> |
| HIGH | <n> | <...> |
| MEDIUM | <n> | <...> |
| LOW | <n> | <...> |

## Findings

### #1 [CRITICAL] <Nome canônico do anti-pattern>

- **File:** `<arquivo>:<linha ou intervalo>`
- **Evidence:**
  ```<linguagem>
  <trecho literal do código>
  ```
- **Description:** <o que está errado, em 1–3 frases>
- **Impact:** <consequência concreta: exploração, bug, custo de manutenção>
- **Recommendation:** <transformação a aplicar> (playbook: `<Rn>`)

### #2 [CRITICAL] <...>

...

## Deprecated APIs

| API | Arquivo:linha | Situação | Substituto |
|---|---|---|---|
| `datetime.utcnow()` | `models/task.py:15` | Deprecated no Python 3.12+ | `datetime.now(timezone.utc)` |

_(omita a seção inteira se o projeto não usa nenhuma API deprecated — e diga isso em uma linha)_

## Endpoints inventariados (contrato da Fase 3)

| # | Método | Rota | Status esperado |
|---|---|---|---|
| 1 | GET | `/produtos` | 200 |

## Plano de refatoração proposto

1. <passo — qual camada, quais achados resolve>
2. <...>

================================
Total: <N> findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

## Exemplo preenchido (um achado)

```markdown
### #7 [CRITICAL] SQL Injection

- **File:** `models.py:109-111`
- **Evidence:**
  ```python
  cursor.execute(
      "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
  )
  ```
- **Description:** A query de login é montada concatenando diretamente `email` e `senha`
  recebidos do corpo da requisição, sem parametrização.
- **Impact:** `POST /login` com `{"email": "admin@loja.com'--", "senha": "x"}` autentica como
  administrador sem conhecer a senha. A mesma técnica permite ler e apagar qualquer tabela.
- **Recommendation:** Trocar por query parametrizada com placeholders `?` e mover a verificação
  de credencial para o model de usuário com hash seguro (playbook: `R2`, `R4`).
```

## Relatório de projeto sem achados

Se a auditoria não encontrar nada relevante (raro em código legado), diga isso explicitamente,
liste o que foi verificado (as seis famílias do catálogo) e **não** invente achados de baixa
relevância para preencher o relatório.
