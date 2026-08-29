# Catálogo de anti-patterns

Fonte da verdade da Fase 2: nome canônico, severidade e **sinais objetivos de detecção**.
Cada entrada traz comandos de busca agnósticos de framework — rode-os e depois confirme
lendo o arquivo na linha encontrada. Um sinal que dispara sem evidência literal no código
é falso positivo e deve ser descartado.

## Escala de severidade

| Nível | Critério | Exemplos canônicos |
|---|---|---|
| **CRITICAL** | Falha grave de arquitetura ou segurança que impede o funcionamento correto, expõe dados sensíveis ou destrói completamente a separação de responsabilidades | credenciais hardcoded, SQL Injection, God Class com banco + regra + rota, endpoint que executa SQL arbitrário, segredo devolvido na resposta HTTP |
| **HIGH** | Forte violação de MVC/SOLID que dificulta muito manutenção e testes | regra de negócio pesada dentro do controller/rota, acoplamento forte sem injeção de dependência, estado global mutável, senha em texto plano ou hash fraco, endpoint administrativo sem autenticação |
| **MEDIUM** | Padronização, duplicação, performance moderada | query N+1, validação ausente na rota, API deprecated, ausência de paginação, tratamento de erro repetido em toda função, integridade referencial não tratada |
| **LOW** | Legibilidade e estilo | magic numbers/strings, nomes ruins, `if/else` que devolve booleano, imports não usados, `print`/`console.log` como logging |

Regra de calibração: **não infle**. Um `print` não é HIGH. Um SQL Injection não é MEDIUM.
Na dúvida entre dois níveis, escolha o menor e justifique no campo *Impact*.

---

# Família A — Segurança

## A1. Hardcoded Credentials / Secrets — CRITICAL
Segredo literal no código versionado: senha, chave de API, `SECRET_KEY`, token, string de conexão.

**Detecção**
```bash
grep -rniE "(secret|password|passwd|pwd|api[_-]?key|token|private[_-]?key)\s*[:=]\s*['\"][^'\"]{3,}" \
  --include='*.py' --include='*.js' --include='*.ts' --include='*.php' --include='*.go' .
grep -rnE "(pk_live|sk_live|AKIA[0-9A-Z]{16}|ghp_|xox[baprs]-)" .
```
Sinais: atribuição literal fora de `.env`/vault; dicionário `config = {...}` com senha; credencial
de SMTP/gateway dentro de `__init__` de serviço.
**Impacto**: qualquer pessoa com acesso ao repositório assume a identidade da aplicação; rotação exige deploy.
**Correção**: R1 do playbook (extrair para módulo de config lendo variáveis de ambiente + `.env.example`).

## A2. SQL Injection — CRITICAL
Query montada por concatenação/interpolação com dado que vem do usuário.

**Detecção**
```bash
grep -rnE "(execute|query|run|raw)\s*\(\s*[\"'].*[\"']\s*\+" .          # concatenação
grep -rnE "(execute|query)\s*\(\s*f[\"']|\\$\{.*\}.*(SELECT|INSERT|UPDATE|DELETE)" .  # f-string / template
grep -rniE "(SELECT|INSERT|UPDATE|DELETE).*(\+ *str\(|% *\(|\.format\()" .
```
Sinal decisivo: o valor concatenado vem de `request`, `params`, `body`, `query`, `argv` — direta ou
indiretamente. Concatenar constante interna é *code smell*, não injeção: registre como MEDIUM.
**Impacto**: leitura, alteração e destruição de dados; bypass de autenticação (`' OR '1'='1`).
**Correção**: R2 (query parametrizada / placeholders / ORM).

## A3. Arbitrary Query / Command Execution Endpoint — CRITICAL
Rota HTTP que recebe SQL, shell ou código do cliente e executa.

**Detecção**
```bash
grep -rnE "(execute|exec|eval|system|spawn|popen)\s*\(.*(req|request)\." .
grep -rniE "route.*(admin|debug|console|query|exec)" .
```
**Impacto**: RCE ou controle total do banco por qualquer cliente. Não existe mitigação parcial.
**Correção**: R11 (remover o endpoint; se houver necessidade operacional real, substituir por
comando de CLI/manutenção fora da superfície HTTP, documentando a remoção).

