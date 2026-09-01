# task-manager-api

API de Task Manager em Python/Flask — **refatorada para MVC** pela skill `refactor-arch`.

O projeto já vinha com `models/`, `routes/`, `services/` e `utils/`, mas a separação era nominal:
as rotas concentravam 63% do código e faziam o trabalho de controller, model e serializador ao
mesmo tempo, enquanto `services/` e `utils/` eram código morto. A refatoração completou a
separação em vez de recomeçá-la.

## Como rodar

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env      # ajuste os valores; o .env não é versionado
.venv/bin/python seed.py  # popula o banco (rode antes do primeiro boot)
.venv/bin/python app.py
```

A aplicação sobe em `http://localhost:5000` (configurável por `HOST`/`PORT`).

## Estrutura

```
app.py                        entry point (chama a application factory)
seed.py                       carga inicial
src/
├── config/
│   ├── settings.py           configuração por variável de ambiente (via python-dotenv)
│   └── logging_config.py     logging estruturado
├── database.py               instância do ORM
├── models/                   dados + regra de negócio + consultas da entidade
│   ├── user.py               (hash PBKDF2, papel, e-mail único)
│   ├── task.py               (is_overdue como única definição de atraso; agregações em SQL)
│   └── category.py
├── controllers/              orquestração por caso de uso, sem ORM direto
│   ├── task_controller.py
│   ├── user_controller.py
│   ├── category_controller.py
│   ├── report_controller.py
│   └── health_controller.py
├── views/                    blueprints com o mapa rota → controller
│   ├── task_routes.py
│   ├── user_routes.py
│   └── report_routes.py
├── middlewares/
│   ├── errors.py             exceções de domínio
│   ├── error_handler.py      tratamento centralizado (com rollback)
│   └── auth.py               token assinado + guards
├── services/
│   └── notification_service.py  transporte de e-mail injetado
├── utils/
│   ├── constants.py          constantes de domínio
│   └── validators.py         validação em um lugar só
└── app.py                    composition root (create_app)
```

## Endpoints

Os 22 endpoints originais respondem no mesmo método, rota e status.

Tasks: `GET /tasks` · `POST /tasks` · `GET /tasks/<id>` · `PUT /tasks/<id>` · `DELETE /tasks/<id>` ·
`GET /tasks/search` · `GET /tasks/stats`

Usuários: `GET /users` · `POST /users` · `GET /users/<id>` · `PUT /users/<id>` ·
`DELETE /users/<id>` · `GET /users/<id>/tasks` · `POST /login`

Relatórios e categorias: `GET /reports/summary` · `GET /reports/user/<id>` · `GET /categories` ·
`POST /categories` · `PUT /categories/<id>` · `DELETE /categories/<id>`

Infraestrutura: `GET /` · `GET /health`

**Mudança de corpo deliberada:** o campo `password` deixou de aparecer nas respostas.
O `token` do login é HMAC-SHA256 com expiração. `POST /users` sempre cria `role=user`
(ignora auto-promoção). Com `AUTH_REQUIRED=true`, as rotas (exceto cadastro, login e health)
exigem Bearer.

## Validando a refatoração

```bash
.venv/bin/python seed.py
.venv/bin/python app.py &
curl -s http://127.0.0.1:5000/tasks
curl -s http://127.0.0.1:5000/reports/summary
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/tasks/9999   # 404
```

Sem o `seed.py` o banco sobe vazio e as rotas por id respondem `404`. O inventário completo, com
os status esperados, está na seção "Endpoints inventariados" do relatório de auditoria.

## Auditoria

O relatório completo está em [`../reports/audit-project-3.md`](../reports/audit-project-3.md).
