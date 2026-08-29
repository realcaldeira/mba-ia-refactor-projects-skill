from src.middlewares.errors import DadosInvalidos, NaoEncontrado
from src.models.base_model import BaseModel
STATUS_PENDENTE = 'pendente'
STATUS_APROVADO = 'aprovado'
STATUS_ENVIADO = 'enviado'
STATUS_ENTREGUE = 'entregue'
STATUS_CANCELADO = 'cancelado'
STATUS_VALIDOS = (STATUS_PENDENTE, STATUS_APROVADO, STATUS_ENVIADO, STATUS_ENTREGUE, STATUS_CANCELADO)
_SELECT_COM_ITENS = '\n    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,\n           i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome\n      FROM pedidos p\n      LEFT JOIN itens_pedido i ON i.pedido_id = p.id\n      LEFT JOIN produtos pr    ON pr.id = i.produto_id\n'

def _cabecalho(linha):
    return {'id': linha['id'], 'usuario_id': linha['usuario_id'], 'status': linha['status'], 'total': linha['total'], 'criado_em': linha['criado_em'], 'itens': []}

def _item(linha):
    return {'produto_id': linha['produto_id'], 'produto_nome': linha['produto_nome'] if linha['produto_nome'] is not None else 'Desconhecido', 'quantidade': linha['quantidade'], 'preco_unitario': linha['preco_unitario']}

def validar_status(status):
    if status not in STATUS_VALIDOS:
        raise DadosInvalidos('Status inválido')
    return status

def _quantidade(item):
    try:
        quantidade = int(item['quantidade'])
    except (KeyError, TypeError, ValueError) as exc:
        raise DadosInvalidos('Quantidade inválida') from exc
    if quantidade < 1:
        raise DadosInvalidos('Quantidade deve ser pelo menos 1')
    return quantidade

def _produto_id(item):
    try:
        return item['produto_id']
    except KeyError as exc:
        raise DadosInvalidos('produto_id é obrigatório') from exc

class PedidoModel(BaseModel):

    def _agrupar(self, linhas):
        pedidos = {}
        for linha in linhas:
            pedido = pedidos.setdefault(linha['id'], _cabecalho(linha))
            if linha['produto_id'] is not None:
                pedido['itens'].append(_item(linha))
        return list(pedidos.values())

    def listar(self):
        return self._agrupar(self.query_all(f'{_SELECT_COM_ITENS} ORDER BY p.id'))

    def listar_por_usuario(self, usuario_id):
        return self._agrupar(self.query_all(f'{_SELECT_COM_ITENS} WHERE p.usuario_id = ? ORDER BY p.id', (usuario_id,)))

    def criar(self, usuario_id, itens):
        if not usuario_id:
            raise DadosInvalidos('Usuario ID é obrigatório')
        if not itens:
            raise DadosInvalidos('Pedido deve ter pelo menos 1 item')
        with self._db:
            total = 0.0
            itens_normalizados = []
            for item in itens:
                produto_id = _produto_id(item)
                quantidade = _quantidade(item)
                produto = self.query_one('SELECT id, nome, preco, estoque FROM produtos WHERE id = ?', (produto_id,))
                if produto is None:
                    raise DadosInvalidos(f'Produto {produto_id} não encontrado')
                if produto['estoque'] < quantidade:
                    raise DadosInvalidos(f"Estoque insuficiente para {produto['nome']}")
                total += produto['preco'] * quantidade
                itens_normalizados.append((produto_id, quantidade, produto['preco']))
            cursor = self.executar('INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)', (usuario_id, STATUS_PENDENTE, total))
            pedido_id = cursor.lastrowid
            for produto_id, quantidade, preco in itens_normalizados:
                self.executar('INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)', (pedido_id, produto_id, quantidade, preco))
                afetadas = self.executar('UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?', (quantidade, produto_id, quantidade)).rowcount
                if afetadas == 0:
                    raise DadosInvalidos('Estoque alterado durante a criação do pedido')
        return {'pedido_id': pedido_id, 'total': total}

    def atualizar_status(self, pedido_id, novo_status):
        validar_status(novo_status)
        with self._db:
            pedido = self.query_one('SELECT id, status FROM pedidos WHERE id = ?', (pedido_id,))
            if pedido is None:
                raise NaoEncontrado('Pedido não encontrado')
            atual = pedido['status']
            if atual == novo_status:
                return True
            if novo_status == STATUS_CANCELADO and atual != STATUS_CANCELADO:
                for item in self.query_all('SELECT produto_id, quantidade FROM itens_pedido WHERE pedido_id = ?', (pedido_id,)):
                    self.executar('UPDATE produtos SET estoque = estoque + ? WHERE id = ?', (item['quantidade'], item['produto_id']))
            afetadas = self.executar('UPDATE pedidos SET status = ? WHERE id = ?', (novo_status, pedido_id)).rowcount
            if afetadas == 0:
                raise NaoEncontrado('Pedido não encontrado')
        return True

    def contar(self):
        return self.query_one('SELECT COUNT(*) AS n FROM pedidos')['n']