## A4. Sensitive Data Exposure in Response — CRITICAL
A resposta HTTP devolve segredo ou credencial: `secret_key`, hash/senha de usuário, config interna,
caminho de banco, flag de debug.

**Detecção**
```bash
grep -rnE "(jsonify|res\.json|return).*(senha|password|secret|token|hash)" .
```
Verifique também serializadores (`to_dict`, `toJSON`, `serialize`) que expõem a coluna de senha.
**Impacto**: vazamento em massa por um simples `GET`; o `/health` vira oráculo de credenciais.
**Correção**: R3 (serializador explícito por camada, sem campos sensíveis).

## A5. Weak or Absent Password Hashing — HIGH
Senha gravada em texto plano, em base64, com MD5/SHA1 sem salt, ou com "criptografia" caseira.

**Detecção**
```bash
grep -rniE "md5|sha1|base64|btoa|atob|rot13" .
grep -rniE "(pass|senha|pwd)\s*[:=].*(request|req\.body|data\.get)" .
```
Sinal: comparação direta `user.password == hash(input)` sem `hmac.compare_digest`/`bcrypt.compare`;
função própria chamada `badCrypto`, `myHash`, `encrypt`.
**Impacto**: vazamento do banco = vazamento das senhas reais dos usuários.
**Correção**: R4 (`bcrypt`/`argon2`/`werkzeug.security` com comparação em tempo constante).

## A6. Missing Authentication / Authorization — HIGH
Endpoint que altera dados, expõe relatório financeiro ou administra o sistema sem checar identidade
nem papel.

**Detecção**: cruze o inventário de endpoints da Fase 1 com a existência de qualquer middleware,
decorator ou guard de autenticação. Zero ocorrências de `login_required`, `@jwt_required`,
`passport.authenticate`, `authMiddleware`, `before_request` → todos os endpoints estão abertos.
```bash
grep -rniE "login_required|jwt_required|authenticate|authorize|middleware.*auth|before_request" .
```
**Impacto**: qualquer cliente lê e altera dados de qualquer outro; `/admin/*` público.
**Correção**: R5 (middleware de autenticação + verificação de papel na camada de rota).

## A7. Insecure Defaults (DEBUG / CORS / bind) — HIGH
`DEBUG=True` fora de desenvolvimento, CORS liberado para qualquer origem, bind em `0.0.0.0` com
debugger ativo, `TRACE`/stacktrace devolvido ao cliente.

**Detecção**
```bash
grep -rniE "debug\s*=\s*true|DEBUG.*True|CORS\(app\)|origin.*\*|cors\(\)" .
grep -rnE "host\s*=\s*['\"]0\.0\.0\.0" .
```
**Impacto**: com Flask, `DEBUG=True` expõe o console Werkzeug (execução de código remota);
CORS aberto permite que qualquer site faça requisições autenticadas.
**Correção**: R1 (config por ambiente; debug e origens vindos de variável de ambiente).

## A8. Fake / Predictable Token — HIGH
Token de sessão previsível (`"fake-jwt-token-" + user.id`), sem assinatura, sem expiração.

**Detecção**
```bash
grep -rniE "fake.?(jwt|token)|token['\"]?\s*[:=].*\+\s*str\(|token.*\+ *user" .
```
**Impacto**: escalada de privilégio trocando um número na string.
**Correção**: R5 (JWT assinado com segredo de ambiente e expiração, ou sessão do framework).

---

# Família B — Arquitetura e MVC

## B1. God Class / God Object — CRITICAL
Uma classe ou módulo concentra roteamento + acesso a dados + regra de negócio + infraestrutura.

