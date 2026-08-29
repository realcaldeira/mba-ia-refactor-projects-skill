from flask import Blueprint
from src.config.settings import settings
from src.middlewares.auth import proteger_se_exigido

def criar_blueprint(controller, config=settings):
    bp = Blueprint('tasks', __name__)

    def proteger(view):
        return proteger_se_exigido(view, config)
    bp.add_url_rule('/tasks', 'get_tasks', proteger(controller.listar), methods=['GET'])
    bp.add_url_rule('/tasks', 'create_task', proteger(controller.criar), methods=['POST'])
    bp.add_url_rule('/tasks/search', 'search_tasks', proteger(controller.pesquisar), methods=['GET'])
    bp.add_url_rule('/tasks/stats', 'task_stats', proteger(controller.estatisticas), methods=['GET'])
    bp.add_url_rule('/tasks/<int:task_id>', 'get_task', proteger(controller.buscar), methods=['GET'])
    bp.add_url_rule('/tasks/<int:task_id>', 'update_task', proteger(controller.atualizar), methods=['PUT'])
    bp.add_url_rule('/tasks/<int:task_id>', 'delete_task', proteger(controller.remover), methods=['DELETE'])
    return bp
