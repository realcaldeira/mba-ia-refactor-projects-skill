'use strict';

/** Exceções de domínio: o status HTTP é atributo do erro, não decisão do controller. */
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

module.exports = { ErroDominio, DadosInvalidos, NaoAutorizado, Proibido, NaoEncontrado };
