import logging
log = logging.getLogger(__name__)

class NotificadorLog:

    def pedido_criado(self, pedido_id, usuario_id):
        log.info('notificação: pedido criado', extra={'pedido_id': pedido_id, 'usuario_id': usuario_id})

    def pedido_aprovado(self, pedido_id):
        log.info('notificação: pedido aprovado, preparar envio', extra={'pedido_id': pedido_id})

    def pedido_cancelado(self, pedido_id):
        log.info('notificação: pedido cancelado, devolver estoque', extra={'pedido_id': pedido_id})
