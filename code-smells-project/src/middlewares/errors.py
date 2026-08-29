"""Exceções de domínio. O status HTTP é atributo da exceção, não decisão do model."""


class ErroDominio(Exception):
    status = 400

    def __init__(self, mensagem):
        super().__init__(mensagem)
        self.mensagem = mensagem


class DadosInvalidos(ErroDominio):
    status = 400


class NaoAutorizado(ErroDominio):
    status = 401


class Proibido(ErroDominio):
    status = 403


class NaoEncontrado(ErroDominio):
    status = 404


class Conflito(ErroDominio):
    status = 409
