import logging
from flask import jsonify, request
from src.middlewares.auth import gerar_token
log = logging.getLogger(__name__)

class UsuarioController:

    def __init__(self, usuarios, segredo, token_ttl_horas=8):
        self._usuarios = usuarios
        self._segredo = segredo
        self._ttl = token_ttl_horas

    def listar(self):
        return (jsonify({'dados': self._usuarios.listar(), 'sucesso': True}), 200)

    def buscar(self, id):
        usuario = self._usuarios.buscar_por_id(id)
        if not usuario:
            return (jsonify({'erro': 'Usuário não encontrado', 'sucesso': False}), 404)
        return (jsonify({'dados': usuario, 'sucesso': True}), 200)

    def criar(self):
        dados = request.get_json(silent=True) or {}
        usuario_id = self._usuarios.criar(dados.get('nome', ''), dados.get('email', ''), dados.get('senha', ''))
        log.info('usuário criado', extra={'usuario_id': usuario_id})
        return (jsonify({'dados': {'id': usuario_id}, 'sucesso': True}), 201)

    def login(self):
        dados = request.get_json(silent=True) or {}
        email, senha = (dados.get('email', ''), dados.get('senha', ''))
        if not email or not senha:
            return (jsonify({'erro': 'Email e senha são obrigatórios', 'sucesso': False}), 400)
        usuario = self._usuarios.autenticar(email, senha)
        if not usuario:
            log.info('tentativa de login recusada')
            return (jsonify({'erro': 'Email ou senha inválidos', 'sucesso': False}), 401)
        log.info('login bem-sucedido', extra={'usuario_id': usuario['id']})
        return (jsonify({'dados': usuario, 'token': gerar_token(usuario, self._segredo, self._ttl), 'sucesso': True, 'mensagem': 'Login OK'}), 200)
