"""Relatório de vendas: agregação em SQL e a política de desconto como regra de domínio."""
from src.models.base_model import BaseModel
from src.models.pedido_model import STATUS_APROVADO, STATUS_CANCELADO, STATUS_PENDENTE

# Política comercial: faixa de faturamento → percentual de desconto.
FAIXAS_DESCONTO = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))


def calcular_desconto(faturamento):
    for piso, taxa in FAIXAS_DESCONTO:
        if faturamento > piso:
            return faturamento * taxa
    return 0.0


class RelatorioModel(BaseModel):
    def vendas(self):
        # Uma varredura no lugar das cinco consultas separadas.
        agregado = self.query_one(
            """
            SELECT COUNT(*) AS total_pedidos,
                   COALESCE(SUM(total), 0) AS faturamento,
                   COALESCE(SUM(status = ?), 0) AS pendentes,
                   COALESCE(SUM(status = ?), 0) AS aprovados,
                   COALESCE(SUM(status = ?), 0) AS cancelados
              FROM pedidos
            """,
            (STATUS_PENDENTE, STATUS_APROVADO, STATUS_CANCELADO),
        )

        total_pedidos = agregado["total_pedidos"]
        faturamento = agregado["faturamento"] or 0
        desconto = calcular_desconto(faturamento)

        return {
            "total_pedidos": total_pedidos,
            "faturamento_bruto": round(faturamento, 2),
            "desconto_aplicavel": round(desconto, 2),
            "faturamento_liquido": round(faturamento - desconto, 2),
            "pedidos_pendentes": agregado["pendentes"],
            "pedidos_aprovados": agregado["aprovados"],
            "pedidos_cancelados": agregado["cancelados"],
            "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
        }
