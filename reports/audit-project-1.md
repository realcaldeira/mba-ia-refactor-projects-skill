================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python 3 + Flask 3.1.1
Files:   4 analyzed | 780 lines of code
Date:    2026-08-29

## Phase 1 — Project Analysis

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3 (ambiente 3.14.6)
Framework:     Flask 3.1.1
Dependencies:  flask-cors 5.0.1, sqlite3 (stdlib)
Domain:        API de e-commerce (produtos, usuários, pedidos e relatório de vendas)
Architecture:  Monolítica — tudo em 4 arquivos, sem separação de camadas
Source files:  4 files analyzed (780 lines)
DB tables:     produtos, usuarios, pedidos, itens_pedido
Endpoints:     19 endpoints mapeados
================================
```

## Summary

CRITICAL: 7 | HIGH: 10 | MEDIUM: 9 | LOW: 6

| Severidade | Qtd | Principais ocorrências |
|---|---|---|
| CRITICAL | 7 | SQL Injection, Hardcoded Secret, Arbitrary SQL Execution Endpoint, Unauthenticated Destructive Endpoint, Sensitive Data Exposure (×2), God Module |
| HIGH | 10 | Plaintext Password, Missing Authentication, Insecure Defaults, Business Logic in Controller, Data Access in Controller, Missing Configuration Layer, No Composition Root, Global Mutable State, Tight Coupling, God Method sem transação |
| MEDIUM | 9 | Missing Centralized Error Handling, N+1 Query, Aggregation in Memory, Missing Pagination, Referential Integrity, Duplicated Code, Duplicated Validation, Information Disclosure, Schema sem constraints |
| LOW | 6 | print as Logging, Magic Numbers, Unused Imports, Builtin Shadowing, Poor Naming, Unnecessary else |

## Findings

### #1 [CRITICAL] SQL Injection

- **File:** `models.py:28-297` (ocorrências: 28, 48-49, 58-60, 68, 92, 110, 127-128, 140, 149-150, 155, 158-160, 164-165, 174, 188, 192, 220, 224, 280, 291-297)
- **Evidence:**
  ```python
  cursor.execute(
      "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
  )
  ```
- **Description:** Todas as 18 queries do arquivo são montadas por concatenação de string com
  valores vindos da requisição HTTP. Nenhuma usa os placeholders `?` que o driver `sqlite3` oferece.
  Alcança `SELECT`, `INSERT`, `UPDATE` e `DELETE` das quatro tabelas.
- **Impact:** `POST /login` com `{"email": "admin@loja.com'--", "senha": "x"}` autentica como
  administrador sem a senha. `GET /produtos/busca?q=' UNION SELECT ...` lê qualquer tabela, inclusive
  as senhas. `criar_pedido` (linha 140) injeta pelo campo numérico `produto_id` do corpo JSON, que
  nunca é convertido para inteiro.
- **Recommendation:** Trocar toda concatenação por query parametrizada; em filtro dinâmico, montar
  a estrutura e passar os valores como parâmetros (playbook: `R2`).

### #2 [CRITICAL] Hardcoded Credentials / Secrets

- **File:** `app.py:7`
- **Evidence:**
  ```python
  app.config["SECRET_KEY"] = "<redacted>"
  ```
- **Description:** A chave de assinatura da aplicação está literal no código versionado. O mesmo
  vale para as credenciais de usuários semeadas em `database.py:75-79` (`admin@loja.com` / `<redacted>`).
- **Impact:** Qualquer pessoa com acesso ao repositório forja sessões e cookies assinados; rotacionar
  a chave exige alterar código e redeploy. As credenciais de admin do seed valem em produção.
- **Recommendation:** Extrair para módulo de config lendo variáveis de ambiente, com `.env.example`
  versionado sem valores reais (playbook: `R1`).

### #3 [CRITICAL] Arbitrary Query Execution Endpoint

- **File:** `app.py:59-78`
- **Evidence:**
  ```python
  @app.route("/admin/query", methods=["POST"])
  def executar_query():
      query = dados.get("sql", "")
      cursor.execute(query)
  ```
