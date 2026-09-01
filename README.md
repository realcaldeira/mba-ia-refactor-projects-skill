# Skill de Auditoria e Refatoração Arquitetural — `refactor-arch`

Skill que audita qualquer codebase e a refatora para o padrão MVC em **três fases sequenciais**,
com um portão humano entre a auditoria e a escrita de código.

```
FASE 1 — ANÁLISE       →   FASE 2 — AUDITORIA        →  [y/n]  →  FASE 3 — REFATORAÇÃO
detecta stack,             cruza o código contra                   reestrutura em MVC,
arquitetura e              o catálogo, emite o                     valida boot + paridade
superfície HTTP            relatório de severidades                de endpoints
```

Aplicada aos três projetos legados deste repositório: **84 achados** catalogados, **três
refatorações** para MVC e **79 casos de teste HTTP** com paridade de contrato preservada.

| Projeto | Stack | Achados | Endpoints | Validação |
|---|---|---|---|---|
| [code-smells-project](code-smells-project/) | Python + Flask 3.1.1 | 32 (7 CRITICAL) | 17 preservados, 2 removidos | 30/30 ✓ |
| [ecommerce-api-legacy](ecommerce-api-legacy/) | Node.js + Express 4 | 26 (5 CRITICAL) | 3 preservados | 8/8 ✓ |
| [task-manager-api](task-manager-api/) | Python + Flask-SQLAlchemy | 26 (3 CRITICAL) | 22 preservados | 41/41 ✓ |

---

## A. Análise Manual

Leitura dos três projetos antes de escrever a skill — é o que definiu quais anti-patterns o
catálogo precisava detectar. Relatórios completos em [`reports/`](reports/).

### Projeto 1 — `code-smells-project` (Python/Flask, 780 linhas em 4 arquivos)

| # | Problema | Sev. | Local | Por que importa |
|---|---|---|---|---|
| 1 | **SQL Injection** | CRITICAL | `models.py:28-297` (18 ocorrências) | Todas as queries são concatenação de string com dado do request. `POST /login` com `{"email": "admin@loja.com'--"}` autentica como administrador sem senha. |
| 2 | **Arbitrary SQL Execution** | CRITICAL | `app.py:59-78` | `POST /admin/query` recebe SQL do cliente e executa. Controle total do banco por qualquer um, sem autenticação. Não tem mitigação parcial. |
| 3 | **Hardcoded Secret** | CRITICAL | `app.py:7` | `SECRET_KEY` literal no código versionado; rotacionar exige deploy. |
| 4 | **Sensitive Data Exposure** | CRITICAL | `models.py:83, 99` e `controllers.py:284-289` | `GET /usuarios` devolve a senha de todos os usuários; `GET /health` devolve a `SECRET_KEY`. Dois vazamentos em massa por requisição sem autenticação. |
| 5 | **God Module** | CRITICAL | `models.py:1-314` | Um arquivo com acesso a dados, regra de negócio, serialização e formatação para 4 domínios. Nenhuma regra é testável sem o banco real. |
| 6 | **Global Mutable State** | HIGH | `database.py:4-11` | Conexão única de módulo compartilhada entre requisições com `check_same_thread=False`: corrupção sob concorrência. |
| 7 | **Business Logic in Controller** | HIGH | `controllers.py:24-58, 188-255` | Categorias válidas, limites de nome, status de pedido e notificações dentro do handler HTTP — nada reusável por CLI ou worker. |
| 8 | **N+1 Query** | MEDIUM | `models.py:171-233` | Uma query por pedido e outra por item: 100 pedidos com 3 itens = 401 idas ao banco em `GET /pedidos`. |
| 9 | **Missing Error Handling** | MEDIUM | `controllers.py` (16 ocorrências) | O mesmo `try/except Exception` em todas as funções, devolvendo `str(e)` ao cliente — vaza nome de tabela e acelera a exploração do item 1. |
| 10 | **Duplicated Validation** | MEDIUM | `controllers.py:28-54` × `72-90` | O bloco copiado já divergiu: `PUT /produtos` aceita categoria inválida que `POST /produtos` rejeita. |
| 11 | **Magic Numbers** | LOW | `models.py:256-262` | Faixas de desconto (`10000`, `0.1`) soltas no meio do cálculo — política comercial sem nome. |
| 12 | **print as Logging** | LOW | `controllers.py` (14 ocorrências) | Sem nível, sem timestamp, com e-mail de usuário em stdout. |
| 13 | **Unused Imports / Shadowing** | LOW | `models.py:2, 24`, `database.py:2` | `import sqlite3` e `import os` mortos; parâmetro `id` sombreia a builtin em 9 funções. |

