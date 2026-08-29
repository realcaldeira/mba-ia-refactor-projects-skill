"""Caso de uso de relatório de vendas."""
from flask import jsonify


class RelatorioController:
    def __init__(self, relatorios):
        self._relatorios = relatorios

    def vendas(self):
        return jsonify({"dados": self._relatorios.vendas(), "sucesso": True}), 200