- **Description:** Endpoint público que recebe uma string SQL do cliente e a executa diretamente no
  banco, sem autenticação, sem allowlist e sem log de auditoria.
- **Impact:** Controle total do banco por qualquer cliente da rede: `DROP TABLE`, leitura de todas as
  senhas, alteração de preços e pedidos. Não existe mitigação parcial para este endpoint.
- **Recommendation:** Remover o endpoint; a necessidade operacional legítima vira script de
  manutenção fora da superfície HTTP (playbook: `R11`).

### #4 [CRITICAL] Unauthenticated Destructive Endpoint

- **File:** `app.py:47-57`
- **Evidence:**
  ```python
  @app.route("/admin/reset-db", methods=["POST"])
  def reset_database():
      cursor.execute("DELETE FROM itens_pedido")
  ```
- **Description:** `POST /admin/reset-db` apaga as quatro tabelas do banco sem qualquer verificação
  de identidade ou papel. Além disso, acessa o banco diretamente do entry point.
- **Impact:** Perda total de dados com uma requisição não autenticada; um crawler ou um teste
  acidental destrói o ambiente.
- **Recommendation:** Remover da API e transformar em comando de manutenção; se mantido, exigir
  autenticação com papel `admin` (playbook: `R11`, `R5`).

### #5 [CRITICAL] Sensitive Data Exposure — senha na resposta

- **File:** `models.py:79-102` (linhas 83 e 99)
- **Evidence:**
  ```python
  "senha": row["senha"],
  ```
- **Description:** `get_todos_usuarios` e `get_usuario_por_id` serializam a coluna `senha` no
  dicionário devolvido, que vai direto para a resposta HTTP de `GET /usuarios` e `GET /usuarios/<id>`.
- **Impact:** Um `GET /usuarios` sem autenticação devolve a senha de todos os usuários em texto
  plano — vazamento em massa com uma única requisição.
- **Recommendation:** Serializador explícito por entidade, com allowlist de campos públicos que
  exclui a senha (playbook: `R3`).

### #6 [CRITICAL] Sensitive Data Exposure — configuração no /health

- **File:** `controllers.py:276-290`
- **Evidence:**
  ```python
  "debug": True,
  "secret_key": "<redacted>"
  ```
- **Description:** O endpoint de health check devolve a `SECRET_KEY`, o caminho do banco, a flag de
  debug e o ambiente declarado como `producao`.
- **Impact:** `GET /health` — tipicamente o endpoint mais exposto e menos protegido de uma API — vira
  um oráculo de credenciais.
- **Recommendation:** Health check devolve apenas estado de liveness e contadores não sensíveis
  (playbook: `R3`).

### #7 [CRITICAL] God Module

- **File:** `models.py:1-314`
- **Evidence:**
  ```python
  def criar_pedido(usuario_id, itens):   # acesso a dados + regra de estoque + cálculo de total
  def relatorio_vendas():                # + agregação + regra de desconto + formatação
  ```
- **Description:** Um único arquivo concentra acesso a dados, regra de negócio (estoque, total,
  faixas de desconto), serialização e formatação de resposta para os quatro domínios (produtos,
  usuários, pedidos, relatórios). `controllers.py` sofre do mesmo problema em outra direção:
  292 linhas com validação, orquestração, notificação e formatação.
- **Impact:** Impossível testar uma regra em isolamento — qualquer teste exige o banco real.
  Qualquer alteração em pedidos arrisca produtos e usuários no mesmo arquivo.
- **Recommendation:** Decompor por domínio em `models/` (um por entidade) e `controllers/`,
  com a regra de negócio junto da entidade (playbook: `R6`, `R7`, `R8`).

### #8 [HIGH] Plaintext Password Storage

- **File:** `models.py:126-129`, `database.py:75-79`
- **Evidence:**
  ```python
  "INSERT INTO usuarios (nome, email, senha, tipo) VALUES ('" +
  nome + "', '" + email + "', '" + senha + "', '" + tipo + "')"
  ```
