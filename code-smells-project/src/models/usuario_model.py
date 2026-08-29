"""Usuário: credenciais com hash e serialização sem campo sensível."""
from werkzeug.security import check_password_hash, generate_password_hash

from src.middlewares.errors import DadosInvalidos
from src.models.base_model import BaseModel

TIPO_PADRAO = "cliente"
TIPO_ADMIN = "admin"
# A senha nunca aparece nesta lista: é o que impede o vazamento por serialização.
CAMPOS_PUBLICOS = ("id", "nome", "email", "tipo", "criado_em")

_SELECT = "SELECT id, nome, email, tipo, criado_em FROM usuarios"


def serializar(linha):
    return {campo: linha[campo] for campo in CAMPOS_PUBLICOS}


class UsuarioModel(BaseModel):
    def listar(self):
        return [serializar(u) for u in self.query_all(_SELECT)]

    def buscar_por_id(self, usuario_id):
        linha = self.query_one(f"{_SELECT} WHERE id = ?", (usuario_id,))
        return serializar(linha) if linha else None

    def criar(self, nome, email, senha, tipo=TIPO_PADRAO):
        if not nome or not email or not senha:
            raise DadosInvalidos("Nome, email e senha são obrigatórios")
        cursor = self.executar(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, generate_password_hash(senha), tipo),
        )
        self.commit()
        return cursor.lastrowid

    def autenticar(self, email, senha):
        """Devolve o usuário público ou None — sem revelar qual dos dois campos falhou."""
        linha = self.query_one("SELECT id, nome, email, tipo, senha FROM usuarios WHERE email = ?", (email,))
        if linha is None or not check_password_hash(linha["senha"], senha):
            return None
        return {"id": linha["id"], "nome": linha["nome"], "email": linha["email"], "tipo": linha["tipo"]}

    def contar(self):
        return self.query_one("SELECT COUNT(*) AS n FROM usuarios")["n"]
