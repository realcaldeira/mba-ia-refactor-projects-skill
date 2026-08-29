"""Notificações de pedido.

Isolado atrás de uma interface: o controller não sabe se o envio é por e-mail, SMS ou log.
Trocar a implementação (ou usar um duplo em teste) não toca em nenhuma outra camada.
"""
import logging

log = logging.getLogger(__name__)


class NotificadorLog:
    """Implementação padrão: registra a intenção de notificar, sem integração externa."""

    def pedido_criado(self, pedido_id, usuario_id):
        log.info("notificação: pedido criado", extra={"pedido_id": pedido_id, "usuario_id": usuario_id})

    def pedido_aprovado(self, pedido_id):
        log.info("notificação: pedido aprovado, preparar envio", extra={"pedido_id": pedido_id})

    def pedido_cancelado(self, pedido_id):
        log.info("notificação: pedido cancelado, devolver estoque", extra={"pedido_id": pedido_id})
