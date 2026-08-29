from flask import Blueprint
from src.config.settings import settings
from src.middlewares.auth import proteger_se_exigido

def criar_blueprint(relatorios, categorias, config=settings):
    bp = Blueprint('reports', __name__)

    def proteger(view):
        return proteger_se_exigido(view, config)
    bp.add_url_rule('/reports/summary', 'summary_report', proteger(relatorios.resumo), methods=['GET'])
    bp.add_url_rule('/reports/user/<int:user_id>', 'user_report', proteger(relatorios.por_usuario), methods=['GET'])
    bp.add_url_rule('/categories', 'get_categories', proteger(categorias.listar), methods=['GET'])
    bp.add_url_rule('/categories', 'create_category', proteger(categorias.criar), methods=['POST'])
    bp.add_url_rule('/categories/<int:category_id>', 'update_category', proteger(categorias.atualizar), methods=['PUT'])
    bp.add_url_rule('/categories/<int:category_id>', 'delete_category', proteger(categorias.remover), methods=['DELETE'])
    return bp