- **Description:** A senha é gravada exatamente como chegou, sem hash e sem salt. O login compara
  a string em SQL (`AND senha = '...'`).
- **Impact:** Um vazamento do arquivo `loja.db` expõe as senhas reais dos usuários — que
  tipicamente são reusadas em outros serviços.
- **Recommendation:** `generate_password_hash`/`check_password_hash` (PBKDF2 com salt) e comparação
  em tempo constante (playbook: `R4`).

### #9 [HIGH] Missing Authentication / Authorization

- **File:** `app.py:11-30`
- **Evidence:**
  ```python
  app.add_url_rule("/usuarios", "listar_usuarios", controllers.listar_usuarios, methods=["GET"])
  ```
- **Description:** Nenhuma das 19 rotas tem verificação de identidade ou papel — não existe
  decorator, middleware ou `before_request` de autenticação no projeto. Listar usuários, criar
  produtos, alterar status de pedido e ler o relatório de vendas são todas operações abertas.
- **Impact:** Qualquer cliente lê e altera os dados de qualquer outro; não há como distinguir
  cliente de administrador.
- **Recommendation:** Middleware de autenticação com token assinado e verificação de papel nas
  rotas privilegiadas (playbook: `R5`).

### #10 [HIGH] Insecure Defaults (DEBUG + CORS + bind)

- **File:** `app.py:8-9, 88`
- **Evidence:**
  ```python
  app.config["DEBUG"] = True
  CORS(app)
  app.run(host="0.0.0.0", port=5000, debug=True)
  ```
- **Description:** Debug ligado por padrão, CORS liberado para qualquer origem e bind em todas as
  interfaces, sem nenhuma dessas decisões vir de variável de ambiente.
- **Impact:** Com `debug=True` exposto em `0.0.0.0`, o console interativo do Werkzeug permite
  execução de código Python remoto. O CORS aberto permite que qualquer site faça requisições
  autenticadas em nome do usuário.
- **Recommendation:** Todas as três decisões passam a vir da config por ambiente, com default seguro
  (playbook: `R1`).

### #11 [HIGH] Business Logic in Controller

- **File:** `controllers.py:24-58, 188-255`
- **Evidence:**
  ```python
  categorias_validas = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]
  if categoria not in categorias_validas:
  ```
- **Description:** Regras de domínio vivem dentro dos handlers HTTP: catálogo de categorias válidas,
  limites de tamanho de nome, lista de status de pedido permitidos (linha 242) e o disparo de
  notificações (linhas 208-210, 248-250).
- **Impact:** Nenhuma dessas regras pode ser reusada por um worker, CLI ou outro endpoint, nem
  testada sem subir uma requisição HTTP. As mesmas regras já divergem entre `criar` e `atualizar`.
- **Recommendation:** Mover as regras para os models de domínio e deixar o controller apenas
  orquestrando (playbook: `R7`).

### #12 [HIGH] Data Access in Controller

- **File:** `controllers.py:264-274`
- **Evidence:**
  ```python
  db = get_db()
  cursor = db.cursor()
  cursor.execute("SELECT COUNT(*) FROM produtos")
  ```
- **Description:** `health_check` abre cursor e escreve SQL diretamente na camada de controller,
  pulando a camada de modelo. `app.py:47-57` faz o mesmo no entry point.
- **Impact:** O schema do banco vaza para a camada de apresentação; trocar o banco obriga a
  reescrever rotas.
- **Recommendation:** Todo acesso a dados desce para os models (playbook: `R8`).

### #13 [HIGH] Missing Configuration Layer

- **File:** `app.py:7-8`, `database.py:5`
- **Evidence:**
  ```python
  db_path = "loja.db"
  ```
- **Description:** Não existe módulo de configuração: porta, host, caminho do banco, segredo e flags
  são literais espalhados por três arquivos. Não há `.env.example`.
- **Impact:** Um artefato por ambiente; impossível rodar em container sem editar código.
- **Recommendation:** Módulo `config/settings.py` lendo variáveis de ambiente (playbook: `R1`).