### Projeto 2 — `ecommerce-api-legacy` (Node/Express, 180 linhas em 3 arquivos)

| # | Problema | Sev. | Local | Por que importa |
|---|---|---|---|---|
| 1 | **Hardcoded Credentials** | CRITICAL | `src/utils.js:1-7` | Senha do banco de produção e chave **live** do gateway (`pk_live_...`) versionadas. |
| 2 | **God Class** | CRITICAL | `src/AppManager.js:4-139` | Conexão, DDL, seed, rotas, pagamento e relatório na mesma classe; `setupRoutes` sozinho tem 113 das 141 linhas. |
| 3 | **Sensitive Data in Logs** | CRITICAL | `src/AppManager.js:45` | Número completo do cartão e a chave do gateway em `console.log` a cada checkout — violação direta de PCI-DSS. |
| 4 | **Broken Authentication** | CRITICAL | `src/AppManager.js:40-75` | Se o e-mail já existe, o fluxo assume aquela identidade **sem verificar a senha**: qualquer um compra em nome de outro. |
| 5 | **Fake Payment Authorization** | HIGH | `src/AppManager.js:46` | `cc.startsWith("4")` decide se o pagamento foi aprovado. Matrícula paga sem cobrança real. |
| 6 | **Broken Cryptography** | HIGH | `src/utils.js:17-23` | `badCrypto` repete 10.000× o base64 da senha e trunca em 10 caracteres; ainda bloqueia o event loop. |
| 7 | **Callback Hell + race condition** | HIGH | `src/AppManager.js:83-128` | Cinco níveis de callback com contadores manuais decidindo quando responder: requisição pendurada se um callback falhar, `res.json` duplo em condição de corrida, ordem não determinística. |
| 8 | **Missing Transaction** | HIGH | `src/AppManager.js:50-63` | Três escritas encadeadas sem transação: falha no meio deixa aluno matriculado sem pagamento. |
| 9 | **Error Swallowing** | HIGH | `src/AppManager.js:57, 92, 104, 106, 133` | Cinco callbacks recebem `err` e ignoram — o `DELETE` responde sucesso mesmo falhando. |
| 10 | **N+1 Query** | MEDIUM | `src/AppManager.js:83-127` | Quatro níveis: 50 cursos × 100 matrículas = 10.051 queries em uma requisição. |
| 11 | **Referential Integrity** | MEDIUM | `src/AppManager.js:131-137` | A resposta narra o defeito: *"as matrículas e pagamentos ficaram sujos no banco"*. |
| 12 | **Poor Naming** | LOW | `src/AppManager.js:29-33` | `u`, `e`, `p`, `cid`, `cc` — e `e` significa e-mail num escopo e erro no aninhado. |
| 13 | **Magic Strings / JS legado** | LOW | `src/AppManager.js:21, 26, 46` | `"PAID"`/`"DENIED"` repetidos, `const self = this`, `let` para constantes. |

### Projeto 3 — `task-manager-api` (Python/Flask-SQLAlchemy, 1158 linhas em 15 arquivos)

O projeto "parcialmente organizado": tem `models/`, `routes/`, `services/` e `utils/`, mas a
separação é **nominal**.

