"""Task: a regra de atraso e as consultas da entidade vivem aqui.

Antes, o trio de `if` que decide se uma task está atrasada aparecia sete vezes em cinco arquivos.
"""
from datetime import datetime, timezone

from src.database import db
from src.utils.constants import PRIORIDADE_PADRAO, STATUS_FINAIS, STATUS_PENDENTE


def agora():
    return datetime.now(timezone.utc)


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=STATUS_PENDENTE)
    priority = db.Column(db.Integer, default=PRIORIDADE_PADRAO)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=agora)
    updated_at = db.Column(db.DateTime, default=agora, onupdate=agora)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship("User", backref=db.backref("tasks", cascade="all, delete-orphan"))
    category = db.relationship("Category", backref="tasks")

    def is_overdue(self):
        """Única definição de 'task atrasada' no projeto."""
        if self.due_date is None or self.status in STATUS_FINAIS:
            return False
        limite = self.due_date
        if limite.tzinfo is None:
            limite = limite.replace(tzinfo=timezone.utc)
        return limite < datetime.now(timezone.utc)

    def to_dict(self, com_relacionamentos=False):
        dados = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "user_id": self.user_id,
            "category_id": self.category_id,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "due_date": str(self.due_date) if self.due_date else None,
            "tags": self.tags.split(",") if self.tags else [],
        }
        if com_relacionamentos:
            dados["overdue"] = self.is_overdue()
            dados["user_name"] = self.user.name if self.user else None
            dados["category_name"] = self.category.name if self.category else None
        return dados

    def resumo(self):
        """Projeção usada em GET /users/<id>/tasks."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "created_at": str(self.created_at),
            "due_date": str(self.due_date) if self.due_date else None,
            "overdue": self.is_overdue(),
        }

    # --- consultas da entidade ---

    @classmethod
    def buscar(cls, task_id):
        return db.session.get(cls, task_id)

    @classmethod
    def listar(cls, com_relacionamentos=False):
        consulta = db.select(cls).order_by(cls.id)
        if com_relacionamentos:
            # Carrega usuário e categoria junto: elimina as 2 queries por task do N+1.
            consulta = consulta.options(db.selectinload(cls.user), db.selectinload(cls.category))
        return db.session.execute(consulta).scalars().all()

    @classmethod
    def por_usuario(cls, user_id):
        return db.session.execute(db.select(cls).filter_by(user_id=user_id).order_by(cls.id)).scalars().all()

    @classmethod
    def buscar_com_filtros(cls, termo=None, status=None, prioridade=None, user_id=None):
        consulta = db.select(cls)
        if termo:
            consulta = consulta.filter(
                db.or_(cls.title.like(f"%{termo}%"), cls.description.like(f"%{termo}%"))
            )
        if status:
            consulta = consulta.filter(cls.status == status)
        if prioridade:
            consulta = consulta.filter(cls.priority == int(prioridade))
        if user_id:
            consulta = consulta.filter(cls.user_id == int(user_id))
        return db.session.execute(consulta.order_by(cls.id)).scalars().all()

    @classmethod
    def total(cls):
        return db.session.execute(db.select(db.func.count(cls.id))).scalar_one()

    @classmethod
    def contagem_por_status(cls):
        """Um GROUP BY no lugar de uma consulta COUNT por status."""
        linhas = db.session.execute(
            db.select(cls.status, db.func.count(cls.id)).group_by(cls.status)
        ).all()
        return {status: total for status, total in linhas}

    @classmethod
    def contagem_por_prioridade(cls):
        linhas = db.session.execute(
            db.select(cls.priority, db.func.count(cls.id)).group_by(cls.priority)
        ).all()
        return {prioridade: total for prioridade, total in linhas}

    @classmethod
    def atrasadas(cls):
        """Filtra no banco o que dava para filtrar, e confirma a regra no model."""
        candidatas = db.session.execute(
            db.select(cls).filter(cls.due_date.isnot(None), cls.status.notin_(STATUS_FINAIS))
        ).scalars().all()
        return [t for t in candidatas if t.is_overdue()]

    @classmethod
    def criadas_desde(cls, momento):
        return db.session.execute(
            db.select(db.func.count(cls.id)).filter(cls.created_at >= momento)
        ).scalar_one()

    @classmethod
    def concluidas_desde(cls, momento, status_concluida):
        return db.session.execute(
            db.select(db.func.count(cls.id)).filter(
                cls.status == status_concluida, cls.updated_at >= momento
            )
        ).scalar_one()

    @classmethod
    def produtividade_por_usuario(cls, status_concluida):
        """Total e concluídas por usuário em uma consulta, no lugar de uma por usuário."""
        linhas = db.session.execute(
            db.select(
                cls.user_id,
                db.func.count(cls.id),
                db.func.sum(db.case((cls.status == status_concluida, 1), else_=0)),
            ).group_by(cls.user_id)
        ).all()
        return {user_id: (total, concluidas or 0) for user_id, total, concluidas in linhas}
