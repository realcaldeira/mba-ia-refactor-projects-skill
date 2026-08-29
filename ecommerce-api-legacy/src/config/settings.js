'use strict';

/** Configuração da aplicação — tudo que muda por ambiente vive aqui. */
const toBool = (valor, padrao = false) =>
  valor === undefined ? padrao : ['1', 'true', 'yes', 'on'].includes(String(valor).toLowerCase());

const settings = {
  port: Number(process.env.PORT || 3000),
  host: process.env.HOST || '127.0.0.1',
  dbPath: process.env.DB_PATH || ':memory:',
  ambiente: process.env.NODE_ENV || 'desenvolvimento',
  logLevel: process.env.LOG_LEVEL || 'info',
  seedOnBoot: toBool(process.env.SEED_ON_BOOT, true),
  auth: {
    secret: process.env.SECRET_KEY || 'dev-secret-change-me',
    tokenTtlHoras: Number(process.env.TOKEN_TTL_HORAS || 8),
  },
  payment: {
    gatewayKey: process.env.PAYMENT_GATEWAY_KEY || 'pk_test_local',
    gatewayUrl: process.env.PAYMENT_GATEWAY_URL || '',
  },
  smtp: {
    user: process.env.SMTP_USER || '',
    pass: process.env.SMTP_PASS || '',
  },
};

/** Falha alto quando um segredo de desenvolvimento chega em produção. */
function validar(config = settings) {
  if (config.ambiente !== 'production') return config;
  if (config.auth.secret === 'dev-secret-change-me') {
    throw new Error('SECRET_KEY precisa ser definida fora de desenvolvimento');
  }
  if (config.payment.gatewayKey === 'pk_test_local') {
    throw new Error('PAYMENT_GATEWAY_KEY precisa ser definida fora de desenvolvimento');
  }
  return config;
}

module.exports = { settings, validar };
