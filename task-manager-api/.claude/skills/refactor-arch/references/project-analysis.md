# Fase 1 — Heurísticas de análise de projeto

Objetivo: produzir, sem escrever nada em disco, um retrato factual do projeto: linguagem,
framework, banco, domínio, arquitetura atual e superfície HTTP.

Toda afirmação sai de evidência no repositório. Sem evidência → `desconhecido`.

## 1. Delimitar o que é código-fonte

Antes de qualquer contagem, exclua o que não é escrito pelo time:

```
node_modules/  .venv/  venv/  env/  .git/  dist/  build/  target/  vendor/
__pycache__/  *.pyc  *.min.js  *.lock  package-lock.json  yarn.lock  poetry.lock
*.db  *.sqlite  *.sqlite3  coverage/  .pytest_cache/  .next/  .idea/  .vscode/
```

```bash
# arquivos de código + total de linhas (ajuste as extensões à linguagem detectada)
find . \( -name node_modules -o -name .venv -o -name venv -o -name .git \
       -o -name __pycache__ -o -name dist -o -name build \) -prune -o \
     -type f \( -name '*.py' -o -name '*.js' -o -name '*.ts' -o -name '*.php' \
       -o -name '*.rb' -o -name '*.go' -o -name '*.java' -o -name '*.cs' \) -print | xargs wc -l
```

`Source files` = número desses arquivos. `lines` = total do `wc -l`.

## 2. Detectar linguagem

| Sinal | Linguagem |
|---|---|
| `requirements.txt`, `pyproject.toml`, `Pipfile`, `*.py` | Python |
| `package.json`, `*.js`, `*.mjs`, `*.ts` | JavaScript / TypeScript (Node.js) |
| `composer.json`, `*.php` | PHP |
| `go.mod`, `*.go` | Go |
| `pom.xml`, `build.gradle`, `*.java` | Java |
| `Gemfile`, `*.rb` | Ruby |
| `*.csproj`, `*.cs` | C# / .NET |

Versão da linguagem: `python_requires` / `engines.node` / `go 1.x` no `go.mod` / `<java.version>`.
Se não houver, reporte a versão do runtime instalado (`python3 --version`, `node --version`) e
marque como *ambiente*, não como requisito do projeto.

## 3. Detectar framework e versão

**Sempre pelo manifesto de dependências primeiro** — é a única fonte com versão exata:

```bash
cat requirements.txt pyproject.toml 2>/dev/null      # Python
cat package.json | sed -n '/dependencies/,/}/p'      # Node
cat composer.json go.mod pom.xml Gemfile 2>/dev/null # outros
```

Confirme com os imports reais do código (uma dependência declarada e não usada não é o framework):

| Import / uso | Framework |
|---|---|
| `from flask import Flask` | Flask |
| `from fastapi import FastAPI` | FastAPI |
| `from django...` , `manage.py` | Django |
| `require('express')` / `import express` | Express |
| `@nestjs/core` | NestJS |
| `fastify` | Fastify |
| `Illuminate\\`, `artisan` | Laravel |
| `Symfony\\Component` | Symfony |
| `gin-gonic/gin`, `net/http` | Gin / stdlib Go |
| `org.springframework` | Spring Boot |
| `Rails.application` | Ruby on Rails |

Anote também as libs de apoio relevantes para a auditoria: ORM (`flask-sqlalchemy`, `sequelize`,
`prisma`, `typeorm`, `mongoose`, `gorm`), validação (`marshmallow`, `pydantic`, `zod`, `joi`),
autenticação (`flask-login`, `passport`, `jsonwebtoken`), CORS, cliente HTTP.

## 4. Detectar banco de dados e tabelas

Três fontes, nesta ordem de confiabilidade:

1. **DDL literal**: `grep -rn "CREATE TABLE" --include='*.py' --include='*.js' --include='*.sql' .`
2. **Models ORM**: classes com `db.Model` / `Model` / `Entity` / `@Table` — o nome da tabela vem de
   `__tablename__`, `tableName`, `@Table(name=...)` ou da convenção de pluralização.
