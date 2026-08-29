# Playbook de refatoração

Uma transformação concreta por anti-pattern do catálogo. Os exemplos alternam Python e JavaScript
de propósito: **o padrão é o mesmo, a sintaxe é detalhe**. Aplique um padrão por vez e mantenha a
aplicação subindo entre eles.

Ordem recomendada: `R1` (config) → `R2`/`R4` (segurança de dados) → `R8`/`R6` (models) →
`R7` (regra sai do controller) → `R9` (composition root) → `R10` (erros) → o resto.

---

## R1 — Extrair configuração para módulo de config

**Resolve:** A1 Hardcoded Credentials, A7 Insecure Defaults, B5 Missing Configuration Layer.

**Antes**
```python
# app.py
app.config["SECRET_KEY"] = "<redacted>"
app.config["DEBUG"] = True
CORS(app)
app.run(host="0.0.0.0", port=5000, debug=True)
```

**Depois**
```python
# src/config/settings.py
import os

class Settings:
    SECRET_KEY  = os.getenv("SECRET_KEY", "")
    DEBUG       = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    HOST        = os.getenv("HOST", "127.0.0.1")
    PORT        = int(os.getenv("PORT", "5000"))
    DB_PATH     = os.getenv("DB_PATH", "loja.db")
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]

    @classmethod
    def validate(cls):
        if not cls.DEBUG and not cls.SECRET_KEY:
            raise RuntimeError("SECRET_KEY precisa ser definida fora de desenvolvimento")

settings = Settings()
```
```bash
# .env.example  (versionado, sem valores reais)
SECRET_KEY=
FLASK_DEBUG=false
PORT=5000
DB_PATH=loja.db
CORS_ORIGINS=http://localhost:3000
```

Regras: default seguro para desenvolvimento; `DEBUG` **nunca** default `true`; CORS com origem
explícita em vez de `*`; segredo sem default em produção falha no boot.

---

## R2 — Parametrizar queries

**Resolve:** A2 SQL Injection.

**Antes**
```python
cursor.execute("SELECT * FROM produtos WHERE id = " + str(id))
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
query = "SELECT * FROM produtos WHERE 1=1"
if termo:
    query += " AND nome LIKE '%" + termo + "%'"
```

**Depois**
```python
cursor.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,))
cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))   # senha conferida com hash — ver R4

# filtro dinâmico: monte a estrutura da query, nunca os valores
sql = "SELECT id, nome, preco FROM produtos WHERE 1=1"
params = []
if termo:
    sql += " AND (nome LIKE ? OR descricao LIKE ?)"
    params += [f"%{termo}%", f"%{termo}%"]
if categoria:
    sql += " AND categoria = ?"
    params.append(categoria)
cursor.execute(sql, params)
```

O que pode ser concatenado: **estrutura** (nome de coluna vindo de allowlist, `ORDER BY` validado).
O que nunca pode: **valor** vindo do cliente. Em ORM, `filter(Model.campo == valor)` já parametriza;
`text()` com f-string não.

---

## R3 — Serializador explícito sem campos sensíveis

**Resolve:** A4 Sensitive Data Exposure, E1/E4 duplicação e inconsistência de resposta.

**Antes**
```python
# models.py — repetido em 4 funções, e devolve a senha
result.append({"id": row["id"], "nome": row["nome"], "email": row["email"],
               "senha": row["senha"], "tipo": row["tipo"]})
```

**Depois**
```python
# src/models/usuario_model.py
CAMPOS_PUBLICOS = ("id", "nome", "email", "tipo", "criado_em")

def _serializar(row):
    """Converte uma linha do banco no contrato público da entidade. Senha nunca sai daqui."""
    return {campo: row[campo] for campo in CAMPOS_PUBLICOS}
```

Um único mapeador por entidade; a coluna sensível não aparece na lista. Se algum consumidor
interno precisa do hash, ele usa um método dedicado (`buscar_credencial`), não o serializador.

---

## R4 — Hash de senha forte com comparação em tempo constante

**Resolve:** A5 Weak/Absent Password Hashing.

