"""Health check e index. Nenhum dado de configuração sensível é exposto."""
from flask import jsonify


class HealthController:
    def __init__(self, produtos, usuarios, pedidos, versao, ambiente):
        self._produtos = produtos
        self._usuarios = usuarios
        self._pedidos = pedidos
        self._versao = versao
        self._ambiente = ambiente

    def check(self):
        return jsonify(
            {
                "status": "ok",
                "database": "connected",
                "counts": {
                    "produtos": self._produtos.contar(),
                    "usuarios": self._usuarios.contar(),
                    "pedidos": self._pedidos.contar(),
                },
                "versao": self._versao,
                "ambiente": self._ambiente,
            }
        ), 200

    def index(self):
        return jsonify(
            {
                "mensagem": "Bem-vindo à API da Loja",
                "versao": self._versao,
                "endpoints": {
                    "produtos": "/produtos",
                    "usuarios": "/usuarios",
                    "pedidos": "/pedidos",
                    "login": "/login",
                    "relatorios": "/relatorios/vendas",
                    "health": "/health",
                },
            }
        ), 200