**Detecção**
```bash
wc -l **/*.{py,js,ts,php}                      # arquivos muito acima da mediana do projeto
grep -c "def \|function \|=> {" <arquivo>      # densidade de responsabilidades
```
Sinais: um mesmo arquivo contém `route`/`app.get` **e** `execute`/`query` **e** cálculo de regra;
nome genérico (`Manager`, `Helper`, `Utils`, `Service`, `App`) sem domínio; método `setupRoutes`
com centenas de linhas.
**Impacto**: impossível testar em isolamento; qualquer mudança arrisca todo o sistema; conflitos
permanentes de merge.
**Correção**: R6 (decompor por domínio em model/controller/rota).

## B2. God Method / Long Method — HIGH
Função com muitas responsabilidades encadeadas: validar, buscar, calcular, persistir, notificar,
formatar.

**Detecção**: função com mais de ~50 linhas, mais de 3 níveis de aninhamento, ou que toca banco,
regra e resposta HTTP na mesma unidade.
**Impacto**: cada regra só é testável subindo o request inteiro.
**Correção**: R6 e R7 (extrair método; mover a orquestração para o controller).

## B3. Business Logic in Controller/Route — HIGH
Regra de negócio (preço, desconto, estoque, transição de status, agregação de relatório) escrita
dentro do handler HTTP.

**Detecção**
```bash
grep -rnE -A20 "@app\.route|app\.(get|post|put|delete)|def .*\(.*\):" . | \
  grep -nE "\* *0\.[0-9]|if .*(total|preco|price|estoque|stock|status) *[<>=]"
```
Sinal: dentro do handler existe cálculo aritmético de domínio, laço de agregação, ou lista literal
de estados válidos.
**Impacto**: a regra não pode ser reusada por outro canal (CLI, worker, outro endpoint) nem testada
sem HTTP.
**Correção**: R7 (regra desce para o model/serviço; o controller só orquestra).

## B4. Data Access in Controller/View — HIGH
SQL cru ou chamada de ORM dentro do handler de rota, pulando a camada de modelo.

**Detecção**
```bash
grep -rnE "(cursor|db|conn|session|Model)\.(execute|query|run|all|get|filter)" \
  <arquivos de rota/controller>
```
**Impacto**: o schema vaza para a camada de apresentação; trocar o banco obriga a reescrever rotas.
**Correção**: R8 (repositório/model por entidade).

## B5. Missing Configuration Layer — HIGH
Configuração espalhada em literais dentro do código da aplicação (porta, caminho do banco, host de
SMTP, chave de gateway, URL de serviço externo).

**Detecção**
```bash
grep -rnE "port\s*[:=]\s*[0-9]{2,5}|localhost|127\.0\.0\.1|smtp\.|\.db['\"]|sqlite:///" .
ls .env.example config/ settings.py 2>/dev/null   # ausência é o sinal
```
**Impacto**: um binário por ambiente; segredo em git; impossível rodar em container sem editar código.
**Correção**: R1.

## B6. No Composition Root / Implicit Wiring — HIGH
Entry point que instancia, configura e registra tudo em escopo de módulo, sem um ponto único de
composição — ou pior, sem entry point identificável.

**Detecção**: `app = Flask(__name__)` seguido de dezenas de `add_url_rule` no mesmo arquivo;
`new Manager()` no topo do `app.js`; ausência de `create_app()`/`bootstrap()`/`main()`.
**Impacto**: impossível criar a aplicação em modo de teste com dependências falsas.
**Correção**: R9 (application factory + composition root).

## B7. Missing Centralized Error Handling — MEDIUM
Cada função repete `try/except` devolvendo `500` com a mensagem crua da exceção.

**Detecção**
```bash
grep -rc "try:" --include='*.py' . ; grep -rc "try {" --include='*.js' .
grep -rnE "except Exception as e:|catch *\(err" -A3 . | grep -c "500"
```
Sinal: mais de ~1 bloco `try` por função pública; `str(e)` ou `err.message` dentro do corpo da resposta.
**Impacto**: mensagem interna vaza para o cliente; formato de erro inconsistente entre rotas;
ruído que esconde a regra de negócio.
**Correção**: R10 (error handler central + exceções de domínio).

