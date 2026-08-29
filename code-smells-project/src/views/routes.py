"""Fronteira HTTP: apenas o mapa rota → controller. Nenhuma lógica vive aqui."""


def registrar_rotas(app, controllers):
    produtos = controllers["produto"]
    usuarios = controllers["usuario"]
    pedidos = controllers["pedido"]
    relatorios = controllers["relatorio"]
    health = controllers["health"]

    rotas = (
        ("/", "index", health.index, ["GET"]),
        ("/health", "health_check", health.check, ["GET"]),

        ("/produtos", "listar_produtos", produtos.listar, ["GET"]),
        ("/produtos/busca", "buscar_produtos", produtos.pesquisar, ["GET"]),
        ("/produtos/<int:id>", "buscar_produto", produtos.buscar, ["GET"]),
        ("/produtos", "criar_produto", produtos.criar, ["POST"]),
        ("/produtos/<int:id>", "atualizar_produto", produtos.atualizar, ["PUT"]),
        ("/produtos/<int:id>", "deletar_produto", produtos.remover, ["DELETE"]),

        ("/usuarios", "listar_usuarios", usuarios.listar, ["GET"]),
        ("/usuarios/<int:id>", "buscar_usuario", usuarios.buscar, ["GET"]),
        ("/usuarios", "criar_usuario", usuarios.criar, ["POST"]),
        ("/login", "login", usuarios.login, ["POST"]),

        ("/pedidos", "criar_pedido", pedidos.criar, ["POST"]),
        ("/pedidos", "listar_todos_pedidos", pedidos.listar, ["GET"]),
        ("/pedidos/usuario/<int:usuario_id>", "listar_pedidos_usuario", pedidos.listar_por_usuario, ["GET"]),
        ("/pedidos/<int:pedido_id>/status", "atualizar_status_pedido", pedidos.atualizar_status, ["PUT"]),

        ("/relatorios/vendas", "relatorio_vendas", relatorios.vendas, ["GET"]),
    )

    for regra, nome, view, metodos in rotas:
        app.add_url_rule(regra, nome, view, methods=metodos)

    return app
