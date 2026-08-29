"""Composition root: cria as dependências concretas e as conecta."""
from flask import Flask
from flask_cors import CORS

from src.config.logging_config import configurar_logging
from src.config.settings import settings
from src.controllers.category_controller import CategoryController
from src.controllers.health_controller import HealthController
from src.controllers.report_controller import ReportController
from src.controllers.task_controller import TaskController
from src.controllers.user_controller import UserController
from src.database import db
from src.middlewares.error_handler import registrar_error_handler
from src.services.notification_service import NotificationService, TransporteLog, TransporteSmtp
from src.views import report_routes, task_routes, user_routes


def _criar_transporte(config):
    if config.SMTP_USER and config.SMTP_PASSWORD:
        return TransporteSmtp(config.SMTP_HOST, config.SMTP_PORT, config.SMTP_USER, config.SMTP_PASSWORD)
    return TransporteLog()


def create_app(config=settings, database_uri=None, notificador=None):
    """Application factory. `database_uri` e `notificador` são injetáveis para teste."""
    config.validar()
    configurar_logging(config.LOG_LEVEL)

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri or config.DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["DEBUG"] = config.DEBUG

    CORS(app, origins=config.CORS_ORIGINS)
    db.init_app(app)

    # Importa os models para que o metadata conheça as tabelas antes do create_all.
    from src.models import Category, Task, User  # noqa: F401

    servico_notificacao = notificador or NotificationService(_criar_transporte(config))

    tasks = TaskController(notificador=servico_notificacao)
    usuarios = UserController(config.SECRET_KEY, config.TOKEN_TTL_HORAS)
    relatorios = ReportController()
    categorias = CategoryController()
    health = HealthController(config.VERSAO, config.AMBIENTE)

    app.register_blueprint(task_routes.criar_blueprint(tasks))
    app.register_blueprint(user_routes.criar_blueprint(usuarios))
    app.register_blueprint(report_routes.criar_blueprint(relatorios, categorias))

    app.add_url_rule("/health", "health", health.check, methods=["GET"])
    app.add_url_rule("/", "index", health.index, methods=["GET"])

    registrar_error_handler(app)

    with app.app_context():
        db.create_all()

    return app