## B8. Global Mutable State — HIGH
Variável de módulo mutável compartilhada entre requisições: cache global, contador, conexão única,
acumulador de receita.

**Detecção**
```bash
grep -rnE "^\s*(global |let |var )[a-zA-Z_]+\s*=\s*(\{\}|\[\]|0|None|null)" .
grep -rn "global " --include='*.py' .
```
**Impacto**: vazamento de dados entre requisições, corrida em ambiente multi-thread/worker,
testes que dependem de ordem de execução.
**Correção**: R12 (estado por requisição / injeção de dependência / factory de conexão).

## B9. Tight Coupling without Dependency Injection — HIGH
Módulo instancia concretamente suas dependências (`new Database()`, `smtplib.SMTP(...)`,
`import db` global) em vez de recebê-las.

**Detecção**
```bash
grep -rnE "new [A-Z][a-zA-Z]*\(|= *[A-Z][a-zA-Z]*\(\)" . | grep -viE "test|spec"
grep -rnE "smtplib\.|requests\.(get|post)|fetch\(|axios\." <arquivos de model/serviço>
```
**Impacto**: nenhum teste unitário sem rede/banco reais; troca de implementação exige editar o consumidor.
**Correção**: R13 (injetar dependência pelo construtor/parâmetro, com default de produção).

---

# Família C — Dados e performance

## C1. N+1 Query — MEDIUM
Uma query para a coleção e mais uma (ou várias) por item dentro do laço.

**Detecção**
```bash
grep -rnE -B5 "(execute|query|\.get\(|filter_by|findOne)" . | grep -E "for |forEach|while |map\("
```
Sinal literal: chamada ao banco cujo argumento usa a variável de iteração do laço externo.
**Impacto**: latência linear no tamanho da coleção; 100 itens = 201 idas ao banco.
**Correção**: R14 (`JOIN`, `IN (...)`, `selectinload`/`include`, ou agregação em SQL).

## C2. Aggregation in Application Memory — MEDIUM
Contagens, somas e percentuais calculados percorrendo todos os registros em memória, quando o banco
faz em uma query.

**Detecção**
```bash
grep -rnE "\.all\(\)|fetchall\(\)" -A10 . | grep -E "count|sum|total|\+= 1|\+ 1"
```
**Impacto**: transferência do dataset inteiro a cada request; relatório que degrada com o tempo.
**Correção**: R14 (`COUNT`, `SUM`, `GROUP BY`).

## C3. Missing Pagination — MEDIUM
Endpoint de listagem que devolve a tabela inteira, sem `limit`/`offset` nem cursor.

**Detecção**: no inventário de endpoints, todo `GET` de coleção cuja implementação chama
`.all()`/`SELECT *` sem cláusula de limite.
**Impacto**: resposta cresce sem limite; timeout e consumo de memória em produção.
**Correção**: R15 (parâmetros `page`/`per_page` com teto e envelope de metadados).

## C4. Referential Integrity Ignored — MEDIUM
Deleção de entidade pai sem tratar filhos: nem cascade, nem bloqueio, nem limpeza — o banco fica
com registros órfãos.

**Detecção**
```bash
grep -rnE "DELETE FROM|\.delete\(" -A5 . | grep -viE "cascade|ondelete|foreign"
grep -rn "FOREIGN KEY" .        # ausência total em schema relacional é sinal
```
**Impacto**: relatórios contam registros inexistentes; joins retornam `NULL` silencioso.
**Correção**: R16 (transação + cascade explícito ou recusa com `409`).

## C5. Callback Hell / Missing Async Contract — MEDIUM
Callbacks aninhados em três ou mais níveis, com contadores manuais (`pending--`) para saber quando
responder; erro de cada nível ignorado.

**Detecção**
```bash
grep -rnE "function *\(err" . | wc -l
grep -rnE "pending--|counter--|remaining--" .
```
Sinal: `res.json()` dentro de `if (pending === 0)`; `if (err)` sem tratamento em nível interno.
**Impacto**: resposta dupla ou ausente, ordem não determinística, erro engolido — bug de corrida
que só aparece em produção.
**Correção**: R17 (promisificar + `async/await` + `Promise.all`).