**Antes**
```python
cursor.execute("INSERT INTO usuarios (senha) VALUES ('" + senha + "')")   # texto plano
```
```javascript
function badCrypto(pwd) {                    // hash caseiro
    let hash = "";
    for (let i = 0; i < 10000; i++) hash += Buffer.from(pwd).toString('base64').substring(0, 2);
    return hash.substring(0, 10);
}
```

**Depois**
```python
# src/models/usuario_model.py
from werkzeug.security import generate_password_hash, check_password_hash

def criar(self, nome, email, senha, tipo="cliente"):
    senha_hash = generate_password_hash(senha)          # PBKDF2 com salt por usuário
    self._db.execute("INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                     (nome, email, senha_hash, tipo))

def autenticar(self, email, senha):
    row = self._db.query_one("SELECT * FROM usuarios WHERE email = ?", (email,))
    if row is None or not check_password_hash(row["senha"], senha):
        return None                                      # mesma resposta para os dois casos
    return _serializar(row)
```
```javascript
const bcrypt = require('bcrypt');
const hash = await bcrypt.hash(senha, 10);
const ok   = await bcrypt.compare(senha, usuario.pass);
```

Nunca `==` entre hashes calculados manualmente — use o `check`/`compare` da biblioteca, que compara
em tempo constante. Não diga ao cliente *qual* dos dois campos falhou.

---

## R5 — Middleware de autenticação e autorização

**Resolve:** A6 Missing Authentication, A8 Fake Token.

**Antes**
```python
return jsonify({"token": "fake-jwt-token-" + str(user.id)}), 200   # previsível
@app.route("/admin/reset-db", methods=["POST"])                    # aberto a qualquer cliente
```

**Depois**
```python
# src/middlewares/auth.py
from functools import wraps
from flask import request, g
import jwt
from src.config.settings import settings
from src.middlewares.errors import NaoAutorizado, Proibido

def gerar_token(usuario):
    payload = {"sub": usuario["id"], "tipo": usuario["tipo"],
               "exp": datetime.now(timezone.utc) + timedelta(hours=settings.TOKEN_TTL_HORAS)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def requer_autenticacao(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise NaoAutorizado("Token ausente")
        try:
            g.usuario = jwt.decode(header[7:], settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            raise NaoAutorizado("Token inválido") from exc
        return fn(*args, **kwargs)
    return wrapper

def requer_papel(papel):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if g.usuario.get("tipo") != papel:
                raise Proibido("Permissão insuficiente")
            return fn(*args, **kwargs)
        return wrapper
    return decorator
```
```python
# src/views/routes.py
bp.add_url_rule("/admin/reset-db", view_func=requer_autenticacao(requer_papel("admin")(admin_ctrl.reset)), methods=["POST"])
```

Quando adicionar autenticação muda o contrato de endpoints já existentes, isso é uma decisão do
usuário: proponha na Fase 2 e destaque no resumo da Fase 3.

---

## R6 — Decompor God Class por domínio

**Resolve:** B1 God Class, B2 God Method.

**Antes** — `AppManager.js` (141 linhas) com conexão, DDL, seed, rotas, pagamento, relatório.

**Depois**
```
src/
├── config/settings.js          # porta, chaves, caminho do banco
├── database/connection.js      # cria a conexão e expõe run/get/all promisificados
├── database/schema.js          # DDL + seed, chamados só no bootstrap
├── models/courseModel.js       # SELECT/INSERT de cursos
├── models/userModel.js
├── models/enrollmentModel.js
├── models/paymentModel.js
├── controllers/checkoutController.js   # o caso de uso "matricular e cobrar"
├── controllers/reportController.js
├── views/routes.js             # só o mapa rota → controller
├── middlewares/errorHandler.js
├── services/paymentGateway.js  # a integração externa isolada
└── app.js                      # composition root
```

Roteiro: (1) liste as responsabilidades do arquivo; (2) agrupe por entidade de domínio; (3) extraia
primeiro a camada mais interna (models) — ela não depende de ninguém; (4) só então mova o caso de
uso para o controller; (5) apague o arquivo original **depois** que a validação passar.

---

## R7 — Mover regra de negócio do controller para o model

**Resolve:** B3 Business Logic in Controller.

