from flask import Flask
from flask_cors import CORS
from src.config.logging_config import configurar_logging
from src.config.settings import settings
from src.controllers.health_controller import HealthController
from src.controllers.pedido_controller import PedidoController
from src.controllers.produto_controller import ProdutoController
from src.controllers.relatorio_controller import RelatorioController
from src.controllers.usuario_controller import UsuarioController
from src.database.connection import criar_conexao
from src.database.schema import inicializar
from src.middlewares.error_handler import registrar_error_handler
from src.models.pedido_model import PedidoModel
from src.models.produto_model import ProdutoModel
from src.models.relatorio_model import RelatorioModel
from src.models.usuario_model import UsuarioModel
from src.services.notificador import NotificadorLog
from src.views.routes import registrar_rotas

def create_app(conexao=None, config=settings, notificador=None):
    config.validar()
    configurar_logging(config.LOG_LEVEL)
    app = Flask(__name__)
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['DEBUG'] = config.DEBUG
    CORS(app, origins=config.CORS_ORIGINS)
    db = conexao or inicializar(criar_conexao(config.DB_PATH))
    produtos = ProdutoModel(db)
    usuarios = UsuarioModel(db)
    pedidos = PedidoModel(db)
    relatorios = RelatorioModel(db)
    controllers = {'produto': ProdutoController(produtos), 'usuario': UsuarioController(usuarios, config.SECRET_KEY, config.TOKEN_TTL_HORAS), 'pedido': PedidoController(pedidos, notificador or NotificadorLog()), 'relatorio': RelatorioController(relatorios), 'health': HealthController(produtos, usuarios, pedidos, config.VERSAO, config.AMBIENTE)}
    registrar_rotas(app, controllers, config)
    registrar_error_handler(app)
    return app
