================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   Node.js + Express 4.22.1
Files:   3 analyzed | 180 lines of code
Date:    2026-08-29

## Phase 1 — Project Analysis

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js, CommonJS)
Framework:     Express 4.22.1 (declarado ^4.18.2)
Dependencies:  sqlite3 5.1.7
Domain:        LMS com fluxo de checkout (cursos, matrículas, pagamentos e auditoria)
Architecture:  God Object — a classe AppManager concentra conexão, DDL, seed, roteamento,
               pagamento e relatório; app.js apenas a instancia
Source files:  3 files analyzed (180 lines)
DB tables:     users, courses, enrollments, payments, audit_logs
Endpoints:     3 endpoints mapeados
================================
```

## Summary

CRITICAL: 5 | HIGH: 8 | MEDIUM: 7 | LOW: 6

| Severidade | Qtd | Principais ocorrências |
|---|---|---|
| CRITICAL | 5 | Hardcoded Credentials, God Class, Sensitive Data in Logs, Broken Authentication, Missing Authentication em endpoint administrativo e destrutivo |
| HIGH | 8 | Fake Payment Authorization, Broken Cryptography, Callback Hell com race condition, Missing Transaction, Error Swallowing, Global Mutable State, Tight Coupling, No Composition Root |
| MEDIUM | 7 | N+1 Query, Referential Integrity, Missing Validation, Inconsistent Response, Missing Configuration Layer, Aggregation in Memory, Outdated/Vulnerable Dependencies |
| LOW | 6 | Poor Naming, Dead Import, console.log as Logging, Magic Strings, padrões legados de JS, resposta que documenta o bug |

## Findings

### #1 [CRITICAL] Hardcoded Credentials / Secrets

- **File:** `src/utils.js:1-7`
- **Evidence:**
  ```javascript
  dbPass: "senha_super_secreta_prod_123",
  paymentGatewayKey: "pk_live_1234567890abcdef",
  ```
- **Description:** O objeto `config` traz senha do banco de produção, chave **live** do gateway de
  pagamento e usuário de SMTP como literais no código versionado. Nenhum valor vem de variável de
  ambiente.
- **Impact:** Quem tem acesso ao repositório opera o gateway de pagamento real e o banco de
  produção. O prefixo `pk_live_` indica credencial de produção, não de sandbox — rotacionar exige
  alterar código e redeploy.
- **Recommendation:** Módulo de config lendo variáveis de ambiente, `.env.example` versionado sem
  valores, e rotação das chaves expostas (playbook: `R1`).

### #2 [CRITICAL] God Class

- **File:** `src/AppManager.js:4-139`
- **Evidence:**
  ```javascript
  class AppManager {
      constructor() { this.db = new sqlite3.Database(':memory:'); }
      initDb() { ... }
      setupRoutes(app) { ... }   // 113 linhas: rotas + SQL + pagamento + relatório
  ```
- **Description:** Uma única classe concentra criação de conexão, DDL, seed, registro de rotas HTTP,
  autorização de pagamento, cálculo de receita e deleção de usuário — cinco camadas em um arquivo.
  O método `setupRoutes` sozinho tem 113 das 141 linhas.
- **Impact:** Nenhuma parte é testável em isolamento: exercitar a regra de pagamento exige subir
  Express e SQLite. Qualquer mudança em uma rota arrisca as outras duas.
- **Recommendation:** Decompor por domínio em `models/` (user, course, enrollment, payment),
  `controllers/` (checkout, report), `views/routes.js` e `services/paymentGateway.js`
  (playbook: `R6`, `R7`, `R8`).

### #3 [CRITICAL] Sensitive Data Exposure in Logs

- **File:** `src/AppManager.js:45`
- **Evidence:**
  ```javascript
  console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
  ```
- **Description:** O número completo do cartão (PAN) recebido do cliente e a chave do gateway são
  escritos em log a cada checkout.
- **Impact:** Violação direta do PCI-DSS: qualquer coletor de logs, arquivo de stdout ou terminal
  compartilhado passa a conter números de cartão em texto plano.
- **Recommendation:** Nunca logar PAN nem chave; no máximo os quatro últimos dígitos, via logger
  estruturado (playbook: `R22`).

### #4 [CRITICAL] Broken Authentication — identidade assumida pelo e-mail

- **File:** `src/AppManager.js:40-75`
- **Evidence:**
  ```javascript
  this.db.get("SELECT id FROM users WHERE email = ?", [e], (err, user) => {
      ...
      } else { processPaymentAndEnroll(user.id); }
  ```
- **Description:** Quando o e-mail informado já existe, o fluxo assume a identidade daquele usuário e
  segue a matrícula **sem verificar a senha**. A senha recebida (`pwd`) só é usada no ramo de criação
  de usuário novo.
- **Impact:** Qualquer pessoa que saiba o e-mail de outro usuário faz checkout em nome dele e a
  matrícula é registrada na conta da vítima. Não existe autenticação em nenhum ponto da API.
- **Recommendation:** Autenticar antes do checkout (comparação de hash) e derivar o usuário do token
  da sessão, não do corpo da requisição (playbook: `R4`, `R5`).

### #5 [CRITICAL] Missing Authentication em endpoint administrativo e destrutivo

- **File:** `src/AppManager.js:80-137`
- **Evidence:**
  ```javascript
  app.get('/api/admin/financial-report', (req, res) => {
  app.delete('/api/users/:id', (req, res) => {
  ```
- **Description:** O relatório financeiro consolidado (receita por curso e nome de cada aluno) e a
  deleção de usuário por ID são públicos, sem token, sem papel e sem log de quem executou.
- **Impact:** Faturamento e base de alunos expostos a qualquer cliente; um `DELETE /api/users/1`
  anônimo remove usuários da base.
- **Recommendation:** Middleware de autenticação e verificação de papel `admin` antes dessas rotas
  (playbook: `R5`).

### #6 [HIGH] Fake Payment Authorization

- **File:** `src/AppManager.js:46`
- **Evidence:**
  ```javascript
  let status = cc.startsWith("4") ? "PAID" : "DENIED";
  ```
- **Description:** A autorização do pagamento é decidida pelo primeiro dígito do cartão — nenhuma
  chamada real ao gateway, apesar da chave de produção estar configurada. O resultado é gravado como
  `PAID` na tabela `payments`.
- **Impact:** Qualquer número começando com `4` gera matrícula paga sem cobrança real: prejuízo
  financeiro direto e base de pagamentos que não reflete a realidade.
- **Recommendation:** Isolar a integração em `services/paymentGateway.js` com a chave injetada por
  config, e tratar a resposta real do provedor (playbook: `R13`, `R1`).

### #7 [HIGH] Broken Cryptography / Plaintext Password

- **File:** `src/utils.js:17-23`, `src/AppManager.js:18, 68`
- **Evidence:**
  ```javascript
  function badCrypto(pwd) {
      for(let i = 0; i < 10000; i++) hash += Buffer.from(pwd).toString('base64').substring(0, 2);
      return hash.substring(0, 10);
  }
  ```
- **Description:** Hash caseiro que repete 10.000 vezes os dois primeiros caracteres do base64 da
  senha e trunca em 10 caracteres — é reversível por inspeção e colide para qualquer senha com o
  mesmo prefixo. O seed grava a senha `'123'` em texto plano (linha 18) e o checkout usa
  `badCrypto(p || "123456")` (linha 68), com senha padrão quando o campo vem vazio.
- **Impact:** Senhas efetivamente sem proteção; contas criadas sem senha ficam com uma senha padrão
  conhecida. O laço de 10.000 iterações ainda bloqueia o event loop a cada cadastro.
- **Recommendation:** `bcrypt`/`argon2` com salt e comparação em tempo constante; senha obrigatória
  e validada (playbook: `R4`).

### #8 [HIGH] Callback Hell com contador manual e race condition

- **File:** `src/AppManager.js:83-128`
- **Evidence:**
  ```javascript
  let enrPending = enrollments.length;
  ...
  enrPending--;
  if (enrPending === 0) { report.push(courseData); coursesPending--; if (coursesPending === 0) res.json(report); }
  ```
- **Description:** Cinco níveis de callbacks aninhados com dois contadores manuais decidindo quando
  responder. `report.push` acontece em ordem não determinística e o `res.json` depende de todos os
  contadores chegarem a zero exatamente uma vez.
- **Impact:** Se qualquer callback interno falhar, `enrPending` nunca chega a zero e a requisição
  fica pendurada até o timeout; se um curso tiver zero matrículas em condição de corrida, o
  `res.json` pode ser chamado duas vezes e derrubar o processo com
  `ERR_HTTP_HEADERS_SENT`. A ordem dos cursos no relatório varia entre chamadas.
- **Recommendation:** Promisificar o driver e usar `async/await` com `Promise.all` (playbook: `R17`).

### #9 [HIGH] Missing Transaction / Unit of Work

- **File:** `src/AppManager.js:50-63`
- **Evidence:**
  ```javascript
  this.db.run("INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)", ...
      self.db.run("INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)", ...
          self.db.run("INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))", ...
  ```
- **Description:** O checkout faz três (ou quatro, com a criação do usuário) escritas encadeadas sem
  `BEGIN`/`COMMIT`.
- **Impact:** Falha no segundo INSERT deixa matrícula sem pagamento — aluno matriculado de graça e
  base inconsistente, sem nenhum registro de auditoria do que ocorreu.
- **Recommendation:** Envolver a operação em transação com rollback (playbook: `R18`).

### #10 [HIGH] Error Swallowing

- **File:** `src/AppManager.js:57, 92, 104, 106, 133`
- **Evidence:**
  ```javascript
  this.db.run("DELETE FROM users WHERE id = ?", [id], (err) => {
      res.send("Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.");
  ```
- **Description:** Cinco callbacks recebem o parâmetro `err` e o ignoram completamente — inclusive o
  do `DELETE`, que responde sucesso mesmo se a operação falhar. Não existe error handler registrado
  no Express.
- **Impact:** Falhas de banco viram respostas de sucesso; o cliente acredita que a operação
  aconteceu. Nada é registrado para diagnóstico.
- **Recommendation:** Error handler central do Express (`app.use((err, req, res, next) => ...)`) com
  `next(erro)` nos controllers (playbook: `R10`).

### #11 [HIGH] Global Mutable State

- **File:** `src/utils.js:9-15, 25`
- **Evidence:**
  ```javascript
  let globalCache = {};
  let totalRevenue = 0;
  function logAndCache(key, data) { globalCache[key] = data; }
  ```
- **Description:** Cache global sem limite de tamanho nem TTL, alimentado a cada checkout com a chave
  `last_checkout_${userId}`, e um acumulador `totalRevenue` exportado por valor (nunca atualizado, e
  que nem poderia ser — primitivo exportado por cópia em CommonJS).
- **Impact:** O cache cresce indefinidamente enquanto o processo viver — vazamento de memória
  proporcional ao número de usuários; dados de uma requisição permanecem visíveis para as seguintes.
- **Recommendation:** Cache instanciado e injetado, com limite e TTL; agregações vêm de `SUM()` no
  banco (playbook: `R12`).

### #12 [HIGH] Tight Coupling without Dependency Injection

- **File:** `src/AppManager.js:1-8`
- **Evidence:**
  ```javascript
  constructor() {
      this.db = new sqlite3.Database(':memory:');
  }
  ```
- **Description:** A classe instancia sua própria conexão concreta no construtor e importa `config`,
  `logAndCache` e `badCrypto` diretamente do módulo de utils.
- **Impact:** Impossível instanciar `AppManager` com um banco de teste ou um gateway falso; o banco
  em memória também significa que **todos os dados somem a cada restart** — decisão de
  infraestrutura fixada em código.
- **Recommendation:** Receber a conexão e os serviços por construtor, criados no composition root
  (playbook: `R13`, `R12`).

### #13 [HIGH] No Composition Root / Missing Error Handler

- **File:** `src/app.js:5-14`
- **Evidence:**
  ```javascript
  const manager = new AppManager();
  manager.initDb();
  manager.setupRoutes(app);
  ```
- **Description:** O entry point instancia o God Object, dispara a criação do schema como efeito
  colateral e sobe o servidor em escopo de módulo. Não há factory, não há middleware de erro, não há
  tratamento de `unhandledRejection`, e `initDb()` é fire-and-forget (os callbacks de erro do DDL
  nem são passados).
- **Impact:** Importar `app.js` em um teste sobe o servidor real na porta 3000; uma falha no DDL
  passa despercebida e a aplicação atende requisições com o banco incompleto.
- **Recommendation:** `buildApp()` que cria dependências, registra rotas e o error handler, com o
  `listen` isolado (playbook: `R9`, `R10`).

### #14 [MEDIUM] N+1 Query

- **File:** `src/AppManager.js:83-127`
- **Evidence:**
  ```javascript
  this.db.all("SELECT * FROM courses", [], (err, courses) => {
      courses.forEach(c => {
          this.db.all("SELECT * FROM enrollments WHERE course_id = ?", [c.id], (err, enrollments) => {
              enrollments.forEach(enr => {
                  this.db.get("SELECT name, email FROM users WHERE id = ?", ...
                      this.db.get("SELECT amount, status FROM payments WHERE enrollment_id = ?", ...
  ```
- **Description:** O relatório financeiro faz 1 query de cursos, N de matrículas e **duas** por
  matrícula (usuário e pagamento) — quatro níveis de N+1.
- **Impact:** 50 cursos com 100 matrículas cada = 10.051 queries em uma única requisição HTTP.
- **Recommendation:** Uma query com `JOIN` entre courses, enrollments, users e payments, agregando
  a receita em SQL (playbook: `R14`, `R17`).

### #15 [MEDIUM] Referential Integrity Ignored

- **File:** `src/AppManager.js:131-137`
- **Evidence:**
  ```javascript
  res.send("Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.");
  ```
- **Description:** A deleção remove apenas a linha de `users`, deixando `enrollments` e `payments`
  órfãos — o próprio código documenta isso na resposta ao cliente. O schema (linhas 12-16) não
  declara nenhuma `FOREIGN KEY`.
- **Impact:** O relatório financeiro passa a mostrar `student: 'Unknown'` com receita associada;
  pagamentos ficam sem dono, corrompendo a conciliação.
- **Recommendation:** Transação removendo dependentes ou `ON DELETE CASCADE` no schema; alternativa
  legítima é recusar com `409` (playbook: `R16`).

### #16 [MEDIUM] Missing Input Validation

- **File:** `src/AppManager.js:35, 68`
- **Evidence:**
  ```javascript
  if (!u || !e || !cid || !cc) return res.status(400).send("Bad Request");
  let hash = badCrypto(p || "123456");
  ```
- **Description:** A validação cobre apenas presença de quatro campos: não valida formato de e-mail,
  não valida o cartão, não exige senha (a linha 68 substitui a ausência por `"123456"`) e não
  converte `c_id` para número.
- **Impact:** Contas criadas com senha padrão conhecida; e-mails inválidos entram na base e viram
  chave de identidade no achado #4.
- **Recommendation:** Camada de validação declarativa antes do controller, com senha obrigatória
  (playbook: `R20`).

### #17 [MEDIUM] Inconsistent Response Shape

- **File:** `src/AppManager.js:35, 38, 48, 51, 55, 60, 135`
- **Evidence:**
  ```javascript
  return res.status(400).send("Bad Request");
  res.status(200).json({ msg: "Sucesso", enrollment_id: enrId });
  ```
- **Description:** O mesmo endpoint responde `text/plain` em erro e `application/json` em sucesso;
  entre endpoints, um devolve array cru, outro objeto, outro string. Mensagens misturam português e
  inglês.
- **Impact:** O cliente precisa de um parser diferente por caminho de execução; erros não são
  processáveis programaticamente.
- **Recommendation:** Envelope único de erro e sucesso via error handler e serializador
  (playbook: `R10`, `R3`).

### #18 [MEDIUM] Missing Configuration Layer / Schema no código da aplicação

- **File:** `src/AppManager.js:7, 10-23`
- **Evidence:**
  ```javascript
  this.db = new sqlite3.Database(':memory:');
  this.db.run("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, pass TEXT)");
  ```
- **Description:** Caminho do banco, DDL das cinco tabelas e dados de seed estão embutidos na classe
  de aplicação, executados a cada boot. Nenhuma coluna tem `NOT NULL`, `UNIQUE` ou `FOREIGN KEY`.
- **Impact:** Não é possível apontar para outro banco sem alterar código; o schema não pode evoluir
  de forma versionada; dois usuários podem ter o mesmo e-mail, quebrando a identidade do achado #4.
- **Recommendation:** Config por ambiente, schema e seed em módulos próprios chamados no bootstrap,
  com constraints declaradas (playbook: `R1`, `R8`).

### #19 [MEDIUM] Aggregation in Memory / SELECT *

- **File:** `src/AppManager.js:83, 92, 108-115`
- **Evidence:**
  ```javascript
  if (payment && payment.status === 'PAID') { courseData.revenue += payment.amount; }
  ```
- **Description:** A receita por curso é somada em JavaScript, registro a registro, e as consultas
  usam `SELECT *` mesmo precisando de duas colunas.
- **Impact:** Todo o dataset trafega do banco para o processo a cada chamada do relatório; a soma
  poderia ser um `SUM(...) WHERE status = 'PAID'`.
- **Recommendation:** Agregar em SQL e selecionar apenas as colunas necessárias (playbook: `R14`).

### #20 [MEDIUM] Outdated / Vulnerable Dependencies

- **File:** `package.json:9-12`
- **Evidence:**
  ```json
  "express": "^4.18.2",
  "sqlite3": "^5.1.6"
  ```
- **Description:** `npm outdated` aponta Express 4.22.1 instalado com 5.2.1 disponível e sqlite3
  5.1.7 com 6.0.1 disponível. `npm audit --omit=dev` reporta **13 vulnerabilidades (1 crítica, 7
  altas)** na árvore de dependências de build do sqlite3. Não há script de teste nem de lint.
- **Impact:** A aplicação carrega vulnerabilidades conhecidas e não tem rede de segurança automatizada
  para permitir a atualização.
- **Recommendation:** Atualizar com verificação de breaking changes e adicionar suíte mínima de
  testes antes do bump de major (playbook: `R19`).

### #21 [LOW] Poor Naming

- **File:** `src/AppManager.js:29-33`
- **Evidence:**
  ```javascript
  let u = req.body.usr;
  let e = req.body.eml;
  let p = req.body.pwd;
  let cid = req.body.c_id;
  let cc = req.body.card;
  ```
- **Description:** Cinco variáveis de uma ou duas letras para conceitos centrais do domínio. `e` é
  especialmente ruim: no restante do arquivo `e`/`err` denota erro. O contrato público da API tem o
  mesmo problema (`usr`, `eml`, `pwd`, `c_id`).
- **Impact:** Leitura ambígua em um método de 113 linhas onde `e` significa e-mail em um escopo e
  erro no escopo aninhado.
- **Recommendation:** Desestruturar com nomes de domínio (playbook: `R21`).

### #22 [LOW] Dead Import / Export de primitivo

- **File:** `src/AppManager.js:2`, `src/utils.js:10, 25`
- **Evidence:**
  ```javascript
  const { config, logAndCache, badCrypto, totalRevenue } = require('./utils');
  ```
- **Description:** `totalRevenue` é importado e nunca usado; exportado por valor, jamais refletiria
  atualizações mesmo se fosse.
- **Impact:** Sugere um mecanismo de acumulação que não existe.
- **Recommendation:** Remover.

### #23 [LOW] console.log as Logging

- **File:** `src/AppManager.js:45`, `src/app.js:13`, `src/utils.js:13`
- **Evidence:**
  ```javascript
  console.log(`[LOG] Salvando no cache: ${key}`);
  ```
- **Description:** Log via `console.log`, com prefixo manual `[LOG]`, sem nível nem estrutura.
- **Impact:** Não há como filtrar por severidade nem desligar em produção — e é por esse caminho que
  o cartão vaza no achado #3.
- **Recommendation:** Logger com níveis, injetado (playbook: `R22`).

### #24 [LOW] Magic Strings e Magic Numbers

- **File:** `src/AppManager.js:21, 46, 108`, `src/utils.js:6, 19, 22`
- **Evidence:**
  ```javascript
  let status = cc.startsWith("4") ? "PAID" : "DENIED";
  for(let i = 0; i < 10000; i++)
  ```
- **Description:** Status de pagamento como string literal repetida em três arquivos, o dígito `"4"`
  como regra de bandeira, `10000` iterações e `3000` como porta, todos sem constante nomeada.
- **Impact:** Trocar `PAID` por outro rótulo exige caçar ocorrências; nada documenta o significado
  dos literais.
- **Recommendation:** Constantes/enum de domínio (playbook: `R21`).

### #25 [LOW] Padrões legados de JavaScript

- **File:** `src/AppManager.js:26, 29-33, 43`
- **Evidence:**
  ```javascript
  const self = this;
  ```
- **Description:** `const self = this` para contornar o escopo de `function(err)`, `let` em variáveis
  nunca reatribuídas, e uso alternado de `this` e `self` no mesmo método.
- **Impact:** Confusão sobre qual contexto está ativo em cada nível de callback.
- **Recommendation:** Arrow functions e `const`; o `self` desaparece com a promisificação
  (playbook: `R17`, `R21`).

### #26 [LOW] Resposta que documenta o defeito

- **File:** `src/AppManager.js:135`
- **Evidence:**
  ```javascript
  res.send("Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.");
  ```
- **Description:** A mensagem de sucesso narra ao cliente um defeito conhecido em vez de corrigi-lo.
- **Impact:** Contrato de API que documenta corrupção de dados como comportamento esperado.
- **Recommendation:** Corrigir a integridade (achado #15) e devolver uma resposta neutra.

## Deprecated APIs

Varredura por `new Buffer()`, `url.parse()`, `util.isArray`, `body-parser`, `crypto.createCipher`,
`domain` e `process.binding`: **nenhuma API deprecated do Node em uso**. O projeto já usa
`Buffer.from()` e `express.json()` embutido.

O ponto relevante nesta família é de versão, não de API (achado #20):

| Item | Arquivo:linha | Situação | Substituto |
|---|---|---|---|
| `express ^4.18.2` | `package.json:10` | Express 4 em manutenção; 5.2.1 é a linha atual | Express 5 (após testes) |
| `sqlite3 ^5.1.6` | `package.json:11` | 6.0.1 disponível; árvore com 13 CVEs (1 crítica) | sqlite3 6 ou `node:sqlite` |
| API de callbacks do `sqlite3` | `src/AppManager.js:37-133` | Estilo callback sem Promise, origem do achado #8 | `util.promisify` / driver com Promise |

## Endpoints inventariados (contrato da Fase 3)

| # | Método | Rota | Status baseline |
|---|---|---|---|
| 1 | POST | `/api/checkout` | 200 / 400 / 404 / 500 |
| 2 | GET | `/api/admin/financial-report` | 200 |
| 3 | DELETE | `/api/users/:id` | 200 |

## Plano de refatoração proposto

1. **config/** — porta, caminho do banco, chave do gateway e SMTP vindos de variáveis de ambiente,
   com `.env.example` (resolve #1, parte de #18).
2. **database/** — `connection.js` promisificado e injetável, `schema.js` com DDL + constraints e
   `seed.js` separados (resolve #12, #18 e habilita #8, #9, #15).
3. **models/** — `userModel`, `courseModel`, `enrollmentModel`, `paymentModel`, `auditLogModel`
   com queries parametrizadas, `JOIN` no relatório e transação no checkout
   (resolve #9, #14, #15, #19).
4. **services/paymentGateway.js** — a integração isolada, com chave injetada
   (resolve #6 e parte de #1).
5. **controllers/** — `checkoutController` e `reportController` em `async/await`, sem SQL
   (resolve #2, #8, #16).
6. **views/routes.js** — mapa rota → controller preservando as 3 rotas, com middleware de
   autenticação nas rotas administrativas (resolve #5).
7. **middlewares/** — `errorHandler` central e logger sem dado sensível (resolve #10, #17, #23, #3).
8. **app.js** — `buildApp()` como composition root, `listen` isolado (resolve #13).
9. Limpeza: hash com bcrypt, nomes de domínio, constantes, remoção de estado global
   (resolve #7, #11, #21, #22, #24, #25, #26).

================================
Total: 26 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
