'use strict';

const { PagamentoStatus } = require('../models/paymentModel');

/**
 * Integração de pagamento isolada atrás de uma interface.
 *
 * A implementação padrão continua sendo local (o projeto nunca chamou um gateway real), mas
 * agora: a chave vem da config, o número do cartão nunca é logado inteiro, e trocar por um
 * provedor de verdade — ou por um duplo em teste — não toca em nenhuma outra camada.
 */
class PaymentGateway {
  constructor({ chave, logger }) {
    this.chave = chave;
    this.logger = logger;
  }

  static mascarar(cartao) {
    return `**** **** **** ${String(cartao).slice(-4)}`;
  }

  async autorizar({ cartao, valor }) {
    this.logger.info('autorização solicitada', {
      cartao: PaymentGateway.mascarar(cartao),
      valor,
    });

    const aprovado = String(cartao).startsWith('4');
    return {
      status: aprovado ? PagamentoStatus.PAGO : PagamentoStatus.RECUSADO,
      aprovado,
    };
  }
}

module.exports = { PaymentGateway };