**Antes**
```python
# controllers.py — o controller decide a regra de desconto e dispara notificações
desconto = 0
if faturamento > 10000:  desconto = faturamento * 0.1
elif faturamento > 5000: desconto = faturamento * 0.05
print("ENVIANDO EMAIL: Pedido criado")
```

**Depois**
```python
# src/models/pedido_model.py
FAIXAS_DESCONTO = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))

def calcular_desconto(faturamento):
    """Regra de negócio: desconto progressivo por faixa de faturamento."""
    for piso, taxa in FAIXAS_DESCONTO:
        if faturamento > piso:
            return round(faturamento * taxa, 2)
    return 0.0
```
```python
# src/controllers/pedido_controller.py — orquestra, não decide
def criar(self):
    dados = request.get_json() or {}
    self._validador.validar_pedido(dados)
    pedido = self._pedidos.criar(dados["usuario_id"], dados["itens"])
    self._notificador.pedido_criado(pedido)
    return jsonify({"dados": pedido, "sucesso": True}), 201
```

Teste da separação: a regra continua funcionando chamada de um script CLI, sem HTTP? Se não,
ela ainda está no lugar errado.

---

## R8 — Isolar acesso a dados em model/repositório

**Resolve:** B4 Data Access in Controller, C6 Connection Mismanagement.

**Antes**
```python
# controllers.py — o handler abre cursor e escreve SQL
def health_check():
    db = get_db(); cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM produtos")
```

**Depois**
```python
# src/models/base_model.py — todo model herda o acesso parametrizado
class BaseModel:
    def __init__(self, db):
        self._db = db                       # injetado: testável com um fake

    def query_all(self, sql, params=()):
        return [dict(r) for r in self._db.execute(sql, params).fetchall()]

    def query_one(self, sql, params=()):
        row = self._db.execute(sql, params).fetchone()
        return dict(row) if row else None
```
```python
# src/controllers/health_controller.py
def check(self):
    return jsonify({"status": "ok", "counts": self._stats.contagens()}), 200
```

Depois desta transformação, `grep -rn "execute(" src/controllers src/views` tem de voltar vazio.

---

## R9 — Application factory / composition root

**Resolve:** B6 No Composition Root, B9 Tight Coupling.

**Antes**
```python
app = Flask(__name__)
app.add_url_rule("/produtos", "listar_produtos", controllers.listar_produtos, methods=["GET"])
# ... 18 registros manuais, dependências resolvidas por import global
```

**Depois**
```python
# src/app.py
from flask import Flask
from flask_cors import CORS
from src.config.settings import settings
from src.database.connection import criar_conexao
from src.models.produto_model import ProdutoModel
from src.controllers.produto_controller import ProdutoController
from src.views.routes import registrar_rotas
from src.middlewares.error_handler import registrar_error_handler

def create_app(db=None):
    """Composition root: cria as dependências concretas e as conecta."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    CORS(app, origins=settings.CORS_ORIGINS)

    conexao = db or criar_conexao(settings.DB_PATH)
    controllers = {"produto": ProdutoController(ProdutoModel(conexao))}

    registrar_rotas(app, controllers)
    registrar_error_handler(app)
    return app

if __name__ == "__main__":
    create_app().run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
```

O parâmetro `db=None` é o que permite `create_app(db=conexao_em_memoria)` num teste.

---

## R10 — Error handler centralizado com exceções de domínio

**Resolve:** B7 Missing Centralized Error Handling, F5 Silent Exception Swallowing, E4 Inconsistent Response.

**Antes**
```python
# repetido em 16 funções
try:
    ...
except Exception as e:
    return jsonify({"erro": str(e)}), 500      # vaza detalhe interno
```

**Depois**
```python
# src/middlewares/errors.py
class ErroDominio(Exception):
    status = 400
    def __init__(self, mensagem): super().__init__(mensagem); self.mensagem = mensagem

class NaoEncontrado(ErroDominio):    status = 404
class DadosInvalidos(ErroDominio):   status = 400
class NaoAutorizado(ErroDominio):    status = 401
class Proibido(ErroDominio):         status = 403
class Conflito(ErroDominio):         status = 409
```
```python
# src/middlewares/error_handler.py
import logging
log = logging.getLogger(__name__)

def registrar_error_handler(app):
    @app.errorhandler(ErroDominio)
    def _dominio(exc):
        return jsonify({"erro": exc.mensagem, "sucesso": False}), exc.status

    @app.errorhandler(Exception)
    def _inesperado(exc):
        log.exception("Erro não tratado")                 # detalhe vai para o log...
        return jsonify({"erro": "Erro interno", "sucesso": False}), 500   # ...não para o cliente
```
```python
# no model, em vez de devolver {"erro": ...}
if produto is None:
    raise NaoEncontrado(f"Produto {produto_id} não encontrado")
```