## C6. Connection Mismanagement — HIGH
Conexão única global reaproveitada entre requisições (`check_same_thread=False`), sem pool, sem
fechamento, sem transação explícita em operação de escrita composta.

**Detecção**
```bash
grep -rnE "check_same_thread *= *False|global .*(conn|db)|new sqlite3\.Database" .
grep -rnE "commit\(\)" . ; grep -rniE "begin|transaction|rollback" .   # commit sem rollback
```
**Impacto**: corrupção sob concorrência; escrita parcial quando um passo falha no meio.
**Correção**: R12 + R18 (factory de conexão por request e transação com rollback).

---

# Família D — APIs deprecated e dependências

## D1. Deprecated Framework/Language API — MEDIUM
Uso de API marcada como obsoleta na versão declarada no manifesto. Detectar **é obrigatório**:
o código funciona hoje e quebra no próximo upgrade.

**Detecção**
```bash
# Python
grep -rn "datetime.utcnow()\|datetime.utcfromtimestamp(" .   # deprecated no 3.12+
grep -rn "\.query\.get(\|Query.get(" .                       # legado no SQLAlchemy 2.x → Session.get()
grep -rn "@app.before_first_request" .                        # removido no Flask 2.3+
grep -rn "imp\.\|distutils\|asyncio.get_event_loop()" .
# Node/JS
grep -rn "new Buffer(\|url.parse(\|util.isArray\|require('querystring')" .
grep -rn "body-parser" .                                      # embutido no Express 4.16+
grep -rn "crypto.createCipher(" .                             # → createCipheriv
# genérico
grep -rniE "deprecated|obsolete|legacy" .
```
Confronte sempre com a versão do manifesto: `datetime.utcnow()` é deprecated a partir do Python
3.12; `Model.query` é legado a partir do SQLAlchemy 2.0/Flask-SQLAlchemy 3.1.
**Impacto**: `DeprecationWarning` hoje, quebra no upgrade; no caso de `utcnow()`, datetime *naive*
que compara errado com datetime com fuso.
**Correção**: R19 (substituir pela API atual: `datetime.now(timezone.utc)`, `db.session.get()`,
`Buffer.from()`, `express.json()`).

## D2. Outdated / Vulnerable Dependency — MEDIUM
Dependência presa em major antiga ou com CVE conhecido.

**Detecção**
```bash
npm outdated ; npm audit --omit=dev
pip list --outdated
```
Registre apenas o que o manifesto comprova (versão declarada × última estável).
**Correção**: R19 (bump com verificação de breaking changes; nunca subir major cegamente).

## D3. Unpinned Dependency — LOW
Dependência sem versão fixada (`flask`, `express: "*"`) — build não reprodutível.
**Detecção**: linhas do manifesto sem `==`, `~=` ou range explícito.
**Correção**: fixar versão exata ou faixa compatível.

---

# Família E — Duplicação e padronização

## E1. Duplicated Code — MEDIUM
Bloco equivalente repetido em mais de um lugar: mesma validação, mesma serialização, mesmo laço.

**Detecção**: compare handlers do mesmo recurso (`create`/`update` costumam ser cópias);
serializações `to_dict` reescritas manualmente dentro das rotas; a mesma lista de status válidos
declarada em três arquivos.
```bash
grep -rn "valid.*=\s*\[" . | sort | uniq -c | sort -rn
```
**Impacto**: correção aplicada em um lugar e esquecida nos outros; regras divergem com o tempo.
**Correção**: R20 (extrair para validador/serializador único).

## E2. Duplicated Validation Across Layers — MEDIUM
A mesma regra validada na rota, no helper e no model, com mensagens diferentes.
**Impacto**: a fonte da verdade some; erros inconsistentes para o cliente.
**Correção**: R20 (uma camada de validação, invocada pelo controller).

