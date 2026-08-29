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

**Mudança de corpo deliberada:** o campo `password` deixou de aparecer nas respostas de
`GET /users/<id>`, `POST /users`, `PUT /users/<id>` e `POST /login` — antes o hash da senha era
devolvido nesses quatro endpoints. O `token` do login passou a ser assinado com HMAC-SHA256 e tem
expiração, no lugar da string previsível `fake-jwt-token-<id>`.

## Validando a refatoração

```bash
PORT=5002 .venv/bin/python app.py &
.venv/bin/python tools/wait_up.py http://127.0.0.1:5002/health
.venv/bin/python tools/smoke.py tools/endpoints.json /tmp/depois.json
.venv/bin/python tools/compare.py /tmp/antes.json /tmp/depois.json
```

## Auditoria

O relatório completo está em [`../reports/audit-project-3.md`](../reports/audit-project-3.md).
