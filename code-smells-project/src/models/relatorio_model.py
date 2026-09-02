from src.models.base_model import BaseModel
from src.models.pedido_model import STATUS_APROVADO, STATUS_CANCELADO, STATUS_PENDENTE
FAIXAS_DESCONTO = ((10000, 0.1), (5000, 0.05), (1000, 0.02))

def calcular_desconto(faturamento):
    for piso, taxa in FAIXAS_DESCONTO:
        if faturamento > piso:
            return faturamento * taxa
    return 0

class RelatorioModel(BaseModel):

    def vendas(self):
        agregado = self.query_one('\n            SELECT COUNT(*) AS total_pedidos,\n                   COALESCE(SUM(total), 0) AS faturamento,\n                   COALESCE(SUM(status = ?), 0) AS pendentes,\n                   COALESCE(SUM(status = ?), 0) AS aprovados,\n                   COALESCE(SUM(status = ?), 0) AS cancelados\n              FROM pedidos\n            ', (STATUS_PENDENTE, STATUS_APROVADO, STATUS_CANCELADO))
        total_pedidos = agregado['total_pedidos']
        faturamento = agregado['faturamento'] or 0
        desconto = calcular_desconto(faturamento)
        return {'total_pedidos': total_pedidos, 'faturamento_bruto': round(faturamento, 2), 'desconto_aplicavel': round(desconto, 2), 'faturamento_liquido': round(faturamento - desconto, 2), 'pedidos_pendentes': agregado['pendentes'], 'pedidos_aprovados': agregado['aprovados'], 'pedidos_cancelados': agregado['cancelados'], 'ticket_medio': round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0}
