import hashlib
import os
from dotenv import load_dotenv
load_dotenv()

def _bool(valor, padrao=False):
    if valor is None:
        return padrao
    return valor.strip().lower() in ('1', 'true', 'yes', 'on')

def _texto(nome, padrao):
    valor = os.getenv(nome)
    if valor is None or not valor.strip():
        return padrao
    return valor

class Settings:
    SECRET_KEY = _texto('SECRET_KEY', hashlib.sha256(b'desafio-skills-dev-key').hexdigest())
    DEBUG = _bool(os.getenv('FLASK_DEBUG'), False)
    HOST = _texto('HOST', '127.0.0.1')
    PORT = int(_texto('PORT', '5000'))
    DB_PATH = _texto('DB_PATH', 'loja.db')
    CORS_ORIGINS = [o.strip() for o in _texto('CORS_ORIGINS', 'http://localhost:3000').split(',') if o.strip()]
    LOG_LEVEL = _texto('LOG_LEVEL', 'INFO')
    TOKEN_TTL_HORAS = int(_texto('TOKEN_TTL_HORAS', '8'))
    AMBIENTE = _texto('AMBIENTE', 'desenvolvimento')
    AUTH_REQUIRED = _bool(os.getenv('AUTH_REQUIRED'), False)
    VERSAO = '2.0.0'

    @classmethod
    def validar(cls):
        if not cls.SECRET_KEY.strip():
            raise RuntimeError('SECRET_KEY não pode ser vazia')
        if cls.AMBIENTE == 'producao' and cls.SECRET_KEY == hashlib.sha256(b'desafio-skills-dev-key').hexdigest():
            raise RuntimeError('SECRET_KEY precisa ser definida fora de desenvolvimento')
        if cls.AMBIENTE == 'producao' and cls.DEBUG:
            raise RuntimeError('DEBUG não pode estar ativo em produção')
        return cls
settings = Settings()
