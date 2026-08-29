'use strict';

const { PagamentoStatus } = require('../models/paymentModel');

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
