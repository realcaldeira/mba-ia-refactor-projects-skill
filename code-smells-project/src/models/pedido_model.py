"""Pedido: transação, baixa de estoque atômica e leitura sem N+1."""
from src.middlewares.errors import DadosInvalidos
from src.models.base_model import BaseModel

STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_ENVIADO = "enviado"
STATUS_ENTREGUE = "entregue"
STATUS_CANCELADO = "cancelado"
STATUS_VALIDOS = (STATUS_PENDENTE, STATUS_APROVADO, STATUS_ENVIADO, STATUS_ENTREGUE, STATUS_CANCELADO)

# Uma consulta com JOIN no lugar do N+1+M: pedidos, itens e nomes de produto de uma vez.
_SELECT_COM_ITENS = """
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
      FROM pedidos p
      LEFT JOIN itens_pedido i ON i.pedido_id = p.id
      LEFT JOIN produtos pr    ON pr.id = i.produto_id
"""


def _cabecalho(linha):
    return {
        "id": linha["id"],
        "usuario_id": linha["usuario_id"],
        "status": linha["status"],
        "total": linha["total"],
        "criado_em": linha["criado_em"],
        "itens": [],
    }


def _item(linha):
    return {
        "produto_id": linha["produto_id"],
        "produto_nome": linha["produto_nome"] if linha["produto_nome"] is not None else "Desconhecido",
        "quantidade": linha["quantidade"],
        "preco_unitario": linha["preco_unitario"],
    }


def validar_status(status):
    if status not in STATUS_VALIDOS:
        raise DadosInvalidos("Status inválido")
    return status


class PedidoModel(BaseModel):
    def _agrupar(self, linhas):
        pedidos = {}
        for linha in linhas:
            pedido = pedidos.setdefault(linha["id"], _cabecalho(linha))
            if linha["produto_id"] is not None:
                pedido["itens"].append(_item(linha))
        return list(pedidos.values())

    def listar(self):
        return self._agrupar(self.query_all(f"{_SELECT_COM_ITENS} ORDER BY p.id"))

    def listar_por_usuario(self, usuario_id):
        return self._agrupar(
            self.query_all(f"{_SELECT_COM_ITENS} WHERE p.usuario_id = ? ORDER BY p.id", (usuario_id,))
        )

    def criar(self, usuario_id, itens):
        """Cria o pedido inteiro em uma transação; falha em qualquer passo desfaz tudo."""
        if not usuario_id:
            raise DadosInvalidos("Usuario ID é obrigatório")
        if not itens:
            raise DadosInvalidos("Pedido deve ter pelo menos 1 item")

        with self._db:
            total = 0.0
            for item in itens:
                produto = self.query_one(
                    "SELECT id, nome, preco, estoque FROM produtos WHERE id = ?", (item["produto_id"],)
                )
                if produto is None:
                    raise DadosInvalidos(f"Produto {item['produto_id']} não encontrado")
                if produto["estoque"] < item["quantidade"]:
                    raise DadosInvalidos(f"Estoque insuficiente para {produto['nome']}")
                total += produto["preco"] * item["quantidade"]

            cursor = self.executar(
                "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
                (usuario_id, STATUS_PENDENTE, total),
            )
            pedido_id = cursor.lastrowid

            for item in itens:
                produto = self.query_one("SELECT preco FROM produtos WHERE id = ?", (item["produto_id"],))
                self.executar(
                    "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) "
                    "VALUES (?, ?, ?, ?)",
                    (pedido_id, item["produto_id"], item["quantidade"], produto["preco"]),
                )
                # Baixa condicional: fecha a janela entre a verificação e a escrita.
                afetadas = self.executar(
                    "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                    (item["quantidade"], item["produto_id"], item["quantidade"]),
                ).rowcount
                if afetadas == 0:
                    raise DadosInvalidos("Estoque alterado durante a criação do pedido")

        return {"pedido_id": pedido_id, "total": total}

    def atualizar_status(self, pedido_id, novo_status):
        validar_status(novo_status)
        self.executar("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))
        self.commit()
        return True

    def contar(self):
        return self.query_one("SELECT COUNT(*) AS n FROM pedidos")["n"]