Depois disso, remova os `try/except` genéricos dos controllers: eles só escondem o handler central.
Mantenha `try/except` estreito onde há tratamento real (rollback de transação, fallback).

---

## R11 — Remover endpoint perigoso

**Resolve:** A3 Arbitrary Query/Command Execution.

**Antes**
```python
@app.route("/admin/query", methods=["POST"])
def executar_query():
    cursor.execute(request.get_json().get("sql", ""))    # SQL do cliente, direto no banco
```

**Depois** — o endpoint deixa de existir. A necessidade legítima vira comando de manutenção:
```python
# scripts/manutencao.py — roda no servidor, autenticado pelo acesso ao shell
if __name__ == "__main__":
    conexao = criar_conexao(settings.DB_PATH)
    ProdutoModel(conexao).recontar_estoque()
```
Se o endpoint precisar continuar existindo por decisão do usuário, ele fica: autenticado, restrito
a papel `admin`, com allowlist de comandos e log de auditoria — nunca SQL livre.
**Registre a remoção no resumo da Fase 3**: é a única mudança de contrato permitida.

---

## R12 — Eliminar estado global mutável

**Resolve:** B8 Global Mutable State, C6 Connection Mismanagement.

**Antes**
```python
db_connection = None                 # conexão única entre threads
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect(db_path, check_same_thread=False)
    return db_connection
```
```javascript
let globalCache = {};                // cresce sem limite, compartilhado entre requisições
let totalRevenue = 0;
```

**Depois**
```python
# src/database/connection.py
def criar_conexao(caminho):
    """Uma conexão por processo/worker, criada pelo composition root — não por import."""
    conexao = sqlite3.connect(caminho, check_same_thread=False)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao
```
```javascript
// cache com limite e TTL, instanciado e injetado — não um objeto de módulo
class Cache {
  constructor({ maxEntries = 500, ttlMs = 60_000 } = {}) { this.map = new Map(); ... }
}
```

Acumuladores (`totalRevenue`) somem: o valor vem de `SUM()` no banco, que é a fonte da verdade.

---

## R13 — Injeção de dependência

**Resolve:** B9 Tight Coupling.

**Antes**
```python
class NotificationService:
    def __init__(self):
        self.email_host = 'smtp.gmail.com'      # infraestrutura fixa no construtor
        self.email_password = '<redacted>'
    def send_email(self, to, subject, body):
        server = smtplib.SMTP(self.email_host, self.email_port)
```

**Depois**
```python
# src/services/notification_service.py
class NotificationService:
    def __init__(self, config, transporte=None, logger=None):
        self._config = config
        self._transporte = transporte or SmtpTransporte(config)   # default de produção
        self._log = logger or logging.getLogger(__name__)

    def notificar_atribuicao(self, usuario, task):
        self._transporte.enviar(usuario.email, f"Nova task: {task.title}", _corpo(usuario, task))
```
```python
# no teste
servico = NotificationService(config, transporte=TransporteFake())   # sem rede
```

---

## R14 — Resolver N+1 e agregação em memória

**Resolve:** C1 N+1 Query, C2 Aggregation in Memory.

**Antes**
```python
for row in pedidos:                                  # 1 query
    cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"]))   # +N
    for item in itens:
        cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))  # +N*M
```

**Depois**
```python
# uma query com JOIN, agrupada em memória depois de trazer tudo de uma vez
sql = """
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
      FROM pedidos p
      LEFT JOIN itens_pedido i ON i.pedido_id = p.id
      LEFT JOIN produtos pr    ON pr.id = i.produto_id
     WHERE (? IS NULL OR p.usuario_id = ?)
     ORDER BY p.id
"""
pedidos = {}
for row in self.query_all(sql, (usuario_id, usuario_id)):
    pedido = pedidos.setdefault(row["id"], {**_cabecalho(row), "itens": []})
    if row["produto_id"] is not None:
        pedido["itens"].append(_item(row))
return list(pedidos.values())
```