3. **Migrations**: `migrations/`, `alembic/`, `prisma/schema.prisma`, `db/migrate/`.

O driver revela o SGBD: `sqlite3`, `psycopg2`/`pg`, `mysql2`/`PyMySQL`, `pymongo`/`mongoose`,
`redis`. String de conexão: `SQLALCHEMY_DATABASE_URI`, `DATABASE_URL`, `DB_HOST`.

## 5. Inferir o domínio de negócio

Cruze três fontes e descreva em **uma frase, em português**:

- nomes de tabelas/models (`produtos`, `pedidos`, `enrollments`, `payments`, `tasks`);
- prefixos das rotas (`/produtos`, `/api/checkout`, `/reports`);
- README e mensagens de log/erro.

Exemplos: `API de e-commerce (produtos, usuários, pedidos e relatório de vendas)`;
`LMS com fluxo de checkout (cursos, matrículas, pagamentos)`;
`Gerenciador de tarefas (tasks, usuários, categorias e relatórios)`.

## 6. Classificar a arquitetura atual

Percorra a árvore de diretórios e enquadre em um dos padrões:

| Padrão observado | Como descrever |
|---|---|
| Tudo em 1–4 arquivos na raiz, sem pastas de camada | `Monolítica — tudo em N arquivos, sem separação de camadas` |
| Uma classe/objeto que registra rotas, acessa o banco e aplica regra | `God Object — uma classe concentra roteamento, dados e regra de negócio` |
| Existe `models/` e `routes/`, mas a regra vive nas rotas | `Camadas parciais — models e rotas separados, mas sem camada de controller/serviço` |
| `models/ views/ controllers/` completos | `MVC — verificar apenas vazamentos entre camadas` |
| `domain/ application/ infrastructure/` | `Arquitetura em camadas / hexagonal` |

Registre também: existe módulo de configuração? existe error handler central? existe injeção de
dependência ou tudo é importado direto? há estado global (`global`, `let cache = {}`, singleton)?

## 7. Inventariar os endpoints (contrato da refatoração)

Esta lista é o critério de aceite da Fase 3. Precisa ser **completa**.

```bash
# Flask
grep -rn "@app.route\|@.*_bp.route\|add_url_rule" --include='*.py' .
# Express
grep -rn "app\.\(get\|post\|put\|patch\|delete\|use\)\|router\.\(get\|post\|put\|patch\|delete\)" --include='*.js' .
# Django / Rails / Laravel
grep -rn "urlpatterns\|path(\|Route::\|resources :" .
```

Atenção aos casos que o grep sozinho não pega:
- rotas registradas dinamicamente em laço ou dentro de um método (`setupRoutes(app)`);
- blueprints/routers com `url_prefix` ou `app.use('/api', router)` — o prefixo faz parte da rota;
- múltiplos métodos no mesmo decorator (`methods=['GET','POST']`) = dois endpoints;
- rotas de infraestrutura (`/health`, `/`) contam.

Normalize cada linha como `MÉTODO /rota/completa` e valide o total contra a documentação do
projeto (`api.http`, coleção Postman, README) quando existir.

## 8. Saída da fase

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3.x
Framework:     Flask 3.1.1
Dependencies:  flask-cors 5.0.1, sqlite3 (stdlib)
Domain:        API de e-commerce (produtos, usuários, pedidos, relatório de vendas)
Architecture:  Monolítica — tudo em 4 arquivos, sem separação de camadas
Source files:  4 files analyzed (780 lines)
DB tables:     produtos, usuarios, pedidos, itens_pedido
Endpoints:     18 endpoints mapeados
================================
```

Guarde internamente, para as fases seguintes: lista de arquivos com contagem de linhas, lista de
endpoints e lista de tabelas.
