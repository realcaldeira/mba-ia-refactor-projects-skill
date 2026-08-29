import logging
from flask import g, jsonify, request
from src.config.settings import settings
from src.database import db
from src.middlewares.auth import gerar_token
from src.models import Task, User
from src.utils import validators
from src.utils.constants import PAPEL_ADMIN, PAPEL_USUARIO
log = logging.getLogger(__name__)

class UserController:

    def __init__(self, segredo, token_ttl_horas=8):
        self._segredo = segredo
        self._ttl = token_ttl_horas

    def listar(self):
        return (jsonify([u.to_dict(incluir_contagem=True) for u in User.listar()]), 200)

    def buscar(self, user_id):
        usuario = User.buscar(user_id)
        if not usuario:
            return (jsonify({'error': 'Usuário não encontrado'}), 404)
        dados = usuario.to_dict()
        dados['tasks'] = [t.to_dict() for t in Task.por_usuario(user_id)]
        return (jsonify(dados), 200)

    def criar(self):
        dados = validators.exigir_corpo(request.get_json(silent=True))
        nome = dados.get('name')
        if not nome:
            from src.middlewares.errors import DadosInvalidos
            raise DadosInvalidos('Nome é obrigatório')
        email = validators.validar_email(dados.get('email'))
        senha = validators.validar_senha(dados.get('password'))
        if 'role' in dados:
            validators.validar_papel(dados.get('role'))
        User.garantir_email_livre(email)
        usuario = User(name=nome, email=email, role=PAPEL_USUARIO)
        usuario.set_password(senha)
        db.session.add(usuario)
        db.session.commit()
        log.info('usuário criado', extra={'usuario_id': usuario.id})
        return (jsonify(usuario.to_dict()), 201)

    def atualizar(self, user_id):
        usuario = User.buscar(user_id)
        if not usuario:
            return (jsonify({'error': 'Usuário não encontrado'}), 404)
        dados = validators.exigir_corpo(request.get_json(silent=True))
        if 'name' in dados:
            usuario.name = dados['name']
        if 'email' in dados:
            email = validators.validar_email(dados['email'])
            User.garantir_email_livre(email, ignorar_id=user_id)
            usuario.email = email
        if 'password' in dados:
            usuario.set_password(validators.validar_senha(dados['password'], mensagem='Senha muito curta'))
        if 'role' in dados:
            validators.validar_papel(dados['role'])
            if settings.AUTH_REQUIRED and getattr(g, 'usuario', {}).get('role') == PAPEL_ADMIN:
                usuario.role = dados['role']
        if 'active' in dados and settings.AUTH_REQUIRED and (getattr(g, 'usuario', {}).get('role') == PAPEL_ADMIN):
            usuario.active = dados['active']
        db.session.commit()
        return (jsonify(usuario.to_dict()), 200)

    def remover(self, user_id):
        usuario = User.buscar(user_id)
        if not usuario:
            return (jsonify({'error': 'Usuário não encontrado'}), 404)
        db.session.delete(usuario)
        db.session.commit()
        log.info('usuário removido', extra={'usuario_id': user_id})
        return (jsonify({'message': 'Usuário deletado com sucesso'}), 200)

    def tasks_do_usuario(self, user_id):
        if not User.buscar(user_id):
            return (jsonify({'error': 'Usuário não encontrado'}), 404)
        return (jsonify([t.resumo() for t in Task.por_usuario(user_id)]), 200)

    def login(self):
        dados = validators.exigir_corpo(request.get_json(silent=True))
        email, senha = (dados.get('email'), dados.get('password'))
        if not email or not senha:
            return (jsonify({'error': 'Email e senha são obrigatórios'}), 400)
        usuario = User.por_email(email)
        if not usuario or not usuario.check_password(senha):
            log.info('tentativa de login recusada')
            return (jsonify({'error': 'Credenciais inválidas'}), 401)
        if not usuario.active:
            return (jsonify({'error': 'Usuário inativo'}), 403)
        log.info('login bem-sucedido', extra={'usuario_id': usuario.id})
        return (jsonify({'message': 'Login realizado com sucesso', 'user': usuario.to_dict(), 'token': gerar_token(usuario, self._segredo, self._ttl)}), 200)