## E3. Dead Code / Unused Imports — LOW
Import não usado, função nunca chamada, variável atribuída e ignorada, helper órfão.
**Detecção**
```bash
grep -rn "^import \|^from .* import" . # e confira cada símbolo com grep no arquivo
python -m pyflakes . 2>/dev/null ; npx eslint --no-eslintrc --rule '{"no-unused-vars":"warn"}' . 2>/dev/null
```
**Correção**: remover.

## E4. Inconsistent Response Shape — MEDIUM
Endpoints do mesmo projeto devolvem envelopes diferentes (`{dados, sucesso}` × array cru × string
solta) e usam status inconsistentes (`200` para erro, `500` para validação).
**Detecção**: compare os `return`/`res.send` de todos os handlers do inventário.
**Correção**: R3 + R10 (serializador e error handler padronizam envelope e status).

---

# Família F — Legibilidade

## F1. Magic Numbers / Magic Strings — LOW
Literal com significado de domínio embutido no meio do código: `0.1`, `10000`, `'aprovado'`,
`'#000000'`, `5`, `200`.
**Detecção**
```bash
grep -rnE "[^a-zA-Z_.\"'][0-9]{2,}(\.[0-9]+)?[^0-9]" . | grep -viE "port|status|http"
grep -rnE "== *['\"][a-z_]+['\"]|in \[['\"]" .
```
**Correção**: R21 (constantes/enums nomeados na camada de domínio).

## F2. Poor Naming — LOW
Identificadores de uma letra ou abreviações opacas para conceitos de domínio: `u`, `e`, `p`, `cid`,
`cc`, `d`, `t`, `res` para coisas que não são response.
**Detecção**
```bash
grep -rnE "(let|const|var|^\s*)[a-z]{1,2}\s*=\s*req\.|= *request\." .
```
**Correção**: R21 (renomear para o termo do domínio).

## F3. Boolean Return Antipattern — LOW
`if cond: return True else: return False` em vez de `return cond`; `if x == True`.
**Detecção**
```bash
grep -rn -A2 "return True" . | grep -B1 "return False"
```
**Correção**: R21.

## F4. print/console.log as Logging — LOW
Saída de diagnóstico via `print`/`console.log`, sem nível, sem estrutura, às vezes contendo dado
sensível (número de cartão, e-mail, senha).
**Detecção**
```bash
grep -rn "print(\|console\.log(" . | grep -v test
```
Se o conteúdo impresso contém dado sensível, o achado sobe para **HIGH** (vira A4 em log).
**Correção**: R22 (logger com níveis, injetado).

## F5. Silent Exception Swallowing — MEDIUM
`except:` nu, `except Exception: pass`, `catch (e) {}` — o erro desaparece.
**Detecção**
```bash
grep -rnE "except *:|except Exception *:" -A2 . | grep -E "pass|return None"
grep -rnE "catch *\([a-z]*\) *\{ *\}" .
```
**Impacto**: falha silenciosa; bug impossível de diagnosticar em produção.
**Correção**: R10 (deixar propagar para o error handler central, ou tratar com log e erro tipado).

## F6. Deep Nesting / Arrow Code — LOW
Três ou mais níveis de `if` aninhado onde um *early return* resolveria.
**Detecção**: indentação ≥ 12 espaços em corpo de função; `if` dentro de `if` dentro de `if`.
**Correção**: R21 (guard clauses).

---

## Como usar este catálogo na Fase 2

1. Rode os comandos de detecção de cada família contra os arquivos de código-fonte.
2. Para cada hit, **abra o arquivo e confirme** — anote a linha exata e copie o trecho literal.
3. Nomeie o achado com o **nome canônico** deste catálogo (o `Ax`/`Bx` fica implícito; use o nome).
4. Aplique a severidade da entrada, ajustando só quando o contexto justificar (com nota no *Impact*).
5. Deduplique por `arquivo + padrão` e ordene CRITICAL → HIGH → MEDIUM → LOW.

Cobertura mínima esperada de uma auditoria séria: todas as seis famílias percorridas, mesmo que
alguma não produza achado — a ausência também é informação.
