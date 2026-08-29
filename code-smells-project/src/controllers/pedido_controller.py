import logging
from flask import jsonify, request
from src.models.pedido_model import STATUS_APROVADO, STATUS_CANCELADO
log = logging.getLogger(__name__)

class PedidoController:

    def __init__(self, pedidos, notificador):
        self._pedidos = pedidos
        self._notificador = notificador

    def criar(self):
        dados = request.get_json(silent=True) or {}
        resultado = self._pedidos.criar(dados.get('usuario_id'), dados.get('itens', []))
        self._notificador.pedido_criado(resultado['pedido_id'], dados.get('usuario_id'))
        return (jsonify({'dados': resultado, 'sucesso': True, 'mensagem': 'Pedido criado com sucesso'}), 201)

    def listar(self):
        return (jsonify({'dados': self._pedidos.listar(), 'sucesso': True}), 200)

    def listar_por_usuario(self, usuario_id):
        return (jsonify({'dados': self._pedidos.listar_por_usuario(usuario_id), 'sucesso': True}), 200)

    def atualizar_status(self, pedido_id):
        dados = request.get_json(silent=True) or {}
        novo_status = dados.get('status', '')
        self._pedidos.atualizar_status(pedido_id, novo_status)
        if novo_status == STATUS_APROVADO:
            self._notificador.pedido_aprovado(pedido_id)
        elif novo_status == STATUS_CANCELADO:
            self._notificador.pedido_cancelado(pedido_id)
        return (jsonify({'sucesso': True, 'mensagem': 'Status atualizado'}), 200)
