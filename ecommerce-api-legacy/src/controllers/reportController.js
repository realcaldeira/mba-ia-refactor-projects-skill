'use strict';

const { montarRelatorio } = require('../models/enrollmentModel');

class ReportController {
  constructor({ matriculas }) {
    this.matriculas = matriculas;
  }

  financeiro() {
    return async (_req, res, next) => {
      try {
        const linhas = await this.matriculas.relatorioFinanceiro();
        return res.json(montarRelatorio(linhas));
      } catch (erro) {
        return next(erro);
      }
    };
  }
}

module.exports = { ReportController };
