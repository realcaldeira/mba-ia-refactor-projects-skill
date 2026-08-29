# Arquitetura-alvo: MVC

A Fase 3 converge todo projeto para a mesma forma lógica, independente da linguagem. O que muda
entre stacks é a extensão do arquivo e o idioma do framework — não a divisão de responsabilidades.

## Estrutura de diretórios

```
src/
├── config/            # 1. Configuração — tudo que muda por ambiente
│   └── settings.*     #    lê variáveis de ambiente, expõe objeto/classe de config
├── models/            # 2. Model — dados + regra de negócio do domínio
│   ├── <entidade>_model.*
│   └── ...            #    um arquivo por entidade (produto, usuario, pedido)
├── controllers/       # 3. Controller — orquestra o caso de uso
│   └── <entidade>_controller.*
├── views/             # 4. View/Routes — fronteira HTTP
│   └── routes.*       #    (ou <entidade>_routes.* quando houver muitas rotas)
├── middlewares/       # 5. Middleware — preocupações transversais
│   ├── error_handler.*
│   └── auth.*
├── services/          # 6. (opcional) integrações externas: e-mail, gateway, fila
└── app.*              # 7. Composition root — cria e conecta tudo
```

`.env.example` fica na raiz do projeto, versionado, sem valores reais.
Diretórios sem conteúdo não são criados: um projeto sem integração externa não ganha `services/`.

## Regra de dependência

```
views/routes  →  controllers  →  models  →  (banco)
      ↘             ↓              ↙
          config, middlewares, services
```

A seta aponta para quem pode ser importado. **Nunca no sentido contrário**: um model que importa
`request` do framework, ou que devolve um `Response`, quebra a arquitetura — é o erro mais comum
nesta refatoração.

## Responsabilidade de cada camada

### config/
- Lê variáveis de ambiente com *default seguro para desenvolvimento*.
- Concentra: porta, string de conexão, segredo, flags (`DEBUG`), origens de CORS, credenciais de
  serviços externos.
- Nunca contém regra de negócio nem literal de segredo de produção.
- Um segredo sem default (`SECRET_KEY` em produção) deve falhar alto no boot, não silenciosamente.

### models/
- Representa uma entidade do domínio e **é o único lugar que fala com o banco**.
- Contém: schema/mapeamento, queries (sempre parametrizadas), invariantes e regra de negócio
  própria da entidade (cálculo de total, transição de status válida, desconto).
- Expõe um serializador explícito (`to_dict`/`toJSON`) que **omite campos sensíveis** — senha,
  hash, token nunca saem daqui.
- Não conhece HTTP: nada de `request`, `res`, códigos de status ou `jsonify`.
- Erros de domínio são exceções tipadas (`ProdutoNaoEncontrado`, `EstoqueInsuficiente`), não
  dicionários com a chave `"erro"`.

### controllers/
- Um método por caso de uso. Orquestra: valida entrada → chama models → monta a resposta.
- Traduz exceção de domínio em status HTTP.
- **Não contém SQL** e **não contém regra de negócio pesada** — se um cálculo de domínio aparece
  aqui, ele pertence ao model.
- Recebe suas dependências (model, serviço) por parâmetro/construtor, não por import global —
  é isso que torna o controller testável sem banco.

### views/routes/
- Só registra rotas e liga cada uma ao método do controller.
- Pode aplicar middleware por rota (autenticação, validação de schema).
- Zero lógica: uma rota com `if` de negócio está no lugar errado.
- Em frameworks com template (Django, Rails, Laravel), a *view* é o template — a mesma regra vale:
  apresentação, nunca decisão de negócio.

### middlewares/
- `error_handler`: captura toda exceção não tratada, faz o log e devolve o envelope de erro
  padronizado. Depois dele existir, `try/except` genérico dentro de controller é redundante.
- `auth`: identifica o usuário e valida permissão antes do controller.
- Outros: CORS, rate limit, request id, log de acesso.

### services/
- Integrações com o mundo externo: SMTP, gateway de pagamento, fila, cache, API de terceiro.
- Recebem configuração injetada; nunca leem variável de ambiente diretamente.
- Existem para que o model/controller dependa de uma interface, não de `smtplib`.

### app (composition root)
- Único lugar que instancia coisas concretas e as conecta: carrega config, cria conexão, instancia
  models/serviços, injeta nos controllers, registra rotas e middlewares.
- Exponha uma *application factory* (`create_app()`, `buildApp()`) para que os testes montem a
  aplicação com dependências falsas.
- O bloco `if __name__ == "__main__"` / `listen()` só chama a factory e sobe o servidor.

## Preservação de contrato

A refatoração é **comportamentalmente neutra na superfície HTTP**:

- toda rota do inventário da Fase 1 continua existindo, com o mesmo método e o mesmo caminho;
- os status de sucesso e de erro continuam os mesmos para as mesmas entradas;
- o formato do corpo de resposta é preservado. Padronizar envelope só é permitido quando o
  usuário aprovar explicitamente, e nesse caso vira item destacado no resumo da Fase 3.

Exceção única: um endpoint **inseguro por natureza** (execução arbitrária de SQL/comando, reset
destrutivo de banco aberto) pode ser removido ou fechado atrás de autenticação. Isso precisa
aparecer no resumo da Fase 3 como mudança de contrato, com a justificativa e a alternativa
oferecida (comando de manutenção fora do HTTP).

## Nomenclatura

- Arquivos e diretórios em `snake_case` (Python, Ruby, Go) ou `camelCase`/`kebab-case` conforme a
  convenção viva da linguagem (Node/JS). **Siga a convenção da stack, não a sua preferência.**
- Sufixo explícito de camada: `produto_model.py`, `produtoController.js`, `routes.js`.
- Nomes de domínio no idioma que o projeto já usa. Um projeto em português continua em português —
  renomear o domínio inteiro é mudança de escopo, não refatoração arquitetural.

## Critério de "pronto"

- [ ] Nenhum SQL fora de `models/`.
- [ ] Nenhum `request`/`response` dentro de `models/`.
- [ ] Nenhum literal de configuração ou segredo fora de `config/`.
- [ ] Nenhum `try/except` genérico de infraestrutura dentro de controller (o handler central cobre).
- [ ] Toda rota do inventário responde com o status do baseline.
- [ ] Existe factory de aplicação e ela é usada pelo entry point.
- [ ] `.env.example` documenta todas as variáveis lidas por `config/`.