Agregação: troque cinco `SELECT COUNT(*)` por um só.
```sql
SELECT COUNT(*) AS total, COALESCE(SUM(total), 0) AS faturamento,
       SUM(status = 'pendente') AS pendentes,
       SUM(status = 'aprovado') AS aprovados
  FROM pedidos
```
Em ORM: `selectinload`/`joinedload` (SQLAlchemy), `include` (Prisma/Sequelize), `select_related`
(Django) — e `func.count()` em vez de `len(query.all())`.

---

## R15 — Paginação em listagens

**Resolve:** C3 Missing Pagination.

**Antes**
```python
cursor.execute("SELECT * FROM produtos")     # a tabela inteira, sempre
```

**Depois**
```python
PAGINA_PADRAO, TAMANHO_PADRAO, TAMANHO_MAXIMO = 1, 20, 100

def listar(self, pagina=PAGINA_PADRAO, tamanho=TAMANHO_PADRAO):
    tamanho = min(max(int(tamanho), 1), TAMANHO_MAXIMO)
    offset = (max(int(pagina), 1) - 1) * tamanho
    itens = self.query_all("SELECT * FROM produtos LIMIT ? OFFSET ?", (tamanho, offset))
    total = self.query_one("SELECT COUNT(*) AS n FROM produtos")["n"]
    return {"itens": itens, "pagina": pagina, "tamanho": tamanho, "total": total}
```

**Cuidado com o contrato**: se a resposta atual é um array cru, mudar para envelope quebra clientes.
Nesse caso, mantenha o formato e aceite `?page=` opcional (sem parâmetro = comportamento atual),
ou registre a mudança como decisão explícita no resumo.

---

## R16 — Integridade referencial na deleção

**Resolve:** C4 Referential Integrity Ignored.

**Antes**
```javascript
this.db.run("DELETE FROM users WHERE id = ?", [id], (err) => {
    res.send("Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.");
});
```

**Depois**
```javascript
// models/userModel.js — transação: ou tudo, ou nada
async remover(id) {
  await this.db.run('BEGIN');
  try {
    const matriculas = await this.db.all('SELECT id FROM enrollments WHERE user_id = ?', [id]);
    for (const m of matriculas) await this.db.run('DELETE FROM payments WHERE enrollment_id = ?', [m.id]);
    await this.db.run('DELETE FROM enrollments WHERE user_id = ?', [id]);
    const r = await this.db.run('DELETE FROM users WHERE id = ?', [id]);
    await this.db.run('COMMIT');
    return r.changes > 0;
  } catch (erro) {
    await this.db.run('ROLLBACK');
    throw erro;
  }
}
```

Alternativas igualmente válidas: `FOREIGN KEY ... ON DELETE CASCADE` no schema (com
`PRAGMA foreign_keys = ON` no SQLite), ou soft delete. Recusar com `409` também é resposta legítima
— o inaceitável é deixar órfão silencioso.

---

## R17 — Promisificar callbacks e usar async/await

**Resolve:** C5 Callback Hell, contadores manuais de concorrência.

**Antes**
```javascript
this.db.all("SELECT * FROM courses", [], (err, courses) => {
  let coursesPending = courses.length;
  courses.forEach(c => {
    this.db.all("SELECT * FROM enrollments WHERE course_id = ?", [c.id], (err, enrs) => {
      let enrPending = enrs.length;
      enrs.forEach(e => { /* 2 níveis a mais, e um contador manual para saber quando responder */ });
    });
  });
});
```

