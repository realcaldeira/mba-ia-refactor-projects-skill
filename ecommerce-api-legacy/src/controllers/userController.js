'use strict';

const { NaoEncontrado } = require('../middlewares/errors');

class UserController {
  constructor({ usuarios, logger }) {
    this.usuarios = usuarios;
    this.logger = logger;
  }

  remover() {
    return async (req, res, next) => {
      try {
        const { removido, matriculasRemovidas } = await this.usuarios.remover(req.params.id);
        if (!removido) throw new NaoEncontrado('Usuário não encontrado');
        this.logger.info('usuário removido', {
          usuarioId: req.params.id,
          removido,
          matriculasRemovidas,
        });
        return res.send('Usuário deletado, junto com suas matrículas e pagamentos.');
      } catch (erro) {
        return next(erro);
      }
    };
  }
}

module.exports = { UserController };
