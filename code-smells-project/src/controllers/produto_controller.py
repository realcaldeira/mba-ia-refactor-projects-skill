import logging
from flask import jsonify, request
from src.middlewares.errors import NaoEncontrado
from src.models import produto_model
log = logging.getLogger(__name__)

class ProdutoController:

    def __init__(self, produtos):
        self._produtos = produtos

    def listar(self):
        dados = self._produtos.listar(pagina=request.args.get('pagina'), tamanho=request.args.get('tamanho'))
        log.info('produtos listados', extra={'quantidade': len(dados)})
        return (jsonify({'dados': dados, 'sucesso': True}), 200)

    def buscar(self, id):
        produto = self._produtos.buscar_por_id(id)
        if not produto:
            return (jsonify({'erro': 'Produto não encontrado', 'sucesso': False}), 404)
        return (jsonify({'dados': produto, 'sucesso': True}), 200)

    def criar(self):
        dados = produto_model.validar(request.get_json(silent=True))
        produto_id = self._produtos.criar(dados)
        log.info('produto criado', extra={'produto_id': produto_id})
        return (jsonify({'dados': {'id': produto_id}, 'sucesso': True, 'mensagem': 'Produto criado'}), 201)

    def atualizar(self, id):
        if not self._produtos.buscar_por_id(id):
            raise NaoEncontrado('Produto não encontrado')
        dados = produto_model.validar(request.get_json(silent=True))
        self._produtos.atualizar(id, dados)
        return (jsonify({'sucesso': True, 'mensagem': 'Produto atualizado'}), 200)

    def remover(self, id):
        if not self._produtos.buscar_por_id(id):
            raise NaoEncontrado('Produto não encontrado')
        self._produtos.remover(id)
        log.info('produto removido', extra={'produto_id': id})
        return (jsonify({'sucesso': True, 'mensagem': 'Produto deletado'}), 200)

    def pesquisar(self):
        preco_min = request.args.get('preco_min')
        preco_max = request.args.get('preco_max')
        resultados = self._produtos.buscar(termo=request.args.get('q', ''), categoria=request.args.get('categoria'), preco_min=float(preco_min) if preco_min else None, preco_max=float(preco_max) if preco_max else None)
        return (jsonify({'dados': resultados, 'total': len(resultados), 'sucesso': True}), 200)