### #14 [HIGH] No Composition Root

- **File:** `app.py:6-30`
- **Evidence:**
  ```python
  app = Flask(__name__)
  app.add_url_rule("/produtos", "listar_produtos", controllers.listar_produtos, methods=["GET"])
  ```
- **Description:** A aplicação é montada em escopo de módulo com 19 `add_url_rule` manuais e
  dependências resolvidas por import global. Não existe `create_app()`.
- **Impact:** Impossível instanciar a aplicação em teste com um banco em memória ou dependências
  falsas; importar `app` já cria o servidor real.
- **Recommendation:** Application factory registrando rotas via blueprint e injetando dependências
  (playbook: `R9`).

### #15 [HIGH] Global Mutable State / Connection Singleton

- **File:** `database.py:4-11`
- **Evidence:**
  ```python
  db_connection = None
  def get_db():
      global db_connection
      db_connection = sqlite3.connect(db_path, check_same_thread=False)
  ```
- **Description:** Uma conexão única de módulo é compartilhada por todas as requisições, com a
  proteção de thread do SQLite explicitamente desligada.
- **Impact:** Sob concorrência, cursores e transações de requisições diferentes se misturam —
  corrupção de dados e erros intermitentes impossíveis de reproduzir.
- **Recommendation:** Factory de conexão criada pelo composition root e injetada nos models
  (playbook: `R12`).

### #16 [HIGH] Tight Coupling without Dependency Injection

- **File:** `controllers.py:1-3`, `models.py:1,5`
- **Evidence:**
  ```python
  import models
  from database import get_db
  ```
- **Description:** Controllers importam o módulo de models concretamente e models chamam `get_db()`
  global dentro de cada função. Nenhuma dependência é recebida por parâmetro.
- **Impact:** Nenhum teste unitário roda sem o banco real; trocar a implementação exige editar todos
  os consumidores.
- **Recommendation:** Injetar model no controller e conexão no model, via construtor (playbook: `R13`).

### #17 [HIGH] God Method sem transação (criar_pedido)

- **File:** `models.py:133-169`
- **Evidence:**
  ```python
  for item in itens:
      cursor.execute("SELECT * FROM produtos WHERE id = " + str(item["produto_id"]))
      if produto["estoque"] < item["quantidade"]:
  ```
- **Description:** Uma função de 37 linhas valida estoque, calcula total, cria o pedido, insere os
  itens e decrementa o estoque — tudo sem transação explícita e com *check-then-act* entre a
  verificação e a baixa de estoque. Erros de domínio são sinalizados por um dicionário com a chave
  `"erro"`, obrigando o controller a inspecionar o retorno (linha 205).
- **Impact:** Uma falha no meio deixa pedido criado sem itens ou estoque decrementado sem pedido.
  Duas requisições simultâneas vendem o mesmo item em estoque unitário.
- **Recommendation:** Transação envolvendo a operação inteira, baixa condicional de estoque
  (`WHERE estoque >= ?`) e exceções de domínio no lugar do dicionário (playbook: `R18`, `R10`).

### #18 [MEDIUM] Missing Centralized Error Handling

- **File:** `controllers.py:10-292` (16 ocorrências: 10, 21, 60, 95, 108, 125, 133, 143, 164, 185, 218, 226, 234, 254, 261, 291)
- **Evidence:**
  ```python
  except Exception as e:
      return jsonify({"erro": str(e)}), 500
  ```
- **Description:** Cada uma das 16 funções repete o mesmo bloco `try/except Exception` devolvendo
  500 com a mensagem crua da exceção. Não existe `errorhandler` registrado.
- **Impact:** Detalhes internos (nome de tabela, sintaxe SQL) vazam para o cliente; o formato de erro
  é inconsistente entre rotas; a repetição esconde a regra de negócio de cada função.
- **Recommendation:** Error handler central com exceções de domínio tipadas (playbook: `R10`).

### #19 [MEDIUM] N+1 Query

- **File:** `models.py:171-233`
- **Evidence:**
  ```python
  cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"]))
  for item in itens:
      cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
  ```
