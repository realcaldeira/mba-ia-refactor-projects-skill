# ecommerce-api-legacy

LMS API (cursos, matrículas e checkout) em Node.js/Express — **refatorada para MVC** pela skill
`refactor-arch`.

## Como rodar

```bash
npm install
cp .env.example .env      # ajuste os valores; o .env não é versionado
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

**Mudança de comportamento deliberada** (correção de falha crítica de autenticação): no checkout,
um e-mail já cadastrado agora exige a senha correta e responde `401` quando ela não confere. Antes,
informar o e-mail de outra pessoa bastava para comprar em nome dela. Nenhum status do conjunto de
testes original mudou.

## Validando a refatoração

```bash
PORT=3001 npm start &
node tools/smoke.js tools/endpoints.json /tmp/depois.json
node tools/compare.js /tmp/antes.json /tmp/depois.json
```

## Auditoria

O relatório completo está em [`../reports/audit-project-2.md`](../reports/audit-project-2.md).
