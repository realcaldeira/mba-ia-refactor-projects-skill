"""Categoria: entidade simples com suas próprias consultas."""
from datetime import datetime, timezone

from src.database import db
from src.utils.constants import COR_PADRAO


def agora():
    return datetime.now(timezone.utc)


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    color = db.Column(db.String(7), default=COR_PADRAO)
    created_at = db.Column(db.DateTime, default=agora)

    def to_dict(self, task_count=None):
        dados = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "created_at": str(self.created_at),
        }
        if task_count is not None:
            dados["task_count"] = task_count
        return dados

    @classmethod
    def buscar(cls, category_id):
        return db.session.get(cls, category_id)

    @classmethod
    def listar(cls):
        return db.session.execute(db.select(cls).order_by(cls.id)).scalars().all()

    @classmethod
    def total(cls):
        return db.session.execute(db.select(db.func.count(cls.id))).scalar_one()

    @classmethod
    def contagem_de_tasks(cls):
        """Uma consulta agregada no lugar de um COUNT por categoria."""
        from src.models.task import Task

        linhas = db.session.execute(
            db.select(Task.category_id, db.func.count(Task.id)).group_by(Task.category_id)
        ).all()
        return {category_id: total for category_id, total in linhas}