- **Description:** `get_pedidos_usuario` e `get_todos_pedidos` fazem uma query por pedido e mais uma
  por item de cada pedido — N+1+M idas ao banco em três níveis de aninhamento.
- **Impact:** 100 pedidos com 3 itens = 401 queries em uma única requisição. `GET /pedidos` degrada
  linearmente com o crescimento da base.
- **Recommendation:** Uma query com `LEFT JOIN` entre pedidos, itens e produtos, agrupada em memória
  (playbook: `R14`).

### #20 [MEDIUM] Aggregation in Application Memory

- **File:** `models.py:239-254`, `controllers.py:124`
- **Evidence:**
  ```python
  cursor.execute("SELECT COUNT(*) FROM pedidos")
  cursor.execute("SELECT SUM(total) FROM pedidos")
  cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status = 'pendente'")
  ```
- **Description:** O relatório de vendas faz cinco varreduras separadas na mesma tabela quando uma
  única query agregada resolveria. Em `controllers.py:124`, o total da busca vem de `len()` sobre o
  resultado completo já materializado.
- **Impact:** Custo cinco vezes maior que o necessário no endpoint mais pesado da API.
- **Recommendation:** Uma query com `COUNT`, `SUM` e agregação condicional (playbook: `R14`).

### #21 [MEDIUM] Missing Pagination

- **File:** `models.py:7, 75, 174, 206, 289`
- **Evidence:**
  ```python
  cursor.execute("SELECT * FROM produtos")
  ```
- **Description:** Todos os cinco endpoints de listagem devolvem a tabela inteira, sem `LIMIT`,
  `OFFSET` ou cursor.
- **Impact:** A resposta cresce sem limite com a base; com dezenas de milhares de registros, o
  endpoint estoura memória e tempo de resposta.
- **Recommendation:** Parâmetros `page`/`per_page` com teto, preservando o comportamento atual quando
  ausentes (playbook: `R15`).

### #22 [MEDIUM] Referential Integrity Ignored

- **File:** `models.py:65-70`
- **Evidence:**
  ```python
  cursor.execute("DELETE FROM produtos WHERE id = " + str(id))
  ```
- **Description:** Produtos são apagados sem verificar itens de pedido que os referenciam, e o schema
  (`database.py:14-53`) não declara nenhuma `FOREIGN KEY`.
- **Impact:** Pedidos históricos passam a apontar para produtos inexistentes; o relatório e a
  listagem de pedidos devolvem `"produto_nome": "Desconhecido"` silenciosamente.
- **Recommendation:** `FOREIGN KEY` no schema com `PRAGMA foreign_keys = ON`, e recusa ou soft delete
  quando houver dependência (playbook: `R16`).

### #23 [MEDIUM] Duplicated Code — mapeamento linha→dicionário

- **File:** `models.py:12-21, 31-40, 79-86, 95-102, 304-313`
- **Evidence:**
  ```python
  result.append({"id": row["id"], "nome": row["nome"], "descricao": row["descricao"], ...})
  ```
- **Description:** O mesmo mapeamento campo a campo de produto aparece três vezes e o de usuário duas
  vezes, sempre reescrito manualmente.
- **Impact:** Adicionar uma coluna exige lembrar de cinco lugares; foi exatamente assim que a senha
  acabou exposta em dois deles e não nos outros.
- **Recommendation:** Um serializador por entidade (playbook: `R3`, `R20`).

### #24 [MEDIUM] Duplicated Validation

- **File:** `controllers.py:28-54` × `controllers.py:72-90`
- **Evidence:**
  ```python
  if "nome" not in dados: return jsonify({"erro": "Nome é obrigatório"}), 400
  ```
- **Description:** O bloco de validação de produto é copiado entre `criar_produto` e
  `atualizar_produto` — e as cópias já divergiram: o update não valida categoria nem tamanho do nome.
- **Impact:** `PUT /produtos/<id>` aceita categoria inválida que `POST /produtos` rejeita: a mesma
  entidade tem dois contratos diferentes.
