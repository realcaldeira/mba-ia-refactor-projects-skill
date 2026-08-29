"""Configuração da aplicação — tudo que muda por ambiente vive aqui."""
import os


def _bool(valor, padrao=False):
    if valor is None:
        return padrao
    return valor.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    """Lê variáveis de ambiente com default seguro para desenvolvimento."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    DEBUG = _bool(os.getenv("FLASK_DEBUG"), False)
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    DB_PATH = os.getenv("DB_PATH", "loja.db")
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    TOKEN_TTL_HORAS = int(os.getenv("TOKEN_TTL_HORAS", "8"))
    AMBIENTE = os.getenv("AMBIENTE", "desenvolvimento")
    VERSAO = "2.0.0"

    @classmethod
    def validar(cls):
        """Falha alto quando um segredo de desenvolvimento chega em produção."""
        if cls.AMBIENTE == "producao" and cls.SECRET_KEY == "dev-secret-change-me":
            raise RuntimeError("SECRET_KEY precisa ser definida fora de desenvolvimento")
        if cls.AMBIENTE == "producao" and cls.DEBUG:
            raise RuntimeError("DEBUG não pode estar ativo em produção")
        return cls


settings = Settings()
