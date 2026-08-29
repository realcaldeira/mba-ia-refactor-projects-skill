from src.config.settings import settings
from src.middlewares.auth import proteger_se_exigido

def registrar_rotas(app, controllers, config=settings):
    produtos = controllers['produto']
    usuarios = controllers['usuario']
    pedidos = controllers['pedido']
    relatorios = controllers['relatorio']
    health = controllers['health']

    def proteger(view):
        return proteger_se_exigido(view, config)
    rotas = (('/', 'index', health.index, ['GET']), ('/health', 'health_check', health.check, ['GET']), ('/produtos', 'listar_produtos', produtos.listar, ['GET']), ('/produtos/busca', 'buscar_produtos', produtos.pesquisar, ['GET']), ('/produtos/<int:id>', 'buscar_produto', produtos.buscar, ['GET']), ('/produtos', 'criar_produto', proteger(produtos.criar), ['POST']), ('/produtos/<int:id>', 'atualizar_produto', proteger(produtos.atualizar), ['PUT']), ('/produtos/<int:id>', 'deletar_produto', proteger(produtos.remover), ['DELETE']), ('/usuarios', 'listar_usuarios', proteger(usuarios.listar), ['GET']), ('/usuarios/<int:id>', 'buscar_usuario', proteger(usuarios.buscar), ['GET']), ('/usuarios', 'criar_usuario', usuarios.criar, ['POST']), ('/login', 'login', usuarios.login, ['POST']), ('/pedidos', 'criar_pedido', proteger(pedidos.criar), ['POST']), ('/pedidos', 'listar_todos_pedidos', proteger(pedidos.listar), ['GET']), ('/pedidos/usuario/<int:usuario_id>', 'listar_pedidos_usuario', proteger(pedidos.listar_por_usuario), ['GET']), ('/pedidos/<int:pedido_id>/status', 'atualizar_status_pedido', proteger(pedidos.atualizar_status), ['PUT']), ('/relatorios/vendas', 'relatorio_vendas', proteger(relatorios.vendas), ['GET']))
    for regra, nome, view, metodos in rotas:
        app.add_url_rule(regra, nome, view, methods=metodos)
    return app
