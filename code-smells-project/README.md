# code-smells-project

API de E-commerce em Python/Flask — **refatorada para MVC** pela skill `refactor-arch`.

## Como rodar

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env        # ajuste os valores; o .env não é versionado
.venv/bin/python app.py
```

A aplicação sobe em `http://localhost:5000` (configurável por `HOST`/`PORT`). O banco SQLite
(`loja.db`) é criado no primeiro boot com schema, índices e dados de exemplo — as senhas do seed
entram no banco já com hash.

## Estrutura

```
app.py                       entry point (chama a application factory)
src/
├── config/
│   ├── settings.py          configuração por variável de ambiente
│   └── logging_config.py    logging estruturado
├── database/
│   ├── connection.py        factory de conexão (sem estado global)
│   └── schema.py            DDL com constraints/índices + carga inicial
├── models/                  dados + regra de negócio, queries parametrizadas
│   ├── base_model.py
│   ├── produto_model.py
│   ├── usuario_model.py
│   ├── pedido_model.py
│   └── relatorio_model.py
├── controllers/             orquestração por caso de uso, sem SQL
│   ├── produto_controller.py
│   ├── usuario_controller.py
│   ├── pedido_controller.py
│   ├── relatorio_controller.py
│   └── health_controller.py
├── views/routes.py          mapa rota → controller
├── middlewares/
│   ├── errors.py            exceções de domínio
│   ├── error_handler.py     tratamento centralizado
│   └── auth.py              token assinado + decorators de autenticação/papel
├── services/notificador.py  notificação isolada atrás de uma interface
└── app.py                   composition root (create_app)
```

## Endpoints

Os 17 endpoints de negócio da versão original respondem com o mesmo método, rota e status.

`GET /` · `GET /health` · `GET /produtos` · `GET /produtos/busca` · `GET /produtos/<id>` ·
`POST /produtos` · `PUT /produtos/<id>` · `DELETE /produtos/<id>` · `GET /usuarios` ·
`GET /usuarios/<id>` · `POST /usuarios` · `POST /login` · `POST /pedidos` · `GET /pedidos` ·
`GET /pedidos/usuario/<id>` · `PUT /pedidos/<id>/status` · `GET /relatorios/vendas`

**Removidos por serem indefensáveis** (documentado no relatório de auditoria):
`POST /admin/query` (executava SQL arbitrário enviado pelo cliente) e `POST /admin/reset-db`
(apagava o banco sem autenticação).

## Validando a refatoração

```bash
PORT=5001 .venv/bin/python app.py &
.venv/bin/python tools/wait_up.py http://127.0.0.1:5001/health
.venv/bin/python tools/smoke.py tools/endpoints.json /tmp/depois.json
```

`tools/compare.py <antes.json> <depois.json>` compara duas execuções e falha se algum status
divergir.

## Auditoria

O relatório completo desta refatoração está em [`../reports/audit-project-1.md`](../reports/audit-project-1.md).
