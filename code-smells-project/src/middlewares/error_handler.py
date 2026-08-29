import logging
from flask import jsonify
from src.middlewares.errors import ErroDominio
log = logging.getLogger(__name__)

def registrar_error_handler(app):

    @app.errorhandler(ErroDominio)
    def _erro_de_dominio(exc):
        return (jsonify({'erro': exc.mensagem, 'sucesso': False}), exc.status)

    @app.errorhandler(404)
    def _rota_inexistente(_exc):
        return (jsonify({'erro': 'Recurso não encontrado', 'sucesso': False}), 404)

    @app.errorhandler(405)
    def _metodo_invalido(_exc):
        return (jsonify({'erro': 'Método não permitido', 'sucesso': False}), 405)

    @app.errorhandler(Exception)
    def _erro_inesperado(exc):
        log.exception('erro não tratado: %s', exc)
        return (jsonify({'erro': 'Erro interno', 'sucesso': False}), 500)
    return app