**Depois**
```javascript
// database/connection.js — a API callback vira promise uma única vez
const { promisify } = require('util');
function criarConexao(caminho) {
  const db = new sqlite3.Database(caminho);
  return {
    run: promisify(db.run.bind(db)),
    get: promisify(db.get.bind(db)),
    all: promisify(db.all.bind(db)),
    close: promisify(db.close.bind(db)),
  };
}
```
```javascript
// controllers/reportController.js — sequencial na leitura, paralelo onde é seguro
async relatorioFinanceiro(req, res, next) {
  try {
    const cursos = await this.cursos.listar();
    const relatorio = await Promise.all(cursos.map(async (curso) => {
      const alunos = await this.matriculas.listarComAlunoEPagamento(curso.id);   // uma query com JOIN
      return {
        course: curso.title,
        revenue: alunos.filter(a => a.status === 'PAID').reduce((s, a) => s + a.amount, 0),
        students: alunos.map(a => ({ student: a.name ?? 'Unknown', paid: a.amount ?? 0 })),
      };
    }));
    res.json(relatorio);
  } catch (erro) { next(erro); }        // erro vai para o handler central
}
```

O contador manual (`pending--`) some junto: `Promise.all` já sabe quando terminou, e sem risco de
responder duas vezes.

---

## R18 — Transação em operação composta

**Resolve:** C6 (escrita parcial), race condition de check-then-act.

**Antes**
```python
for item in itens:                                   # verifica estoque...
    if produto["estoque"] < item["quantidade"]: return {"erro": "Estoque insuficiente"}
cursor.execute("INSERT INTO pedidos ...")            # ...e só depois escreve, sem transação
for item in itens:
    cursor.execute("UPDATE produtos SET estoque = estoque - ...")
```

**Depois**
```python
def criar(self, usuario_id, itens):
    with self._db:                                   # commit no sucesso, rollback na exceção
        total = 0
        for item in itens:
            produto = self.query_one("SELECT id, nome, preco, estoque FROM produtos WHERE id = ?",
                                     (item["produto_id"],))
            if produto is None:
                raise NaoEncontrado(f"Produto {item['produto_id']} não encontrado")
            if produto["estoque"] < item["quantidade"]:
                raise DadosInvalidos(f"Estoque insuficiente para {produto['nome']}")
            total += produto["preco"] * item["quantidade"]

        cur = self._db.execute("INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
                               (usuario_id, STATUS_PENDENTE, total))
        pedido_id = cur.lastrowid
        for item in itens:
            # baixa condicional: só decrementa se ainda houver estoque — fecha o check-then-act
            afetadas = self._db.execute(
                "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                (item["quantidade"], item["produto_id"], item["quantidade"])).rowcount
            if afetadas == 0:
                raise DadosInvalidos("Estoque alterado durante o pedido")
    return {"pedido_id": pedido_id, "total": total}
```

---

## R19 — Substituir API deprecated

**Resolve:** D1 Deprecated API, D2 Outdated Dependency.

| Antes | Depois | Motivo |
|---|---|---|
| `datetime.utcnow()` | `datetime.now(timezone.utc)` | deprecated no Python 3.12; `utcnow()` devolve datetime *naive* |
| `Model.query.get(id)` | `db.session.get(Model, id)` | `Query.get()` é legado no SQLAlchemy 2.x |
| `Model.query.filter_by(...)` | `db.session.execute(db.select(Model).filter_by(...)).scalars()` | API 2.0 |
| `@app.before_first_request` | inicialização no factory | removido no Flask 2.3 |
| `new Buffer(x)` | `Buffer.from(x)` | removido no Node 10+ |
| `app.use(bodyParser.json())` | `app.use(express.json())` | embutido desde o Express 4.16 |
| `crypto.createCipher` | `crypto.createCipheriv` | inseguro, deprecated |
| `url.parse()` | `new URL()` | API legada |

**Antes / Depois (o caso mais comum em Flask+SQLAlchemy)**
```python
created_at = db.Column(db.DateTime, default=datetime.utcnow)          # naive, deprecated
task = Task.query.get(task_id)
```
```python
created_at = db.Column(db.DateTime(timezone=True),
                       default=lambda: datetime.now(timezone.utc))    # aware
task = db.session.get(Task, task_id)
```

Cuidado: trocar naive por aware muda comparações de data. Ajuste **todas** as comparações do
projeto na mesma passada (`t.due_date < datetime.now(timezone.utc)`) e revalide os endpoints
que usam data — é o ponto onde essa transformação costuma quebrar em silêncio.

---

## R20 — Extrair validação e serialização duplicadas

**Resolve:** E1 Duplicated Code, E2 Duplicated Validation.