- **Recommendation:** Validador único na camada de domínio, chamado pelos dois casos de uso
  (playbook: `R20`).

### #25 [MEDIUM] Information Disclosure via mensagem de exceção

- **File:** `controllers.py:12, 22, 62, 96, 109, 126, 134, 144, 165, 186, 220, 227, 235, 255, 262, 292`
- **Evidence:**
  ```python
  return jsonify({"erro": str(e)}), 500
  ```
- **Description:** A mensagem interna da exceção é devolvida no corpo da resposta.
- **Impact:** Erros de SQL revelam nomes de tabelas e colunas ao atacante — informação que acelera a
  exploração do SQL Injection do achado #1.
- **Recommendation:** Log interno detalhado, resposta genérica ao cliente (playbook: `R10`, `R22`).

### #26 [MEDIUM] Schema sem constraints

- **File:** `database.py:14-53`
- **Evidence:**
  ```python
  CREATE TABLE IF NOT EXISTS usuarios (
      id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT, senha TEXT,
  ```
- **Description:** Nenhuma coluna é `NOT NULL`, `email` não é `UNIQUE`, não há `FOREIGN KEY` nem
  índice nas colunas usadas em filtro (`categoria`, `usuario_id`, `pedido_id`).
- **Impact:** Dois usuários com o mesmo e-mail quebram o login; toda busca por pedido de usuário é
  full table scan.
- **Recommendation:** Declarar constraints e índices no schema, com o DDL fora do getter de conexão
  (playbook: `R8`, `R16`).

### #27 [LOW] print as Logging

- **File:** `controllers.py:8-250` (14 ocorrências), `app.py:56, 83-86`
- **Evidence:**
  ```python
  print("Login bem-sucedido: " + email)
  ```
- **Description:** Diagnóstico via `print`, sem nível, sem timestamp e sem destino configurável.
  Parte dos prints registra dado pessoal (e-mail do usuário nas linhas 161, 179, 182).
- **Impact:** Impossível ajustar verbosidade por ambiente ou coletar logs de forma estruturada;
  e-mails de usuários acabam em stdout.
- **Recommendation:** Logger com níveis, sem dado pessoal (playbook: `R22`).

### #28 [LOW] Magic Numbers e Magic Strings

- **File:** `models.py:256-262`, `controllers.py:47-52, 242`
- **Evidence:**
  ```python
  if faturamento > 10000: desconto = faturamento * 0.1
  elif faturamento > 5000: desconto = faturamento * 0.05
  ```
- **Description:** Faixas e percentuais de desconto, limites de tamanho de nome (2 e 200), lista de
  categorias e lista de status de pedido aparecem como literais soltos no meio da lógica.
- **Impact:** Mudar uma regra de negócio exige caçar literais em dois arquivos; nada indica que
  `0.05` é uma política comercial.
- **Recommendation:** Constantes nomeadas na camada de domínio (playbook: `R21`).

### #29 [LOW] Unused Imports

- **File:** `models.py:2`, `database.py:2`
- **Evidence:**
  ```python
  import sqlite3   # models.py — nunca utilizado
  import os        # database.py — nunca utilizado
  ```
- **Description:** Imports residuais que sugerem acoplamento inexistente.
- **Impact:** Ruído de leitura e falso sinal de dependência.
- **Recommendation:** Remover.

### #30 [LOW] Builtin Shadowing

- **File:** `models.py:24, 43, 54, 65, 89`, `controllers.py:14, 64, 98, 136`
- **Evidence:**
  ```python
  def get_produto_por_id(id):
  ```
- **Description:** O parâmetro `id` sombreia a função embutida `id()` do Python em nove funções.
- **Impact:** Legibilidade e risco de bug sutil se a builtin for necessária no mesmo escopo.
- **Recommendation:** Renomear para `produto_id` / `usuario_id` (playbook: `R21`).

### #31 [LOW] Poor Naming

- **File:** `models.py:187-193, 219-225`
- **Evidence:**
  ```python
  cursor2 = db.cursor()
  cursor3 = db.cursor()
  ```
