"""Tratamento centralizado — substitui os 12 blocos `except:` nus das rotas."""
import logging

from flask import jsonify

from src.database import db
from src.middlewares.errors import ErroDominio

log = logging.getLogger(__name__)


def registrar_error_handler(app):
    @app.errorhandler(ErroDominio)
    def _erro_de_dominio(exc):
        return jsonify({"error": exc.mensagem}), exc.status

    @app.errorhandler(404)
    def _rota_inexistente(_exc):
        return jsonify({"error": "Recurso não encontrado"}), 404

    @app.errorhandler(405)
    def _metodo_invalido(_exc):
        return jsonify({"error": "Método não permitido"}), 405

    @app.errorhandler(Exception)
    def _erro_inesperado(exc):
        # Desfaz a transação pendente antes de responder — antes cada rota fazia isso à mão.
        db.session.rollback()
        log.exception("erro não tratado: %s", exc)
        return jsonify({"error": "Erro interno"}), 500

    return app
