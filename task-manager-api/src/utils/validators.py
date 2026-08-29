"""Validação de entrada — uma fonte da verdade, usada por criação e atualização.

Substitui os blocos duplicados nas rotas e o `process_task_data` que existia em utils/helpers.py
e nunca era chamado.
"""
from datetime import datetime

from src.middlewares.errors import DadosInvalidos
from src.utils.constants import (
    FORMATO_DATA,
    PAPEIS_VALIDOS,
    PRIORIDADE_MAX,
    PRIORIDADE_MIN,
    SENHA_MIN,
    STATUS_VALIDOS,
    TITULO_MAX,
    TITULO_MIN,
)

EMAIL_REGEX = r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$"


def exigir_corpo(dados):
    if not dados:
        raise DadosInvalidos("Dados inválidos")
    return dados


def validar_titulo(titulo, obrigatorio=True):
    if titulo is None:
        if obrigatorio:
            raise DadosInvalidos("Título é obrigatório")
        return None
    if not titulo:
        raise DadosInvalidos("Título é obrigatório")
    if len(titulo) < TITULO_MIN:
        raise DadosInvalidos("Título muito curto")
    if len(titulo) > TITULO_MAX:
        raise DadosInvalidos("Título muito longo")
    return titulo


def validar_status(status):
    if status not in STATUS_VALIDOS:
        raise DadosInvalidos("Status inválido")
    return status


def validar_prioridade(prioridade):
    if prioridade is None or prioridade < PRIORIDADE_MIN or prioridade > PRIORIDADE_MAX:
        raise DadosInvalidos(f"Prioridade deve ser entre {PRIORIDADE_MIN} e {PRIORIDADE_MAX}")
    return prioridade


def validar_papel(papel):
    if papel not in PAPEIS_VALIDOS:
        raise DadosInvalidos("Role inválido")
    return papel


def validar_senha(senha, mensagem="Senha deve ter no mínimo 4 caracteres"):
    if not senha:
        raise DadosInvalidos("Senha é obrigatória")
    if len(senha) < SENHA_MIN:
        raise DadosInvalidos(mensagem)
    return senha


def validar_email(email):
    import re

    if not email:
        raise DadosInvalidos("Email é obrigatório")
    if not re.match(EMAIL_REGEX, email):
        raise DadosInvalidos("Email inválido")
    return email


def converter_data(valor, mensagem="Formato de data inválido. Use YYYY-MM-DD"):
    if not valor:
        return None
    try:
        return datetime.strptime(valor, FORMATO_DATA)
    except (TypeError, ValueError) as exc:
        raise DadosInvalidos(mensagem) from exc


def normalizar_tags(tags):
    if tags is None:
        return None
    return ",".join(tags) if isinstance(tags, list) else tags
