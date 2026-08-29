'use strict';

class ErroDominio extends Error {
  constructor(mensagem, status = 400) {
    super(mensagem);
    this.name = this.constructor.name;
    this.status = status;
  }
}

class DadosInvalidos extends ErroDominio {
  constructor(mensagem = 'Bad Request') {
    super(mensagem, 400);
  }
}

class NaoAutorizado extends ErroDominio {
  constructor(mensagem = 'Não autorizado') {
    super(mensagem, 401);
  }
}

class Proibido extends ErroDominio {
  constructor(mensagem = 'Permissão insuficiente') {
    super(mensagem, 403);
  }
}

class NaoEncontrado extends ErroDominio {
  constructor(mensagem = 'Recurso não encontrado') {
    super(mensagem, 404);
  }
}

class Conflito extends ErroDominio {
  constructor(mensagem = 'Conflito') {
    super(mensagem, 409);
  }
}

module.exports = { ErroDominio, DadosInvalidos, NaoAutorizado, Proibido, NaoEncontrado, Conflito };