- **Description:** Cursores numerados sequencialmente em vez de nomeados pelo que consultam — sintoma
  direto do N+1 do achado #19.
- **Impact:** O leitor precisa rastrear o número para entender qual nível do laço está lendo.
- **Recommendation:** Nomes de domínio; o problema desaparece com o `JOIN` (playbook: `R14`, `R21`).

### #32 [LOW] Unnecessary else after return

- **File:** `app.py:70-76`, `controllers.py:17-20, 139-142, 177-183`
- **Evidence:**
  ```python
  if produto:
      return jsonify(...), 200
  else:
      return jsonify(...), 404
  ```
- **Description:** `else` redundante depois de `return`, adicionando um nível de indentação sem
  necessidade.
- **Impact:** Legibilidade.
- **Recommendation:** Guard clause (playbook: `R21`).

## Deprecated APIs

Varredura executada com `python -W always::DeprecationWarning` sobre o import dos quatro módulos e
por busca dirigida (`datetime.utcnow`, `before_first_request`, adaptadores `sqlite3`, APIs removidas
do Flask 2.3/3.x): **nenhuma API deprecated em uso**. O projeto usa Flask 3.1.1 e `sqlite3` da stdlib
com APIs atuais.

Ponto relacionado, ainda que não seja uma API deprecated: `app.run()` (`app.py:88`) sobe o servidor
de desenvolvimento do Werkzeug, que o próprio Flask desaconselha como runtime de produção.

## Endpoints inventariados (contrato da Fase 3)

| # | Método | Rota | Status baseline |
|---|---|---|---|
| 1 | GET | `/` | 200 |
| 2 | GET | `/health` | 200 |
| 3 | GET | `/produtos` | 200 |
| 4 | GET | `/produtos/busca` | 200 |
| 5 | GET | `/produtos/<id>` | 200 / 404 |
| 6 | POST | `/produtos` | 201 / 400 |
| 7 | PUT | `/produtos/<id>` | 200 / 404 |
| 8 | DELETE | `/produtos/<id>` | 200 / 404 |
| 9 | GET | `/usuarios` | 200 |
| 10 | GET | `/usuarios/<id>` | 200 / 404 |
| 11 | POST | `/usuarios` | 201 / 400 |
| 12 | POST | `/login` | 200 / 401 |
| 13 | POST | `/pedidos` | 201 / 400 |
| 14 | GET | `/pedidos` | 200 |
| 15 | GET | `/pedidos/usuario/<id>` | 200 |
| 16 | PUT | `/pedidos/<id>/status` | 200 / 400 |
| 17 | GET | `/relatorios/vendas` | 200 |
| 18 | POST | `/admin/reset-db` | 200 |
| 19 | POST | `/admin/query` | 200 / 400 / 500 |

## Plano de refatoração proposto

1. **config/** — extrair segredo, debug, CORS, host, porta e caminho do banco para variáveis de
   ambiente com `.env.example` (resolve #2, #10, #13).
2. **database/** — factory de conexão injetável, schema com constraints e índices, seed separado
   (resolve #15, #26 e parte de #22).
3. **models/** — um módulo por entidade, com queries parametrizadas, serializador sem campos
   sensíveis, regra de negócio e transações (resolve #1, #5, #7, #8, #17, #19, #20, #23).
4. **controllers/** — orquestração por caso de uso, sem SQL e sem regra de negócio, recebendo os
   models por injeção (resolve #11, #12, #16, #24).
5. **views/routes.py** — blueprint com o mapa rota → controller, preservando as 19 rotas
   (resolve #14 em conjunto com o passo 7).
6. **middlewares/** — error handler central com exceções de domínio e logging estruturado
   (resolve #18, #25, #27).
7. **app.py** — composition root com `create_app()`; remoção dos dois endpoints administrativos
   inseguros (resolve #3, #4, #14).
8. Limpeza final: constantes nomeadas, imports mortos, renomeações e guard clauses
   (resolve #21, #28, #29, #30, #31, #32).

================================
Total: 32 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
