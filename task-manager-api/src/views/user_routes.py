from flask import Blueprint
from src.config.settings import settings
from src.middlewares.auth import proteger_se_exigido

def criar_blueprint(controller, config=settings):
    bp = Blueprint('users', __name__)

    def proteger(view):
        return proteger_se_exigido(view, config)
    bp.add_url_rule('/users', 'get_users', proteger(controller.listar), methods=['GET'])
    bp.add_url_rule('/users', 'create_user', controller.criar, methods=['POST'])
    bp.add_url_rule('/users/<int:user_id>', 'get_user', proteger(controller.buscar), methods=['GET'])
    bp.add_url_rule('/users/<int:user_id>', 'update_user', proteger(controller.atualizar), methods=['PUT'])
    bp.add_url_rule('/users/<int:user_id>', 'delete_user', proteger(controller.remover), methods=['DELETE'])
    bp.add_url_rule('/users/<int:user_id>/tasks', 'get_user_tasks', proteger(controller.tasks_do_usuario), methods=['GET'])
    bp.add_url_rule('/login', 'login', controller.login, methods=['POST'])
    return bp
