================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python 3 + Flask 3.0.0 (Flask-SQLAlchemy 3.1.1)
Files:   15 analyzed | 1158 lines of code
Date:    2026-08-29

## Phase 1 — Project Analysis

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3 (ambiente 3.14.6)
Framework:     Flask 3.0.0 + Flask-SQLAlchemy 3.1.1
Dependencies:  flask-cors 4.0.0, marshmallow 3.20.1 (declarada, não usada),
               requests 2.31.0 (declarada, não usada), python-dotenv 1.0.0 (declarada, não usada)
Domain:        Gerenciador de tarefas (tasks, usuários, categorias e relatórios de produtividade)
Architecture:  Camadas parciais — models/, routes/, services/ e utils/ existem, mas a regra de
               negócio e o acesso a dados vivem dentro das rotas; não há camada de controller
Source files:  15 files analyzed (1158 lines)
DB tables:     users, tasks, categories
Endpoints:     22 endpoints mapeados
================================
```

Observação da Fase 1: este é o projeto "parcialmente organizado" do conjunto. A estrutura de pastas
sugere separação de camadas, mas a auditoria mostra que ela é **nominal**: `routes/` concentra 733
das 1158 linhas e faz o trabalho de controller, model e serializador ao mesmo tempo, enquanto
`services/` e `utils/` são código morto.

## Summary

CRITICAL: 3 | HIGH: 8 | MEDIUM: 9 | LOW: 6

| Severidade | Qtd | Principais ocorrências |
|---|---|---|
| CRITICAL | 3 | Hardcoded Credentials, Sensitive Data Exposure (hash de senha na resposta), God Route Module |
| HIGH | 8 | Weak Password Hashing (MD5), Missing Authentication, Fake Token, Insecure Defaults, Business Logic in Route, Data Access in Route, Missing Configuration Layer, Tight Coupling |
| MEDIUM | 9 | Deprecated APIs, N+1 Query, Aggregation in Memory, Missing Pagination, Duplicated Code, Duplicated Validation, Missing Error Handler + Silent Exception Swallowing (achado único #18), Dead Code, Integridade referencial manual |
| LOW | 6 | Magic Numbers, print as Logging, Boolean Return, Deep Nesting, Unused Imports, dependências declaradas e não usadas |

## Findings

### #1 [CRITICAL] Hardcoded Credentials / Secrets

- **File:** `app.py:11-13`, `services/notification_service.py:7-10`
- **Evidence:**
  ```python
  app.config['SECRET_KEY'] = '<redacted>'
  self.email_user = 'taskmanager@gmail.com'
  self.email_password = '<redacted>'
  ```
- **Description:** A chave de assinatura da aplicação, a URI do banco e as credenciais completas de
  SMTP estão literais no código versionado. O projeto declara `python-dotenv` em
  `requirements.txt:6` mas não o utiliza em nenhum lugar.
- **Impact:** Qualquer pessoa com acesso ao repositório assina sessões válidas e envia e-mail em nome
  da aplicação. Como não há módulo de config, rotacionar exige alterar código.
- **Recommendation:** Módulo `config/settings.py` lendo variáveis de ambiente, com `.env.example`
  versionado sem valores reais (playbook: `R1`).

### #2 [CRITICAL] Sensitive Data Exposure — hash de senha na resposta

- **File:** `models/user.py:16-25` (linha 21), consumido em `routes/user_routes.py:33, 85, 129, 209`
- **Evidence:**
  ```python
  def to_dict(self):
      return {
          'id': self.id, 'name': self.name, 'email': self.email,
          'password': self.password,
  ```
- **Description:** O serializador da entidade `User` inclui a coluna `password`. Ele é devolvido
  diretamente em `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e — o pior caso — na resposta
  de `POST /login`.
- **Impact:** Quatro endpoints devolvem o hash MD5 de senha de qualquer usuário. Combinado com o
  achado #4 (MD5 sem salt), o hash exposto é quebrável em segundos por tabela arco-íris. Note que
  `GET /users` (linha 15-24) monta o dicionário à mão e **não** expõe a senha — a inconsistência
  mostra que o vazamento é acidental, fruto da duplicação do achado #12.
- **Recommendation:** Serializador com allowlist de campos públicos, sem a coluna de senha; método
  separado para uso interno se necessário (playbook: `R3`).

### #3 [CRITICAL] God Route Module — roteamento, regra, dados e serialização no mesmo arquivo

- **File:** `routes/task_routes.py:1-299`, `routes/user_routes.py:1-211`, `routes/report_routes.py:1-223`
- **Evidence:**
  ```python
  @task_bp.route('/tasks', methods=['GET'])
  def get_tasks():
      tasks = Task.query.all()            # acesso a dados
      task_data['overdue'] = True         # regra de negócio
      user = User.query.get(t.user_id)    # +N queries
      return jsonify(result), 200         # serialização manual
  ```
- **Description:** Os três módulos de rota somam 733 linhas (63% do projeto) e acumulam quatro
  responsabilidades: registro de rota, validação, consulta ao banco via ORM e montagem manual do
  payload. Não existe camada de controller nem de serviço — `services/` contém apenas código morto
  (achado #19). A separação de pastas é nominal.
- **Impact:** Nenhuma regra é testável sem subir o Flask e o banco; `get_tasks` (linhas 11-63)
  sozinha faz o trabalho de quatro camadas. Regras iguais divergiram entre arquivos justamente por
  isso (achados #12 e #13).
- **Recommendation:** Introduzir `controllers/` por domínio, mover consultas e regras para os models,
  e deixar as rotas apenas mapeando (playbook: `R6`, `R7`, `R8`).

### #4 [HIGH] Weak Password Hashing (MD5 sem salt)

- **File:** `models/user.py:27-32`
- **Evidence:**
  ```python
  def set_password(self, pwd):
      self.password = hashlib.md5(pwd.encode()).hexdigest()
  def check_password(self, pwd):
      return self.password == hashlib.md5(pwd.encode()).hexdigest()
  ```
- **Description:** MD5 sem salt, quebrado para uso criptográfico desde 2004, com comparação direta de
  strings (sem tempo constante). O comprimento mínimo de senha aceito é 4 (`user_routes.py:64`).
- **Impact:** Qualquer hash MD5 de senha comum é revertido por consulta a tabela pública. Como o hash
  ainda é devolvido na resposta (achado #2), a senha real do usuário é obtida sem sequer acessar o
  banco.
- **Recommendation:** `werkzeug.security.generate_password_hash`/`check_password_hash` (scrypt com
  salt) e mínimo de senha maior (playbook: `R4`).

### #5 [HIGH] Missing Authentication / Authorization

- **File:** `routes/user_routes.py:134-135`, `app.py:18-20`, e todas as demais rotas de `routes/`
- **Evidence:**
  ```python
  @user_bp.route('/users/<int:user_id>', methods=['DELETE'])
  def delete_user(user_id):
  ```
- **Description:** Nenhum dos 22 endpoints verifica identidade ou papel. Não existe decorator,
  `before_request` ou middleware de autenticação no projeto. `User.is_admin()`
  (`models/user.py:34-38`) foi escrito mas nunca é chamado.
- **Impact:** Qualquer cliente apaga usuários e suas tasks (`DELETE /users/<id>`), lê o relatório de
  produtividade de toda a equipe e altera tasks de terceiros. O papel `admin` existe no modelo, mas
  não protege nada.
- **Recommendation:** Middleware de autenticação por token assinado + verificação de papel nas rotas
  privilegiadas, usando o `is_admin` já modelado (playbook: `R5`).

### #6 [HIGH] Fake / Predictable Token

- **File:** `routes/user_routes.py:207-211`
- **Evidence:**
  ```python
  'token': 'fake-jwt-token-' + str(user.id)
  ```
- **Description:** O login devolve uma string previsível como token: sem assinatura, sem expiração,
  sem verificação em nenhum lugar do código.
- **Impact:** Basta trocar o número no fim da string para se passar por qualquer usuário — se algum
  cliente confiar nesse token, a escalada de privilégio é trivial.
- **Recommendation:** JWT assinado com o segredo vindo da config, com expiração, validado pelo
  middleware do achado #5 (playbook: `R5`).

### #7 [HIGH] Insecure Defaults (DEBUG + CORS + bind)

- **File:** `app.py:15, 34`
- **Evidence:**
  ```python
  CORS(app)
  app.run(debug=True, host='0.0.0.0', port=5000)
  ```
- **Description:** CORS liberado para qualquer origem, debug ligado e bind em todas as interfaces,
  sem que nenhuma dessas decisões venha de variável de ambiente.
- **Impact:** Com `debug=True` acessível na rede, o console do Werkzeug permite execução remota de
  código Python. O CORS aberto permite que qualquer site consuma a API em nome do usuário.
- **Recommendation:** Config por ambiente com defaults seguros (playbook: `R1`).

### #8 [HIGH] Business Logic in Route

- **File:** `routes/task_routes.py:30-39, 71-80, 96-124, 166-215, 283-296`, `routes/report_routes.py:30-68, 119-135`
- **Evidence:**
  ```python
  if t.due_date:
      if t.due_date < datetime.utcnow():
          if t.status != 'done' and t.status != 'cancelled':
              task_data['overdue'] = True
  ```
- **Description:** A regra "task atrasada", as faixas válidas de prioridade, a lista de status
  permitidos e o cálculo de taxa de conclusão estão escritos dentro dos handlers HTTP. `Task` já tem
  `is_overdue()`, `validate_status()` e `validate_priority()` (`models/task.py:38-60`) — **nenhum é
  chamado por rota alguma**.
- **Impact:** A mesma regra existe em duas versões (model e rota) que podem divergir sem que ninguém
  perceba; nada disso é testável sem HTTP. É exatamente o cenário que a camada de model deveria
  impedir.
- **Recommendation:** Rotas passam a chamar os métodos do model; a regra vive em um lugar só
  (playbook: `R7`, `R20`).

### #9 [HIGH] Data Access in Route

- **File:** `routes/task_routes.py:14, 42, 51, 67, 117, 158, 247-266, 275-281`, `routes/user_routes.py:12, 29, 35, 67, 94, 109, 136, 140, 159, 197`, `routes/report_routes.py:15-56, 109, 159, 163`
- **Evidence:**
  ```python
  tasks = Task.query.filter_by(user_id=user_id).all()
  ```
- **Description:** As rotas conversam diretamente com o ORM: mais de 40 chamadas de consulta
  espalhadas pelos três arquivos, incluindo montagem de filtros dinâmicos
  (`task_routes.py:247-266`).
- **Impact:** O modelo de dados vaza para a camada HTTP; qualquer mudança de schema obriga a
  reescrever rotas. Não há como reusar uma consulta entre endpoints — daí as duplicações do
  achado #12.
- **Recommendation:** Consultas descem para os models/repositórios, chamados pelos controllers
  (playbook: `R8`).

### #10 [HIGH] Missing Configuration Layer

- **File:** `app.py:9-20`
- **Evidence:**
  ```python
  app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
  ```
- **Description:** Toda a configuração está inline no entry point: URI do banco, segredo, CORS,
  host, porta e debug. Não há `config/`, não há `.env.example`, e `python-dotenv` está declarado mas
  não é importado.
- **Impact:** Um artefato por ambiente; impossível apontar para Postgres em produção sem editar
  código.
- **Recommendation:** `config/settings.py` por ambiente (playbook: `R1`).

### #11 [HIGH] Tight Coupling / No Composition Root

- **File:** `app.py:9-31`, `services/notification_service.py:5-10`
- **Evidence:**
  ```python
  app = Flask(__name__)      # instanciado em escopo de módulo
  with app.app_context():
      db.create_all()        # efeito colateral no import
  ```
- **Description:** A aplicação é criada em escopo de módulo, `db.create_all()` roda como efeito
  colateral de importar `app` e não existe `create_app()`. `NotificationService` instancia sua
  própria conexão SMTP com credenciais fixas no construtor, sem receber nada por injeção.
- **Impact:** Importar `app` em um teste já cria o banco em disco; não há como montar a aplicação com
  um banco em memória ou um transporte de e-mail falso.
- **Recommendation:** Application factory com dependências injetadas e transporte de e-mail
  parametrizável (playbook: `R9`, `R13`).

### #12 [MEDIUM] Deprecated APIs

- **File:** `models/task.py:15-16, 52`, `models/user.py:14`, `models/category.py:11`, `utils/helpers.py:38`, `routes/task_routes.py:31, 215, 285`, `routes/user_routes.py:172`, `routes/report_routes.py:35, 42, 45, 71, 133`, `seed.py:66-74`
- **Evidence:**
  ```python
  created_at = db.Column(db.DateTime, default=datetime.utcnow)
  user = User.query.get(t.user_id)
  ```
- **Description:** Duas famílias de API obsoleta convivem no projeto:
  `datetime.utcnow()` — deprecated desde o Python 3.12 — aparece em 17 pontos, e o padrão
  `Model.query` / `Query.get()` do SQLAlchemy 1.x é usado em todas as consultas, apesar de o projeto
  declarar Flask-SQLAlchemy 3.1.1 (assentado sobre SQLAlchemy 2.x), onde ele é legado.
- **Impact:** `utcnow()` devolve datetime *naive*: todas as comparações de atraso assumem
  implicitamente que o banco está em UTC e quebram silenciosamente se algum valor vier com fuso.
  `Query.get()` deve desaparecer em uma futura major do SQLAlchemy — o upgrade quebra a aplicação
  inteira de uma vez.
- **Recommendation:** `datetime.now(timezone.utc)` e `db.session.get(Model, pk)` /
  `db.session.execute(db.select(...))`, ajustando **todas** as comparações de data na mesma passada
  (playbook: `R19`).

### #13 [MEDIUM] N+1 Query

- **File:** `routes/task_routes.py:41-57`, `routes/user_routes.py:22`, `routes/report_routes.py:53-68, 163`
- **Evidence:**
  ```python
  for t in tasks:
      user = User.query.get(t.user_id)
      cat = Category.query.get(t.category_id)
  ```
- **Description:** `GET /tasks` faz uma query por task para o usuário e outra para a categoria.
  `GET /users` chama `len(u.tasks)` por usuário (lazy load = uma query cada).
  `GET /reports/summary` executa `Task.query.filter_by(user_id=...)` dentro do laço de usuários e
  `GET /categories` conta tasks por categoria em laço.
- **Impact:** 100 tasks = 201 queries em `GET /tasks`. O relatório cresce com usuários × tasks.
- **Recommendation:** `selectinload`/`joinedload` nos relacionamentos e `COUNT`/`GROUP BY` para as
  contagens (playbook: `R14`).

### #14 [MEDIUM] Aggregation in Application Memory

- **File:** `routes/report_routes.py:15-68`, `routes/task_routes.py:275-287`
- **Evidence:**
  ```python
  p1 = Task.query.filter_by(priority=1).count()
  ...
  p5 = Task.query.filter_by(priority=5).count()
  all_tasks = Task.query.all()
  for t in all_tasks:
  ```
- **Description:** `GET /reports/summary` dispara 13 queries de contagem (4 status + 5 prioridades +
  3 totais + recentes) e ainda carrega **todas** as tasks em memória para calcular atrasos.
  `GET /tasks/stats` repete o padrão com 5 contagens + varredura completa.
- **Impact:** O endpoint mais pesado da API cresce linearmente com a base e faz em 14 idas ao banco o
  que um `GROUP BY` resolve em uma.
- **Recommendation:** `GROUP BY status`, `GROUP BY priority` e filtro de atraso em SQL
  (playbook: `R14`).

### #15 [MEDIUM] Missing Pagination

- **File:** `routes/task_routes.py:14, 266`, `routes/user_routes.py:12, 159`, `routes/report_routes.py:159`
- **Evidence:**
  ```python
  tasks = Task.query.all()
  ```
- **Description:** As cinco listagens devolvem a tabela inteira, sem `limit`, `offset` ou cursor —
  inclusive a busca (`GET /tasks/search`), que é justamente o endpoint com maior potencial de
  resultado amplo.
- **Impact:** Resposta e uso de memória crescem sem limite. Uma das tasks do próprio seed do projeto
  se chama "Adicionar paginação na API" — o problema é conhecido e não tratado.
- **Recommendation:** `page`/`per_page` com teto, mantendo o comportamento atual quando ausentes
  (playbook: `R15`).

### #16 [MEDIUM] Duplicated Code — regra de atraso e serialização

- **File:** `models/task.py:50-59` × `routes/task_routes.py:30-39, 71-80, 283-287` ×
  `routes/user_routes.py:171-180` × `routes/report_routes.py:34-43, 132-135`
- **Evidence:**
  ```python
  if t.status != 'done' and t.status != 'cancelled':
  ```
- **Description:** O mesmo trio de `if` que decide se uma task está atrasada aparece **sete vezes**
  em cinco arquivos. A serialização de task é montada campo a campo em `task_routes.py:17-28` e
  `user_routes.py:162-169` apesar de `Task.to_dict()` existir; a de usuário em `user_routes.py:15-23`
  apesar de `User.to_dict()` existir.
- **Impact:** Uma mudança na definição de "atrasada" exige lembrar de sete lugares. Foi a duplicação
  da serialização que produziu o vazamento de senha do achado #2 em quatro rotas e não em outra.
- **Recommendation:** Chamar `Task.is_overdue()` e os serializadores dos models; apagar as cópias
  (playbook: `R20`, `R3`).

### #17 [MEDIUM] Duplicated Validation

- **File:** `routes/task_routes.py:96-124` × `routes/task_routes.py:166-213`,
  `routes/user_routes.py:54-72` × `routes/user_routes.py:102-125`, `utils/helpers.py:57-108`
- **Evidence:**
  ```python
  if status not in ['pending', 'in_progress', 'done', 'cancelled']:
  ```
- **Description:** Cada par create/update repete a validação com mensagens ligeiramente diferentes
  ("Título muito curto" nas duas, mas o create também rejeita título ausente e o update não).
  A lista de status válidos é escrita literalmente em 5 pontos, embora `VALID_STATUSES` exista em
  `utils/helpers.py:110`. O validador completo `process_task_data` (linhas 57-108) foi escrito e
  nunca é chamado.
- **Impact:** Contratos divergentes para a mesma entidade; a fonte da verdade da validação não existe.
- **Recommendation:** Um validador por entidade, na camada de domínio, usado pelos dois casos de uso
  (playbook: `R20`).

### #18 [MEDIUM] Missing Centralized Error Handling + Silent Exception Swallowing

- **File:** `routes/task_routes.py:62, 137, 204, 236`, `routes/user_routes.py:130, 149`,
  `routes/report_routes.py:186, 207, 221`, `utils/helpers.py:46, 49, 88`
- **Evidence:**
  ```python
  except:
      return jsonify({'error': 'Erro interno'}), 500
  ```
- **Description:** Doze blocos `except:` nus — que capturam inclusive `KeyboardInterrupt` e
  `SystemExit` — devolvendo mensagem genérica sem nenhum log. Não há `errorhandler` registrado na
  aplicação; cada rota repete seu próprio `try/except`.
- **Impact:** Qualquer falha vira "Erro interno" sem rastro: um bug de produção é indiagnosticável.
  Em `task_routes.py:62`, o `except` engole o erro de uma listagem inteira.
- **Recommendation:** Error handler central com exceções de domínio tipadas e log estruturado;
  remover os `try/except` genéricos das rotas (playbook: `R10`).

### #19 [MEDIUM] Dead Code

- **File:** `services/notification_service.py:1-48`, `utils/helpers.py:1-116`,
  `routes/report_routes.py:7`
- **Evidence:**
  ```python
  from utils.helpers import format_date, calculate_percentage   # report_routes.py:7 — nunca chamados
  ```
- **Description:** `NotificationService` (48 linhas, com credencial SMTP hardcoded) não é importado
  em lugar nenhum. De `utils/helpers.py`, nenhuma das nove funções é chamada de fora do próprio
  arquivo: `format_date` e `calculate_percentage` são importados em `report_routes.py:7` e nunca
  usados; `process_task_data`, `validate_email`, `sanitize_string`, `generate_id`, `log_action` e
  `is_valid_color` não têm um único uso. As seis constantes das linhas 110-116 também não.
- **Impact:** 164 linhas (14% do projeto) que aparentam separação de camadas mas não participam da
  execução — inclusive carregando um segredo hardcoded. A auditoria de segurança precisa tratá-las
  mesmo assim, porque estão versionadas.
- **Recommendation:** Ou integrar (o validador de `helpers` resolveria o achado #17, o serviço de
  notificação teria uso real) ou remover. Deixar como está é o pior dos dois mundos.

### #20 [MEDIUM] Integridade referencial tratada à mão

- **File:** `routes/user_routes.py:134-151`
- **Evidence:**
  ```python
  tasks = Task.query.filter_by(user_id=user_id).all()
  for t in tasks:
      db.session.delete(t)
  ```
- **Description:** A deleção de usuário apaga as tasks uma a uma no laço, sem `cascade` declarado no
  relacionamento (`models/task.py:20-21`) e sem transação explícita. `DELETE /categories/<id>`
  (`report_routes.py:211-223`) não faz nem isso: apaga a categoria e deixa as tasks apontando para
  um ID inexistente.
- **Impact:** Deletar categoria produz tasks com `category_id` órfão — `GET /tasks` passa a devolver
  `category_name: null` sem explicação. A deleção de usuário destrói o histórico de tasks quando
  desativar o usuário seria o esperado.
- **Recommendation:** `cascade='all, delete-orphan'` ou `ondelete` no relacionamento, dentro de
  transação; para categoria, recusar com `409` ou desassociar explicitamente (playbook: `R16`).

### #21 [LOW] Magic Numbers e Magic Strings

- **File:** `routes/task_routes.py:96-114, 110, 177, 182`, `routes/user_routes.py:64, 71`,
  `routes/report_routes.py:84-88, 180`, `models/task.py:12, 39, 46`
- **Evidence:**
  ```python
  if priority < 1 or priority > 5:
  if len(password) < 4:
  ```
- **Description:** Faixas de prioridade, limites de título (3/200), tamanho mínimo de senha, cor
  padrão `'#000000'` e os rótulos de prioridade (`critical`, `high`, `medium`...) aparecem como
  literais soltos. As constantes equivalentes existem em `utils/helpers.py:110-116` e são ignoradas.
- **Impact:** Alterar uma regra de validação exige caçar literais em quatro arquivos.
- **Recommendation:** Usar as constantes já existentes, movidas para a camada de domínio
  (playbook: `R21`).

### #22 [LOW] print as Logging

- **File:** `routes/task_routes.py:149, 153, 219, 234`, `routes/user_routes.py:83, 89, 147`,
  `services/notification_service.py:21, 24`, `utils/helpers.py:39, 41`, `seed.py:93-96`
- **Evidence:**
  ```python
  print(f"Erro ao criar task: {str(e)}")
  ```
- **Description:** Diagnóstico via `print`, sem nível nem timestamp. Em `user_routes.py:83` o nome do
  usuário criado vai para stdout.
- **Impact:** Impossível ajustar verbosidade por ambiente; o único registro de erros do projeto é
  texto solto em stdout.
- **Recommendation:** Logger com níveis (playbook: `R22`).

### #23 [LOW] Boolean Return Antipattern

- **File:** `models/user.py:34-38`, `models/task.py:38-48`
- **Evidence:**
  ```python
  def is_admin(self):
      if self.role == 'admin':
          return True
      else:
          return False
  ```
- **Description:** Três métodos devolvem `True`/`False` por ramificação explícita onde a própria
  expressão booleana bastaria.
- **Impact:** Legibilidade.
- **Recommendation:** `return self.role == PAPEL_ADMIN` (playbook: `R21`).

### #24 [LOW] Deep Nesting

- **File:** `models/task.py:50-59`, `routes/task_routes.py:30-39`, `routes/report_routes.py:33-43`
- **Evidence:**
  ```python
  if self.due_date:
      if self.due_date < datetime.utcnow():
          if self.status != 'done' and self.status != 'cancelled':
  ```
- **Description:** Três níveis de `if` aninhado com `else` explícito em cada nível, onde duas guard
  clauses resolveriam.
- **Impact:** Nove linhas para expressar uma condição de uma linha; é a forma em que a regra foi
  copiada sete vezes (achado #16).
- **Recommendation:** Guard clauses (playbook: `R21`).

### #25 [LOW] Unused Imports

- **File:** `app.py:7`, `routes/task_routes.py:7`, `routes/user_routes.py:6`,
  `routes/report_routes.py:8`, `models/task.py:3`, `utils/helpers.py:3-7`
- **Evidence:**
  ```python
  import os, sys, json, datetime
  import json, os, sys, time
  ```
- **Description:** Imports agregados nunca utilizados: `os`, `sys`, `json`, `time` nas rotas,
  `hashlib` em `user_routes.py`, `json` em `models/task.py`, e `os`, `json`, `sys`, `math`,
  `hashlib` em `helpers.py`. Em `app.py`, apenas `datetime` da linha 7 é usado.
- **Impact:** Ruído e falso sinal de dependência.
- **Recommendation:** Remover; um import por linha do que resta.

### #26 [LOW] Dependências declaradas e não usadas

- **File:** `requirements.txt:4-6`
- **Evidence:**
  ```
  marshmallow==3.20.1
  requests==2.31.0
  python-dotenv==1.0.0
  ```
- **Description:** Três dependências instaladas e nunca importadas. `marshmallow` resolveria o
  achado #17 e `python-dotenv` o achado #1 — as ferramentas certas foram escolhidas e esquecidas.
- **Impact:** Superfície de dependência maior que a necessária e falsa impressão de que validação e
  configuração por ambiente estão resolvidas.
- **Recommendation:** Usar (preferível) ou remover do manifesto.

## Deprecated APIs

Diferente dos outros dois projetos, aqui a detecção **produziu achados** (detalhados em #12):

| API | Arquivo:linha | Situação | Substituto |
|---|---|---|---|
| `datetime.utcnow()` | `models/task.py:15, 16, 52`; `models/user.py:14`; `models/category.py:11`; `utils/helpers.py:38`; `routes/task_routes.py:31, 215, 285`; `routes/user_routes.py:172`; `routes/report_routes.py:35, 42, 45, 71, 133`; `seed.py:66-74` | Deprecated no Python 3.12+ (17 ocorrências); devolve datetime *naive* | `datetime.now(timezone.utc)` |
| `Model.query.get(pk)` | `routes/task_routes.py:67, 117, 158`; `routes/user_routes.py:29, 94, 136, 155`; `routes/report_routes.py:109, 191, 213` | Legado no SQLAlchemy 2.x (Flask-SQLAlchemy 3.1.1) | `db.session.get(Model, pk)` |
| `Model.query.filter_by(...)` | 20+ ocorrências nos três módulos de rota | Estilo 1.x; a API 2.0 é `select()` | `db.session.execute(db.select(Model).filter_by(...))` |

## Endpoints inventariados (contrato da Fase 3)

| # | Método | Rota | Status baseline |
|---|---|---|---|
| 1 | GET | `/` | 200 |
| 2 | GET | `/health` | 200 |
| 3 | GET | `/tasks` | 200 |
| 4 | GET | `/tasks/<id>` | 200 / 404 |
| 5 | POST | `/tasks` | 201 / 400 / 404 |
| 6 | PUT | `/tasks/<id>` | 200 / 400 / 404 |
| 7 | DELETE | `/tasks/<id>` | 200 / 404 |
| 8 | GET | `/tasks/search` | 200 |
| 9 | GET | `/tasks/stats` | 200 |
| 10 | GET | `/users` | 200 |
| 11 | GET | `/users/<id>` | 200 / 404 |
| 12 | POST | `/users` | 201 / 400 / 409 |
| 13 | PUT | `/users/<id>` | 200 / 400 / 404 / 409 |
| 14 | DELETE | `/users/<id>` | 200 / 404 |
| 15 | GET | `/users/<id>/tasks` | 200 / 404 |
| 16 | POST | `/login` | 200 / 400 / 401 / 403 |
| 17 | GET | `/reports/summary` | 200 |
| 18 | GET | `/reports/user/<id>` | 200 / 404 |
| 19 | GET | `/categories` | 200 |
| 20 | POST | `/categories` | 201 / 400 |
| 21 | PUT | `/categories/<id>` | 200 / 404 |
| 22 | DELETE | `/categories/<id>` | 200 / 404 |

## Plano de refatoração proposto

Este projeto exige menos demolição e mais **completar a separação que já foi iniciada**:

1. **config/** — `settings.py` com URI, segredo, CORS, host, porta, debug e SMTP vindos do ambiente,
   usando o `python-dotenv` já declarado; `.env.example` (resolve #1, #7, #10, parte de #26).
2. **models/** — mover as consultas e a regra de negócio para os models existentes: `is_overdue`
   passa a ser a única definição de atraso, serializadores sem campo sensível, validadores como
   métodos de classe, APIs do SQLAlchemy 2.x e `datetime` com fuso
   (resolve #2, #4, #12, #13, #16, #17, #20).
3. **controllers/** — `task_controller`, `user_controller`, `category_controller`,
   `report_controller`: a camada que falta, com a orquestração hoje presa nas rotas
   (resolve #3, #8, #9).
4. **views/routes/** — os três blueprints ficam só com o mapa rota → controller, preservando as 22
   rotas (resolve #3).
5. **middlewares/** — error handler central com exceções de domínio, autenticação por JWT assinado e
   verificação de papel (resolve #5, #6, #18).
6. **services/** — `NotificationService` com transporte injetado e credenciais de config, integrado
   ao fluxo de atribuição de task (resolve #11 e metade de #19).
7. **utils/** — o que é útil vira validador de domínio usado de verdade; o resto é removido
   (resolve a outra metade de #19, e #21).
8. **app.py** — `create_app()` como composition root, sem efeito colateral no import (resolve #11).
9. Limpeza: paginação opcional, agregações em SQL, imports mortos, guard clauses, logger
   (resolve #14, #15, #22, #23, #24, #25).

================================
Total: 26 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
> y

## Phase 3 — Refatoração e validação

Confirmado. Camada de controller introduzida; rotas só mapeiam HTTP → controller. MD5 e `fake-jwt-token` substituídos; `datetime.utcnow()` e `Model.query.get()` removidos.

Findings resolved: 25/26  (CRITICAL 3/3 | HIGH 7/8 | MEDIUM 9/9 | LOW 6/6)

Aceito conscientemente: **#5 HIGH Missing Authentication** — JWT HMAC existe, mas `AUTH_REQUIRED=false` por padrão para não quebrar o contrato HTTP legado.

Validation
  ✓ Application boots without errors
  ✓ 41/41 endpoints respond with baseline parity
  ✓ Catalog scan: no new CRITICAL/HIGH introduced
  ✓ Remaining CRITICAL/HIGH: #5 HIGH Missing Authentication — aceito (AUTH_REQUIRED=false)
