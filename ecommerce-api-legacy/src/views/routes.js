'use strict';

const express = require('express');

/** Fronteira HTTP: apenas o mapa rota → controller. Nenhuma lógica vive aqui. */
function registrarRotas(app, { checkout, relatorio, usuario }) {
  const router = express.Router();

  router.post('/checkout', checkout.handler());
  router.get('/admin/financial-report', relatorio.financeiro());
  router.delete('/users/:id', usuario.remover());

  app.use('/api', router);
  return app;
}

module.exports = { registrarRotas };
