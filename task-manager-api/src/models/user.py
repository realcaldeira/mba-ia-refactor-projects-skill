from datetime import datetime, timezone
from werkzeug.security import check_password_hash, generate_password_hash
from src.database import db
from src.middlewares.errors import Conflito
from src.utils.constants import PAPEL_ADMIN, PAPEL_USUARIO

def agora():
    return datetime.now(timezone.utc)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=PAPEL_USUARIO)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=agora)

    def to_dict(self, incluir_contagem=False):
        dados = {'id': self.id, 'name': self.name, 'email': self.email, 'role': self.role, 'active': self.active, 'created_at': str(self.created_at)}
        if incluir_contagem:
            dados['task_count'] = len(self.tasks)
        return dados

    def set_password(self, senha):
        self.password = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.password, senha)

    def is_admin(self):
        return self.role == PAPEL_ADMIN

    @classmethod
    def buscar(cls, user_id):
        return db.session.get(cls, user_id)

    @classmethod
    def listar(cls):
        return db.session.execute(db.select(cls).order_by(cls.id)).scalars().all()

    @classmethod
    def por_email(cls, email):
        return db.session.execute(db.select(cls).filter_by(email=email)).scalars().first()

    @classmethod
    def total(cls):
        return db.session.execute(db.select(db.func.count(cls.id))).scalar_one()

    @classmethod
    def garantir_email_livre(cls, email, ignorar_id=None):
        existente = cls.por_email(email)
        if existente and existente.id != ignorar_id:
            raise Conflito('Email já cadastrado')
        return email
