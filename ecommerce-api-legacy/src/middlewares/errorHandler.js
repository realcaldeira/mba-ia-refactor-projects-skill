'use strict';

const { ErroDominio } = require('./errors');

function criarErrorHandler(logger) {
  return function errorHandler(erro, _req, res, _next) {
    if (erro instanceof ErroDominio) {
      return res.status(erro.status).send(erro.message);
    }

    logger.error('erro não tratado', { mensagem: erro.message, stack: erro.stack });
    return res.status(500).send('Erro interno');
  };
}

function rotaNaoEncontrada(_req, res) {
  return res.status(404).send('Recurso não encontrado');
}

module.exports = { criarErrorHandler, rotaNaoEncontrada };
