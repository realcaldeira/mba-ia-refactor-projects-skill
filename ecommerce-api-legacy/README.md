# ecommerce-api-legacy

LMS API (cursos, matrículas e checkout) em Node.js/Express — **refatorada para MVC** pela skill
`refactor-arch`.

## Como rodar

```bash
npm install
cp .env.example .env      # carregado no boot; SECRET_KEY vazio usa o default de desenvolvimento
npm start
```

A aplicação sobe em `http://localhost:3000` (configurável por `HOST`/`PORT`). O banco SQLite é em
memória por padrão (`DB_PATH=:memory:`) e carrega o seed no boot — a senha do usuário de exemplo
entra já com hash.

## Estrutura

```
src/
├── config/
│   ├── settings.js       configuração por variável de ambiente + validação de produção
│   └── logger.js         logger com níveis
├── database/
│   ├── connection.js     conexão promisificada + helper de transação
│   └── schema.js         DDL com constraints/índices + carga inicial
├── models/               acesso a dados por entidade, com queries parametrizadas
│   ├── userModel.js      (inclui remoção transacional com dependentes)
│   ├── courseModel.js
│   ├── enrollmentModel.js (relatório em uma consulta com JOIN)
│   ├── paymentModel.js
│   └── auditLogModel.js
├── controllers/          casos de uso em async/await, sem SQL
│   ├── checkoutController.js
│   ├── reportController.js
│   └── userController.js
├── views/routes.js       mapa rota → controller
├── middlewares/
│   ├── errors.js         exceções de domínio
│   ├── errorHandler.js   tratamento centralizado
│   ├── crypto.js         hash de senha com scrypt + salt
│   └── auth.js           token assinado + guards
├── services/
│   ├── paymentGateway.js integração de pagamento isolada
│   └── cache.js          cache com limite e TTL
└── app.js                composition root (buildApp) + listen
```

## Endpoints

Os 3 endpoints originais respondem no mesmo método, rota e status:

| Método | Rota |
|---|---|
| POST | `/api/checkout` |
| GET | `/api/admin/financial-report` |
| DELETE | `/api/users/:id` |

Exemplos de requisição em [`api.http`](api.http).

**Mudanças de comportamento deliberadas:** no checkout, um e-mail já cadastrado exige a senha
correta (`401` se não conferir). Matrícula duplicada no mesmo curso responde `409`. Conta nova
só é gravada depois do pagamento aprovado. `DELETE /api/users/:id` inexistente responde `404`.

Com `AUTH_REQUIRED=true`, o relatório financeiro e o DELETE exigem Bearer token.

## Validando a refatoração

```bash
PORT=3001 npm start &
node tools/smoke.js tools/endpoints.json /tmp/depois.json
node tools/compare.js /tmp/antes.json /tmp/depois.json
```

## Auditoria

O relatório completo está em [`../reports/audit-project-2.md`](../reports/audit-project-2.md).
