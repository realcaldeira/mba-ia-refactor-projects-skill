"""Rotas de usuário e login."""
from flask import Blueprint


def criar_blueprint(controller):
    bp = Blueprint("users", __name__)

    bp.add_url_rule("/users", "get_users", controller.listar, methods=["GET"])
    bp.add_url_rule("/users", "create_user", controller.criar, methods=["POST"])
    bp.add_url_rule("/users/<int:user_id>", "get_user", controller.buscar, methods=["GET"])
    bp.add_url_rule("/users/<int:user_id>", "update_user", controller.atualizar, methods=["PUT"])
    bp.add_url_rule("/users/<int:user_id>", "delete_user", controller.remover, methods=["DELETE"])
    bp.add_url_rule("/users/<int:user_id>/tasks", "get_user_tasks", controller.tasks_do_usuario, methods=["GET"])
    bp.add_url_rule("/login", "login", controller.login, methods=["POST"])

    return bp
