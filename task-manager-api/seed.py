"""Popula o banco com dados iniciais. Uso: python seed.py"""
from datetime import timedelta

from src.app import create_app
from src.database import db
from src.models import Category, Task, User
from src.models.task import agora

USUARIOS = (
    ("João Silva", "joao@email.com", "1234", "admin"),
    ("Maria Santos", "maria@email.com", "abcd", "user"),
    ("Pedro Oliveira", "pedro@email.com", "pass", "manager"),
)

CATEGORIAS = (
    ("Backend", "Tarefas de backend", "#3498db"),
    ("Frontend", "Tarefas de frontend", "#2ecc71"),
    ("DevOps", "Tarefas de infraestrutura", "#e74c3c"),
    ("Bug", "Correção de bugs", "#e67e22"),
)


def tasks_iniciais(usuarios, categorias):
    momento = agora()
    return (
        {"title": "Implementar autenticação JWT", "description": "Adicionar autenticação real com JWT",
         "status": "pending", "priority": 1, "user_id": usuarios[0].id, "category_id": categorias[0].id,
         "due_date": momento - timedelta(days=3)},
        {"title": "Criar tela de login", "description": "Tela de login responsiva",
         "status": "in_progress", "priority": 2, "user_id": usuarios[1].id, "category_id": categorias[1].id,
         "due_date": momento + timedelta(days=5)},
        {"title": "Configurar CI/CD", "description": "Pipeline com GitHub Actions",
         "status": "done", "priority": 2, "user_id": usuarios[2].id, "category_id": categorias[2].id,
         "tags": "devops,ci,github"},
        {"title": "Corrigir bug no filtro de busca", "description": "Filtro não funciona com caracteres especiais",
         "status": "pending", "priority": 1, "user_id": usuarios[0].id, "category_id": categorias[3].id,
         "due_date": momento - timedelta(days=1)},
        {"title": "Adicionar paginação na API", "description": "Endpoints retornam todos os registros",
         "status": "pending", "priority": 3, "user_id": usuarios[0].id, "category_id": categorias[0].id,
         "due_date": momento + timedelta(days=10)},
        {"title": "Escrever testes unitários", "description": "Cobertura mínima de 80%",
         "status": "pending", "priority": 2, "user_id": usuarios[1].id, "category_id": categorias[0].id},
        {"title": "Documentar API com Swagger", "description": "Gerar documentação automática",
         "status": "cancelled", "priority": 4, "user_id": usuarios[2].id, "category_id": categorias[0].id},
        {"title": "Refatorar models", "description": "Melhorar organização dos models",
         "status": "in_progress", "priority": 3, "user_id": usuarios[1].id, "category_id": categorias[0].id,
         "tags": "refactor,tech-debt"},
        {"title": "Configurar monitoramento", "description": "Prometheus + Grafana",
         "status": "pending", "priority": 4, "user_id": usuarios[2].id, "category_id": categorias[2].id,
         "due_date": momento + timedelta(days=20)},
        {"title": "Melhorar validações de input", "description": "Usar marshmallow ou pydantic",
         "status": "pending", "priority": 3, "user_id": usuarios[0].id, "category_id": categorias[0].id,
         "tags": "improvement,validation"},
    )


def seed_data():
    app = create_app()
    with app.app_context():
        # API 2.0 do SQLAlchemy: `Model.query` é legado.
        for modelo in (Task, User, Category):
            db.session.execute(db.delete(modelo))
        db.session.commit()

        usuarios = []
        for nome, email, senha, papel in USUARIOS:
            usuario = User(name=nome, email=email, role=papel)
            usuario.set_password(senha)   # entra no banco já com hash
            db.session.add(usuario)
            usuarios.append(usuario)

        categorias = [Category(name=n, description=d, color=c) for n, d, c in CATEGORIAS]
        db.session.add_all(categorias)
        db.session.commit()

        db.session.add_all(Task(**dados) for dados in tasks_iniciais(usuarios, categorias))
        db.session.commit()

        print("Seed concluído com sucesso!")
        print(f"  {User.total()} usuários")
        print(f"  {Category.total()} categorias")
        print(f"  {Task.total()} tasks")


if __name__ == "__main__":
    seed_data()
