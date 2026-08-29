"""Configuração da aplicação — tudo que muda por ambiente vive aqui."""
import os

from dotenv import load_dotenv

load_dotenv()


def _bool(valor, padrao=False):
    if valor is None:
        return padrao
    return valor.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///tasks.db")
    DEBUG = _bool(os.getenv("FLASK_DEBUG"), False)
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    TOKEN_TTL_HORAS = int(os.getenv("TOKEN_TTL_HORAS", "8"))
    AMBIENTE = os.getenv("AMBIENTE", "desenvolvimento")
    VERSAO = "2.0"

    SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

    @classmethod
    def validar(cls):
        if cls.AMBIENTE != "producao":
            return cls
        if cls.SECRET_KEY == "dev-secret-change-me":
            raise RuntimeError("SECRET_KEY precisa ser definida fora de desenvolvimento")
        if cls.DEBUG:
            raise RuntimeError("DEBUG não pode estar ativo em produção")
        return cls


settings = Settings()
