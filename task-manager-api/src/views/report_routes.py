"""Rotas de relatório e categoria."""
from flask import Blueprint


def criar_blueprint(relatorios, categorias):
    bp = Blueprint("reports", __name__)

    bp.add_url_rule("/reports/summary", "summary_report", relatorios.resumo, methods=["GET"])
    bp.add_url_rule("/reports/user/<int:user_id>", "user_report", relatorios.por_usuario, methods=["GET"])

    bp.add_url_rule("/categories", "get_categories", categorias.listar, methods=["GET"])
    bp.add_url_rule("/categories", "create_category", categorias.criar, methods=["POST"])
    bp.add_url_rule("/categories/<int:category_id>", "update_category", categorias.atualizar, methods=["PUT"])
    bp.add_url_rule("/categories/<int:category_id>", "delete_category", categorias.remover, methods=["DELETE"])

    return bp