| # | Problema | Sev. | Local | Por que importa |
|---|---|---|---|---|
| 1 | **Sensitive Data Exposure** | CRITICAL | `models/user.py:21` | `to_dict()` inclui `password`; devolvido em `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e no `POST /login`. Combinado com MD5 (item 4), o hash exposto é quebrável em segundos. |
| 2 | **Hardcoded Credentials** | CRITICAL | `app.py:13`, `services/notification_service.py:7-10` | `SECRET_KEY` e credenciais completas de SMTP no código — com `python-dotenv` declarado e nunca usado. |
| 3 | **God Route Module** | CRITICAL | `routes/*.py` (733 linhas) | As rotas fazem roteamento, validação, consulta ao ORM e serialização. A camada de controller não existe; a separação de pastas é fachada. |
| 4 | **Weak Password Hashing** | HIGH | `models/user.py:27-32` | MD5 sem salt, com comparação direta de strings. |
| 5 | **Fake Token** | HIGH | `routes/user_routes.py:210` | `'fake-jwt-token-' + str(user.id)`: trocar o número troca de usuário. |
| 6 | **Business Logic in Route** | HIGH | 5 arquivos | `Task.is_overdue()` e `validate_status()` existem no model e **nenhuma rota os chama** — a regra foi reescrita à mão em cada lugar. |
| 7 | **Deprecated APIs** | MEDIUM | 17 + 30 ocorrências | `datetime.utcnow()` (deprecated no Python 3.12, devolve naive) e `Model.query.get()` (legado no SQLAlchemy 2.x, que o projeto declara). |
| 8 | **N+1 Query** | MEDIUM | `routes/task_routes.py:41-57` e outros | `GET /tasks` faz 2 queries por task; `/reports/summary` dispara 14 consultas e carrega toda a tabela em memória. |
| 9 | **Duplicated Code** | MEDIUM | 7 ocorrências em 5 arquivos | O trio de `if` do "atrasada" copiado sete vezes. Foi a duplicação da serialização que produziu o vazamento do item 1 em quatro rotas e não em outra. |
| 10 | **Dead Code** | MEDIUM | `utils/helpers.py`, `services/notification_service.py` | 164 linhas (14% do projeto) que nunca são chamadas — incluindo um segredo hardcoded e o validador que resolveria a duplicação do item 9. |
| 11 | **Silent Exception Swallowing** | MEDIUM | 12 ocorrências | `except:` nus devolvendo "Erro interno" sem log: bug de produção indiagnosticável. |
| 12 | **Magic Numbers** | LOW | 4 arquivos | Faixas de prioridade e limites de título soltos — com as constantes equivalentes existindo, e ignoradas, em `utils/helpers.py:110-116`. |
| 13 | **Boolean Return / Deep Nesting** | LOW | `models/user.py:34-38`, `models/task.py:50-59` | `if cond: return True else: return False` e três níveis de `if` onde duas guard clauses bastam. |

---

## B. Construção da Skill

### Estrutura

```
.claude/skills/refactor-arch/
├── SKILL.md                            orquestrador das 3 fases (o prompt)
└── references/                         o conhecimento de domínio
    ├── project-analysis.md             heurísticas de detecção (Fase 1)
    ├── antipatterns-catalog.md         36 anti-patterns com sinais de detecção (Fase 2)
    ├── audit-report-template.md        formato do relatório (Fase 2)
    ├── mvc-architecture.md             estrutura-alvo e regras de camada (Fase 3)
    ├── refactoring-playbook.md         22 transformações com antes/depois (Fase 3)
    └── validation.md                   protocolo de boot + paridade (Fase 3)
```

O `SKILL.md` é curto e operacional — ele diz **o que fazer e em que ordem**. Todo o conhecimento
de domínio está nos arquivos de referência, carregados sob demanda na fase que precisa deles.

### Decisões de design

**Separar o prompt do conhecimento.** Um `SKILL.md` de 167 linhas que carrega referências
específicas por fase custa menos contexto e é mais fácil de evoluir do que um arquivo monolítico:
ajustar a detecção de um anti-pattern mexe só no catálogo.

**Sinal de detecção acionável em toda entrada do catálogo.** "Código ruim" não ajuda. Cada
anti-pattern traz o comando de busca concreto —
`grep -rnE "(execute|query)\s*\(\s*[\"'].*[\"']\s*\+"` para SQL Injection,
`grep -rnE -B5 "(execute|query)" . | grep -E "for |forEach"` para N+1 — seguido da regra que
separa hit de achado real: **abrir o arquivo e confirmar a linha**. Foi isso que manteve os 84
achados com `arquivo:linha` verificável.

**Escala de severidade fixa e anti-inflação.** A severidade vem do catálogo, não do julgamento
do momento: `Weak Password Hashing` é sempre HIGH, `SQL Injection` é sempre CRITICAL. O SKILL.md
instrui explicitamente a escolher o menor nível na dúvida. Sem isso, tudo vira CRITICAL e a
priorização perde valor.

**O portão humano é regra inviolável nº 1.** As Fases 1 e 2 são estritamente somente-leitura —
nem o relatório é escrito em disco antes do `y`. Auditar é barato e reversível; refatorar não é.

**Paridade de contrato como critério de aceite, não como intenção.** A Fase 1 produz o inventário
de endpoints; a Fase 3 grava o baseline **antes** de editar e compara depois. `references/validation.md`
traz o harness pronto (stdlib pura, sem dependência nova). A única mudança de contrato permitida é
fechar um endpoint indefensável — e ela tem de aparecer nomeada no resumo final.

### Anti-patterns incluídos e por quê

Seis famílias, 36 entradas — cada uma escolhida por aparecer em pelo menos um dos três projetos ou
por ser o modo de falha vizinho do que apareceu:

| Família | Entradas | Motivo |
|---|---|---|
| **A. Segurança** | 8 | Onde estão os CRITICAL reais: SQL Injection, credenciais versionadas, execução arbitrária, vazamento na resposta e no log, hash fraco, ausência de autenticação, defaults inseguros, token previsível. |
| **B. Arquitetura/MVC** | 9 | O alvo da skill: God Class/Method, regra no controller, dado no controller, ausência de config, ausência de composition root, erro não centralizado, estado global, acoplamento sem DI. |
| **C. Dados/performance** | 6 | N+1, agregação em memória, falta de paginação, integridade referencial, callback hell, má gestão de conexão e transação — os três projetos tinham N+1, e dois tinham escrita composta sem transação. |
| **D. APIs deprecated** | 3 | Exigência do desafio e problema real: o projeto 3 tem 17 `datetime.utcnow()` e 30 usos de `Model.query`, com CVEs no projeto 2. Código que funciona hoje e quebra no próximo upgrade. |
| **E. Duplicação** | 4 | A causa raiz de vários CRITICAL: foi a serialização duplicada que expôs a senha em quatro rotas do projeto 3 e não numa quinta. |
| **F. Legibilidade** | 6 | Magic numbers, nomes ruins, retorno booleano, `print`, exceção engolida, aninhamento — os LOW que o relatório precisa cobrir sem inflar. |

### Como a skill ficou agnóstica de tecnologia

1. **Detecção por manifesto, não por convenção.** A Fase 1 lê `requirements.txt`, `package.json`,
   `go.mod`, `composer.json`, `pom.xml` ou `Gemfile` e confirma com os imports reais. Sem manifesto,
   a resposta é `desconhecido` — nunca um palpite.
2. **Sinais de detecção multi-linguagem.** Cada entrada do catálogo traz o padrão nas várias
   sintaxes: `cursor.execute(... + ...)` e `db.query(\`...${x}\`)` são o mesmo anti-pattern.
3. **A arquitetura-alvo é lógica, não sintática.** `references/mvc-architecture.md` define
   responsabilidade e direção de dependência; o que muda entre stacks é a extensão do arquivo.
   O playbook alterna Python e JavaScript de propósito, para deixar claro que o padrão é o mesmo.
4. **Convenção da stack acima da preferência.** A skill instrui a seguir `snake_case` em Python e
   `camelCase` em Node, e a manter o idioma de domínio que o projeto já usa.
5. **Validação por HTTP, não por framework.** O harness fala com a aplicação por requisição —
   funciona igual com Flask e Express, e o `validation.md` prevê o caso de projeto sem entry point
   HTTP (troca a validação por import + suíte de testes).

### Desafios encontrados

**O grep encontra, o grep também engana.** A varredura de regressão acusou "concatenação em SQL"
no projeto 1 e "console.log" no 2 — os dois eram falsos positivos (`Blueprint(` contém `print(`;
a concatenação era numa mensagem de erro). Daí a regra do catálogo: **hit é hipótese, evidência
literal é achado**. Sem isso, o relatório se enche de ruído.

**Corrigir segurança tende a quebrar contrato.** Adicionar autenticação obrigatória mudaria o
status de endpoints hoje públicos. A saída foi construir o token e o middleware, e deixá-los
**opt-in** via `AUTH_REQUIRED=false` (default). Com `true`, as rotas sensíveis passam a exigir
Bearer — decisão de produto, não efeito colateral silencioso da refatoração.

**Nem toda mudança de corpo é regressão.** A comparação de respostas acusou diferenças nos três
projetos. Foi preciso classificá-las: campo sensível que sumiu (`password`, `secret_key`) é o
objetivo; campo de negócio que sumiu seria regressão. No projeto 2, o relatório financeiro
pós-deleção mudou de `revenue: 1994, students: [Unknown, Unknown]` para `revenue: 0, students: []`
— não é regressão, é a integridade referencial funcionando.

**"Parcialmente organizado" é mais difícil que "monolítico".** No projeto 3, a estrutura de pastas
sugeria camadas que não existiam: `Task.is_overdue()` estava escrito e nenhuma rota o chamava.
Refatorar ali foi menos demolir e mais **completar a separação iniciada** — e é onde a Fase 1
ganha valor, ao classificar a arquitetura atual antes de julgá-la.

---

## C. Resultados

### Resumo dos relatórios de auditoria

| | Projeto 1 | Projeto 2 | Projeto 3 | Total |
|---|---|---|---|---|
| CRITICAL | 7 | 5 | 3 | **15** |
| HIGH | 10 | 8 | 8 | **26** |
| MEDIUM | 9 | 7 | 9 | **25** |
| LOW | 6 | 6 | 6 | **18** |
| **Total** | **32** | **26** | **26** | **84** |

### Antes e depois

| | Antes | Depois |
|---|---|---|
| **Projeto 1** | 4 arquivos, 780 linhas, sem camadas | 24 módulos em 7 camadas |
| | 18 queries por concatenação | 0 — todas parametrizadas |
| | senha em texto plano; senha e `SECRET_KEY` na resposta | PBKDF2 com salt; serialização com allowlist |
| | `GET /pedidos` com 401 queries (100 pedidos) | 1 query com `LEFT JOIN` |
| | relatório com 5 varreduras | 1 varredura agregada |
| | 16 blocos `try/except` repetidos | 1 error handler central |
| | conexão global com `check_same_thread=False` | factory injetada pelo composition root |
| **Projeto 2** | 1 God Class de 141 linhas | 20 módulos em 7 camadas |
| | 5 níveis de callback com contador manual | `async/await` + `Promise.all` |
| | relatório com 10.051 queries (50 cursos) | 1 query com `JOIN` |
| | e-mail conhecido = identidade assumida | senha verificada; `401` sem ela |
| | PAN e chave live no log | `**** **** **** 4444` |
| | deleção deixava órfãos (documentado na resposta) | transação removendo dependentes |
| **Projeto 3** | 733 linhas de rota fazendo 4 papéis | camada de controller introduzida |
| | `password` em 4 respostas | 0 |
| | MD5 sem salt | PBKDF2 com salt |
| | `fake-jwt-token-<id>` | HMAC-SHA256 com expiração |
| | 17 `datetime.utcnow()` + 30 `Model.query` | APIs atuais (Python 3.12+, SQLAlchemy 2.x) |
| | regra de "atrasada" em 7 lugares | `Task.is_overdue()` |
| | `/reports/summary` com 14 consultas | 6, com `GROUP BY` |
| | 164 linhas de código morto | 0 |

### Checklist de validação

**Fase 1 — Análise**

- [x] Linguagem detectada corretamente nos 3 projetos
- [x] Framework e versão detectados a partir do manifesto (Flask 3.1.1 / Express 4.22.1 / Flask 3.0.0 + Flask-SQLAlchemy 3.1.1)
- [x] Domínio descrito corretamente (e-commerce / LMS com checkout / task manager)
- [x] Contagem de arquivos conferida (4 / 3 / 15) e de linhas (780 / 180 / 1158)

**Fase 2 — Auditoria**

- [x] Relatório no formato do template em `references/audit-report-template.md`
- [x] Todo achado com arquivo e linha exatos, verificados com `cat -n`
- [x] Achados ordenados CRITICAL → HIGH → MEDIUM → LOW
- [x] Mínimo de 5 achados por projeto (32 / 26 / 26)
- [x] Pelo menos 1 CRITICAL por projeto (7 / 5 / 3)
- [x] Detecção de APIs deprecated executada nos três; produziu achados no projeto 3 e a seção declara explicitamente a ausência nos outros dois
- [x] Skill pausou e pediu confirmação antes de qualquer escrita

**Fase 3 — Refatoração**

- [x] Estrutura de diretórios em MVC nos 3 projetos
- [x] Configuração extraída para módulo de config, sem valor hardcoded, com `.env.example`
- [x] Models abstraem os dados e concentram a regra de domínio
- [x] Views/routes apenas mapeiam rota → controller
- [x] Controllers concentram o fluxo, sem SQL e sem regra pesada
- [x] Error handling centralizado nos 3
- [x] Entry point claro com application factory
- [x] Aplicação inicia sem erros nos 3
- [x] Endpoints originais respondem com o status do baseline (30/30, 8/8, 41/41)

### Recorte das 3 fases

Não há gravação do CLI `claude` neste repositório. O recorte abaixo replica a saída da skill
a partir dos relatórios versionados em [`reports/`](reports/) e da validação de paridade
executada em 2026-09-01.

```
$ cd code-smells-project && claude "/refactor-arch"
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3
Framework:     Flask 3.1.1
Domain:        API de e-commerce (produtos, usuários, pedidos)
Architecture:  Monolítica — tudo em 4 arquivos
Source files:  4 files analyzed (780 lines)
================================

ARCHITECTURE AUDIT REPORT  —  CRITICAL: 7 | HIGH: 10 | MEDIUM: 9 | LOW: 6
Total: 32 findings
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
> y

================================
PHASE 3: REFACTORING COMPLETE
================================
Findings resolved: 31/32  (CRITICAL 7/7 | HIGH 9/10 | MEDIUM 9/9 | LOW 6/6)
Remaining CRITICAL/HIGH: #9 HIGH Missing Authentication — aceito (AUTH_REQUIRED=false)
Validation
  ✓ Application boots without errors
  ✓ 30/30 endpoints respond with baseline parity
================================

$ cd ../ecommerce-api-legacy && claude "/refactor-arch"
PHASE 1  Language: JavaScript (Node.js)  Framework: Express 4.22.1
         Domain: LMS com checkout  Source files: 3 (180 lines)
PHASE 2  CRITICAL: 5 | HIGH: 8 | MEDIUM: 7 | LOW: 6  —  Total: 26
PHASE 3  Findings resolved: 25/26
         Remaining: #5 CRITICAL Missing Authentication — aceito (AUTH_REQUIRED=false)
         ✓ 8/8 endpoints

$ cd ../task-manager-api && claude "/refactor-arch"
PHASE 1  Language: Python 3  Framework: Flask 3.0.0 + Flask-SQLAlchemy 3.1.1
         Domain: Gerenciador de tarefas  Source files: 15 (1158 lines)
PHASE 2  CRITICAL: 3 | HIGH: 8 | MEDIUM: 9 | LOW: 6  —  Total: 26
PHASE 3  Findings resolved: 25/26
         Remaining: #5 HIGH Missing Authentication — aceito (AUTH_REQUIRED=false)
         ✓ 41/41 endpoints
```

### Logs da validação

Gerados pelo harness de paridade descrito em
[`references/validation.md`](code-smells-project/.claude/skills/refactor-arch/references/validation.md),
executado contra as três aplicações antes e depois da refatoração:

```
════════ PROJETO 1: code-smells-project ════════
UP
30/30 requisições responderam

════════ PROJETO 2: ecommerce-api-legacy ════════
UP
8/8 requisições responderam

════════ PROJETO 3: task-manager-api ════════
UP
41/41 requisições responderam
```

Varredura de regressão de anti-patterns após a refatoração (as ocorrências restantes são menções
em docstrings, falsos positivos do grep, ou **aceitação consciente**):

```
SQL fora de models: 0        HTTP dentro de models: 0      senha em serialização: 0
datetime.utcnow() real: 0    Model.query.get() legado: 0
```

Auth nas rotas permanece **desligada por padrão** (`AUTH_REQUIRED=false`) para não quebrar o
contrato HTTP legado. Ligar o middleware é uma linha de configuração, não código novo. Isso
continua sendo um HIGH do catálogo — não afirmamos “zero HIGH restante”.

### Mudanças de contrato deliberadas

Documentadas no relatório do respectivo projeto ou abaixo:

1. **Projeto 1** — `POST /admin/query` e `POST /admin/reset-db` removidos. O primeiro executava SQL
   arbitrário do cliente; o segundo apagava o banco sem autenticação. Ambos respondem `404` agora.
2. **Projeto 2** — o checkout com e-mail já cadastrado passa a exigir a senha correta e responde
   `401` quando ela não confere. Matrícula duplicada no mesmo curso responde `409`.
3. **Projetos 1 e 3** — campos sensíveis saíram do corpo das respostas (`password`, `secret_key`,
   `debug`, `db_path`). Os status permaneceram idênticos.
4. **Projeto 3** — `POST /users` ignora `role` enviado pelo cliente e sempre cria `user` (bloqueia
   auto-promoção a admin). Papel só muda com `AUTH_REQUIRED=true` e token de admin.
5. **Os três** — autenticação obrigatória só com `AUTH_REQUIRED=true`. O default preserva o
   contrato legado (rotas públicas + token emitido no login).

---

## D. Como Executar

### Pré-requisitos

- Python 3.10+ e Node.js 18+
- A skill em `.claude/skills/refactor-arch/` dentro do projeto que será auditado

### Executando a skill

```bash
cd code-smells-project
claude "/refactor-arch"
```

A Fase 1 imprime o retrato do projeto; a Fase 2 emite o relatório e **pausa**:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Responder `n` encerra sem tocar em nenhum arquivo. Responder `y` executa a refatoração e a
validação. O mesmo comando roda nos outros dois projetos — a skill é copiável e não tem nada
específico de um projeto:

```bash
cd ../ecommerce-api-legacy && claude "/refactor-arch"
cd ../task-manager-api    && claude "/refactor-arch"
```

### Rodando as aplicações refatoradas

A porta vem de `PORT` (via `.env`). Os projetos 1 e 3 têm o **mesmo default (5000)** — para subir
os dois ao mesmo tempo, passe `PORT` explicitamente em um deles, como abaixo.

```bash
# Projeto 1 — http://localhost:5000
cd code-smells-project
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env && .venv/bin/python app.py

# Projeto 2 — http://localhost:3000
cd ecommerce-api-legacy
npm install && cp .env.example .env && npm start

# Projeto 3 — http://localhost:5100 (default 5000 colide com o projeto 1)
cd task-manager-api
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python seed.py                 # obrigatório: sem seed, metade das rotas responde 404
PORT=5100 .venv/bin/python app.py
```

### Validando que a refatoração funciona

O inventário de endpoints de cada projeto — método, rota e status esperado — está na seção
**"Endpoints inventariados (contrato da Fase 3)"** do relatório correspondente em
[`reports/`](reports/). É esse o contrato que a refatoração preserva.

Suba a aplicação e confira que ela responde:

```bash
# Projeto 1
cd code-smells-project && .venv/bin/python app.py &
curl -s http://127.0.0.1:5000/health
curl -s http://127.0.0.1:5000/produtos
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/produtos/9999   # 404

# Projeto 2
cd ecommerce-api-legacy && npm start &
curl -s -X POST http://127.0.0.1:3000/api/checkout \
  -H 'Content-Type: application/json' \
  -d '{"usr":"Bia","eml":"bia@teste.com","pwd":"senha123","c_id":1,"card":"4111222233334444"}'
curl -s http://127.0.0.1:3000/api/admin/financial-report

# Projeto 3 — o seed roda antes do boot; porta 5100 para não colidir com o projeto 1
cd task-manager-api && .venv/bin/python seed.py && PORT=5100 .venv/bin/python app.py &
curl -s http://127.0.0.1:5100/tasks
curl -s http://127.0.0.1:5100/reports/summary
```

O projeto 2 traz as requisições prontas em [`ecommerce-api-legacy/api.http`](ecommerce-api-legacy/api.http).
Para comparar com a versão original, rode os mesmos `curl` contra o commit anterior à refatoração
(`git checkout 6d1ce62`) e confronte os status.

---

## Estrutura do repositório

Os três projetos convergiram para o mesmo desenho de camadas — `config`, `models`, `controllers`,
`views`, `middlewares`, `services` e um composition root — apesar de linguagens e frameworks
diferentes. É o que a skill faz de agnóstico, visto de fora.

```
desafio-skills/
├── README.md
├── reports/
│   ├── audit-project-1.md              32 achados — code-smells-project
│   ├── audit-project-2.md              26 achados — ecommerce-api-legacy
│   └── audit-project-3.md              26 achados — task-manager-api
│
├── code-smells-project/                Python/Flask — API de e-commerce
│   ├── .claude/skills/refactor-arch/
│   │   ├── SKILL.md                    orquestrador das 3 fases
│   │   └── references/
│   │       ├── project-analysis.md
│   │       ├── antipatterns-catalog.md
│   │       ├── audit-report-template.md
│   │       ├── mvc-architecture.md
│   │       ├── refactoring-playbook.md
│   │       └── validation.md
│   ├── app.py                          entry point (chama a application factory)
│   ├── .env.example
│   ├── requirements.txt
│   ├── README.md
│   └── src/
│       ├── app.py                      composition root (create_app)
│       ├── config/                     settings.py · logging_config.py
│       ├── database/                   connection.py · schema.py
│       ├── models/                     base · produto · usuario · pedido · relatorio
│       ├── controllers/                produto · usuario · pedido · relatorio · health
│       ├── views/                      routes.py
│       ├── middlewares/                errors.py · error_handler.py · auth.py
│       └── services/                   notificador.py
│
├── ecommerce-api-legacy/               Node/Express — LMS com checkout
│   ├── .claude/skills/refactor-arch/   (idêntica à do projeto 1)
│   ├── api.http
│   ├── .env.example
│   ├── package.json
│   ├── package-lock.json
│   ├── README.md
│   └── src/
│       ├── app.js                      composition root (buildApp) + entry point
│       ├── config/                     settings.js · logger.js
│       ├── database/                   connection.js · schema.js
│       ├── models/                     user · course · enrollment · payment · auditLog
│       ├── controllers/                checkout · report · user
│       ├── views/                      routes.js
│       ├── middlewares/                errors.js · errorHandler.js · auth.js · crypto.js
│       └── services/                   paymentGateway.js · cache.js
│
└── task-manager-api/                   Python/Flask-SQLAlchemy — gerenciador de tarefas
    ├── .claude/skills/refactor-arch/   (idêntica à do projeto 1)
    ├── app.py                          entry point
    ├── seed.py                         carga inicial (rodar antes do primeiro boot)
    ├── .env.example
    ├── requirements.txt
    ├── README.md
    └── src/
        ├── app.py                      composition root (create_app)
        ├── database.py                 instância do SQLAlchemy
        ├── config/                     settings.py · logging_config.py
        ├── models/                     user · task · category
        ├── controllers/                task · user · report · category · health
        ├── views/                      task_routes · user_routes · report_routes
        ├── middlewares/                errors.py · error_handler.py · auth.py
        ├── services/                   notification_service.py
        └── utils/                      constants.py · validators.py
```

A skill é **byte a byte igual** nos três projetos — `diff -r` entre as três cópias não acusa
diferença. Foi o critério para considerá-la agnóstica: nada nela é específico de um projeto.

Fora do versionamento (`.gitignore`): `.env`, `node_modules/`, `.venv/`, `__pycache__/`,
`*.db` e `instance/`.
