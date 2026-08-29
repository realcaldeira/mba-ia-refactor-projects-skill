"""Rotas de task: só o mapa rota → controller."""
from flask import Blueprint


def criar_blueprint(controller):
    bp = Blueprint("tasks", __name__)

    bp.add_url_rule("/tasks", "get_tasks", controller.listar, methods=["GET"])
    bp.add_url_rule("/tasks", "create_task", controller.criar, methods=["POST"])
    bp.add_url_rule("/tasks/search", "search_tasks", controller.pesquisar, methods=["GET"])
    bp.add_url_rule("/tasks/stats", "task_stats", controller.estatisticas, methods=["GET"])
    bp.add_url_rule("/tasks/<int:task_id>", "get_task", controller.buscar, methods=["GET"])
    bp.add_url_rule("/tasks/<int:task_id>", "update_task", controller.atualizar, methods=["PUT"])
    bp.add_url_rule("/tasks/<int:task_id>", "delete_task", controller.remover, methods=["DELETE"])

    return bp