**Antes** — o mesmo bloco de 20 linhas em `criar_produto` e `atualizar_produto`; a mesma lista de
status válidos em três arquivos.

**Depois**
```python
# src/models/produto_model.py — a regra vive junto da entidade
CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")
NOME_MIN, NOME_MAX = 2, 200

def validar_payload(dados, obrigatorios=("nome", "preco", "estoque")):
    for campo in obrigatorios:
        if campo not in dados:
            raise DadosInvalidos(f"{campo.capitalize()} é obrigatório")
    if not (NOME_MIN <= len(dados["nome"]) <= NOME_MAX):
        raise DadosInvalidos("Nome deve ter entre 2 e 200 caracteres")
    if dados["preco"] < 0 or dados["estoque"] < 0:
        raise DadosInvalidos("Preço e estoque não podem ser negativos")
    if dados.get("categoria", "geral") not in CATEGORIAS_VALIDAS:
        raise DadosInvalidos(f"Categoria inválida. Válidas: {list(CATEGORIAS_VALIDAS)}")
    return dados
```

Antes de extrair, confirme que os blocos são mesmo equivalentes — em código legado, "quase iguais"
costuma esconder uma diferença intencional (o `update` que não valida categoria pode ser bug ou
regra). Preserve o comportamento observável; se for bug, corrija e registre no resumo.

---

## R21 — Constantes nomeadas, guard clauses e nomes de domínio

**Resolve:** F1 Magic Numbers, F2 Poor Naming, F3 Boolean Return, F6 Deep Nesting.

**Antes**
```javascript
let u = req.body.usr, e = req.body.eml, p = req.body.pwd, cid = req.body.c_id, cc = req.body.card;
let status = cc.startsWith("4") ? "PAID" : "DENIED";
```
```python
def is_admin(self):
    if self.role == 'admin': return True
    else: return False
```

**Depois**
```javascript
const { usr: nome, eml: email, pwd: senha, c_id: cursoId, card: cartao } = req.body;
const status = gateway.autorizar(cartao) ? PagamentoStatus.PAGO : PagamentoStatus.RECUSADO;
```
```python
PAPEL_ADMIN = "admin"

def is_admin(self):
    return self.role == PAPEL_ADMIN
```

Guard clause no lugar de aninhamento:
```python
# antes: 3 níveis de if
if self.due_date:
    if self.due_date < agora:
        if self.status not in (STATUS_CONCLUIDA, STATUS_CANCELADA):
            return True
    ...
# depois
def esta_atrasada(self):
    if self.due_date is None or self.status in (STATUS_CONCLUIDA, STATUS_CANCELADA):
        return False
    return self.due_date < datetime.now(timezone.utc)
```

---

## R22 — Logging estruturado no lugar de print/console.log

**Resolve:** F4 print as Logging, A4 quando o print contém dado sensível.

**Antes**
```python
print("Login bem-sucedido: " + email)
```
```javascript
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);  // PAN + chave no log
```

**Depois**
```python
# src/config/logging.py
import logging
def configurar_logging(nivel="INFO"):
    logging.basicConfig(level=nivel, format="%(asctime)s %(levelname)s %(name)s %(message)s")
```
```python
log = logging.getLogger(__name__)
log.info("login bem-sucedido", extra={"usuario_id": usuario["id"]})   # id, não e-mail
```
```javascript
logger.info('checkout iniciado', { cursoId, cartaoFinal: cartao.slice(-4) });  // nunca o PAN
```

Regra: nunca logar senha, hash, token, chave, número de cartão completo ou e-mail em texto —
use identificador interno ou máscara.

---

## Checklist de verificação após aplicar o playbook

```bash
grep -rn "execute(\|query(" src/controllers src/views      # vazio: SQL só nos models
grep -rn "request\|jsonify\|res\." src/models              # vazio: model não conhece HTTP
grep -rniE "secret|password|api_key" src/ --include='*.py' --include='*.js' | grep -v config
grep -rn "print(\|console\.log(" src/                      # só no entry point, se tanto
grep -rn "except Exception\|catch (e) {}" src/controllers  # o handler central já cobre
grep -rn "global \|let cache" src/                         # sem estado global mutável
```
