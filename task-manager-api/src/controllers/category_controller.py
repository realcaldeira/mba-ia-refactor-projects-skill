"""Casos de uso de categoria."""
from flask import jsonify, request

from src.database import db
from src.middlewares.errors import DadosInvalidos
from src.models import Category
from src.utils import validators
from src.utils.constants import COR_PADRAO


class CategoryController:
    def listar(self):
        contagens = Category.contagem_de_tasks()
        return jsonify(
            [c.to_dict(task_count=contagens.get(c.id, 0)) for c in Category.listar()]
        ), 200

    def criar(self):
        dados = validators.exigir_corpo(request.get_json(silent=True))
        nome = dados.get("name")
        if not nome:
            raise DadosInvalidos("Nome é obrigatório")

        categoria = Category(
            name=nome,
            description=dados.get("description", ""),
            color=dados.get("color", COR_PADRAO),
        )
        db.session.add(categoria)
        db.session.commit()
        return jsonify(categoria.to_dict()), 201

    def atualizar(self, category_id):
        categoria = Category.buscar(category_id)
        if not categoria:
            return jsonify({"error": "Categoria não encontrada"}), 404

        dados = request.get_json(silent=True) or {}
        if "name" in dados:
            categoria.name = dados["name"]
        if "description" in dados:
            categoria.description = dados["description"]
        if "color" in dados:
            categoria.color = dados["color"]

        db.session.commit()
        return jsonify(categoria.to_dict()), 200

    def remover(self, category_id):
        categoria = Category.buscar(category_id)
        if not categoria:
            return jsonify({"error": "Categoria não encontrada"}), 404

        # Desassocia as tasks antes de remover: nada de category_id órfão.
        for tarefa in categoria.tasks:
            tarefa.category_id = None

        db.session.delete(categoria)
        db.session.commit()
        return jsonify({"message": "Categoria deletada"}), 200
