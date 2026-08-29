'use strict';

const express = require('express');

const { settings } = require('../config/settings');
const { requerAutenticacao } = require('../middlewares/auth');

function registrarRotas(app, { checkout, relatorio, usuario }, config = settings) {
  const router = express.Router();
  const guards = config.auth.required ? [requerAutenticacao(config.auth.secret)] : [];

  router.post('/checkout', checkout.handler());
  router.get('/admin/financial-report', ...guards, relatorio.financeiro());
  router.delete('/users/:id', ...guards, usuario.remover());

  app.use('/api', router);
  return app;
}

module.exports = { registrarRotas };
