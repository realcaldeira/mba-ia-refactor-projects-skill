"""Instância do ORM. A configuração e o binding ficam com a application factory."""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
