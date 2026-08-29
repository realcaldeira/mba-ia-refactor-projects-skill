'use strict';

const { ErroDominio } = require('./errors');

/**
 * Tratamento centralizado. Depois dele existir, nenhum controller precisa de try/catch
 * de infraestrutura — basta chamar next(erro).
 */
function criarErrorHandler(logger) {
  return function errorHandler(erro, _req, res, _next) {
    if (erro instanceof ErroDominio) {
      return res.status(erro.status).send(erro.message);
    }
    // O detalhe fica no log; o cliente recebe apenas a mensagem genérica.
    logger.error('erro não tratado', { mensagem: erro.message, stack: erro.stack });
    return res.status(500).send('Erro interno');
  };
}

function rotaNaoEncontrada(_req, res) {
  return res.status(404).send('Recurso não encontrado');
}

module.exports = { criarErrorHandler, rotaNaoEncontrada };
