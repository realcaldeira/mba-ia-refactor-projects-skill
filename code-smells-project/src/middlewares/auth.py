"""Autenticação por token assinado.

A infraestrutura existe e é usada pelo login; aplicá-la como obrigatória em uma rota é
uma decisão de contrato — basta envolver a view com `requer_autenticacao`.
"""
import hashlib
import hmac
import json
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import g, request

from src.middlewares.errors import NaoAutorizado, Proibido


def _assinar(conteudo, segredo):
    return hmac.new(segredo.encode(), conteudo, hashlib.sha256).digest()


def _b64(dados):
    return urlsafe_b64encode(dados).rstrip(b"=")


def _unb64(texto):
    return urlsafe_b64decode(texto + b"=" * (-len(texto) % 4))


def gerar_token(usuario, segredo, ttl_horas=8):
    """Token assinado com HMAC-SHA256 e expiração — substitui o token previsível."""
    payload = {
        "sub": usuario["id"],
        "tipo": usuario.get("tipo", "cliente"),
        "exp": (datetime.now(timezone.utc) + timedelta(hours=ttl_horas)).timestamp(),
    }
    corpo = _b64(json.dumps(payload, separators=(",", ":")).encode())
    return f"{corpo.decode()}.{_b64(_assinar(corpo, segredo)).decode()}"


def validar_token(token, segredo):
    try:
        corpo, assinatura = token.encode().split(b".")
    except ValueError as exc:
        raise NaoAutorizado("Token malformado") from exc

    if not hmac.compare_digest(_unb64(assinatura), _assinar(corpo, segredo)):
        raise NaoAutorizado("Token inválido")

    payload = json.loads(_unb64(corpo))
    if payload.get("exp", 0) < datetime.now(timezone.utc).timestamp():
        raise NaoAutorizado("Token expirado")
    return payload


def requer_autenticacao(segredo):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            cabecalho = request.headers.get("Authorization", "")
            if not cabecalho.startswith("Bearer "):
                raise NaoAutorizado("Token ausente")
            g.usuario = validar_token(cabecalho[7:], segredo)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def requer_papel(papel):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if getattr(g, "usuario", {}).get("tipo") != papel:
                raise Proibido("Permissão insuficiente")
            return fn(*args, **kwargs)

        return wrapper

    return decorator
